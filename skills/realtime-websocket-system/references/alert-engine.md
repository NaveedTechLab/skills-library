# Alert Engine Reference

## Table of Contents
1. [PostgreSQL Schema](#1-postgresql-schema)
2. [Threshold Operators and Evaluation](#2-threshold-operators-and-evaluation)
3. [Cooldown Logic](#3-cooldown-logic)
4. [Campaign-Level Rule Configuration](#4-campaign-level-rule-configuration)
5. [Data Source Integration Patterns](#5-data-source-integration-patterns)
6. [Alert Persistence and History Queries](#6-alert-persistence-and-history-queries)

---

## 1. PostgreSQL Schema

```sql
-- Per-campaign alert rules (configurable)
CREATE TABLE alert_rules (
  id             BIGSERIAL PRIMARY KEY,
  campaign_id    BIGINT      NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  name           TEXT        NOT NULL,
  metric_key     TEXT        NOT NULL,  -- e.g. 'roas', 'spend', 'ctr', 'impressions'
  operator       TEXT        NOT NULL CHECK (operator IN ('gt', 'lt', 'gte', 'lte', 'eq')),
  threshold_value NUMERIC(14,4) NOT NULL,
  severity       TEXT        NOT NULL DEFAULT 'warning'
                   CHECK (severity IN ('info', 'warning', 'critical')),
  cooldown_minutes INT        NOT NULL DEFAULT 60,  -- suppress repeated alerts
  enabled        BOOLEAN     NOT NULL DEFAULT true,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alert_rules_campaign ON alert_rules (campaign_id) WHERE enabled = true;

-- Triggered alert events (immutable log)
CREATE TABLE alert_events (
  id           BIGSERIAL PRIMARY KEY,
  rule_id      BIGINT      NOT NULL REFERENCES alert_rules(id),
  campaign_id  BIGINT      NOT NULL,
  metric_key   TEXT        NOT NULL,
  actual_value NUMERIC(14,4) NOT NULL,
  threshold_value NUMERIC(14,4) NOT NULL,
  severity     TEXT        NOT NULL,
  read_at      TIMESTAMPTZ,              -- NULL = unread
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alert_events_campaign_unread
  ON alert_events (campaign_id, created_at DESC)
  WHERE read_at IS NULL;
```

---

## 2. Threshold Operators and Evaluation

```ts
type Operator = 'gt' | 'lt' | 'gte' | 'lte' | 'eq';

function exceedsThreshold(actual: number, operator: Operator, threshold: number): boolean {
  switch (operator) {
    case 'gt':  return actual > threshold;
    case 'lt':  return actual < threshold;
    case 'gte': return actual >= threshold;
    case 'lte': return actual <= threshold;
    case 'eq':  return actual === threshold;
  }
}
```

**Evaluation loop — called after each campaign metrics refresh:**

```ts
import { db } from './db';
import { emitToCampaign } from './websocket';

interface CampaignMetrics {
  roas: number;
  spend: number;
  ctr: number;
  impressions: number;
  clicks: number;
  revenue: number;
  [key: string]: number;
}

export async function evaluateAlertRules(
  campaignId: number,
  metrics: CampaignMetrics
): Promise<void> {
  const { rows: rules } = await db.query<AlertRule>(
    `SELECT * FROM alert_rules
     WHERE campaign_id = $1 AND enabled = true`,
    [campaignId]
  );

  for (const rule of rules) {
    const actual = metrics[rule.metric_key];
    if (actual === undefined) continue; // metric not present in this snapshot

    if (!exceedsThreshold(actual, rule.operator, rule.threshold_value)) continue;
    if (await isInCooldown(rule)) continue;

    const event = await persistAlertEvent(rule, actual);
    emitToCampaign(campaignId, 'alert:triggered', {
      eventId: event.id,
      ruleId: rule.id,
      campaignId,
      metricKey: rule.metric_key,
      actualValue: actual,
      thresholdValue: rule.threshold_value,
      operator: rule.operator,
      severity: rule.severity,
      triggeredAt: event.created_at,
    });
  }
}
```

---

## 3. Cooldown Logic

Prevent alert flooding: suppress re-triggering a rule for its configured cooldown window.

```ts
async function isInCooldown(rule: AlertRule): Promise<boolean> {
  const { rows } = await db.query(
    `SELECT 1 FROM alert_events
     WHERE rule_id = $1
       AND created_at >= NOW() - ($2 || ' minutes')::INTERVAL
     LIMIT 1`,
    [rule.id, rule.cooldown_minutes]
  );
  return rows.length > 0;
}
```

---

## 4. Campaign-Level Rule Configuration

REST API endpoints for managing rules per campaign:

```ts
// GET /api/campaigns/:campaignId/alert-rules
router.get('/:campaignId/alert-rules', async (req, res) => {
  const { rows } = await db.query(
    'SELECT * FROM alert_rules WHERE campaign_id = $1 ORDER BY created_at DESC',
    [req.params.campaignId]
  );
  res.json(rows);
});

// POST /api/campaigns/:campaignId/alert-rules
router.post('/:campaignId/alert-rules', async (req, res) => {
  const { name, metric_key, operator, threshold_value, severity, cooldown_minutes } = req.body;
  const { rows } = await db.query(
    `INSERT INTO alert_rules (campaign_id, name, metric_key, operator, threshold_value, severity, cooldown_minutes)
     VALUES ($1, $2, $3, $4, $5, $6, $7)
     RETURNING *`,
    [req.params.campaignId, name, metric_key, operator, threshold_value, severity ?? 'warning', cooldown_minutes ?? 60]
  );
  res.status(201).json(rows[0]);
});

// PATCH /api/campaigns/:campaignId/alert-rules/:ruleId
router.patch('/:campaignId/alert-rules/:ruleId', async (req, res) => {
  const allowed = ['name', 'threshold_value', 'operator', 'severity', 'cooldown_minutes', 'enabled'];
  const updates = Object.fromEntries(
    Object.entries(req.body).filter(([k]) => allowed.includes(k))
  );
  const sets = Object.keys(updates).map((k, i) => `${k} = $${i + 3}`).join(', ');
  const { rows } = await db.query(
    `UPDATE alert_rules SET ${sets}, updated_at = NOW()
     WHERE id = $1 AND campaign_id = $2 RETURNING *`,
    [req.params.ruleId, req.params.campaignId, ...Object.values(updates)]
  );
  res.json(rows[0]);
});
```

---

## 5. Data Source Integration Patterns

**Pattern A — Polling scheduler (simplest, works with any data source):**

```ts
import { evaluateAlertRules } from './alertEngine';
import { fetchCampaignMetrics } from './campaignService';

// Run every 60 seconds for all active campaigns
setInterval(async () => {
  const { rows: campaigns } = await db.query(
    "SELECT id FROM campaigns WHERE status = 'active'"
  );
  await Promise.allSettled(
    campaigns.map(async ({ id }) => {
      const metrics = await fetchCampaignMetrics(id);
      await evaluateAlertRules(id, metrics);
    })
  );
}, 60_000);
```

**Pattern B — Event-driven (triggered on data write):**

```ts
// Call after inserting a new performance snapshot
async function onMetricsUpdated(campaignId: number, metrics: CampaignMetrics) {
  await evaluateAlertRules(campaignId, metrics);
}
```

**Pattern C — PostgreSQL LISTEN/NOTIFY (zero polling):**

```sql
-- Trigger on fact_ad_performance insert
CREATE OR REPLACE FUNCTION notify_metrics_updated()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  PERFORM pg_notify('metrics_updated', NEW.campaign_id::TEXT);
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_metrics_updated
AFTER INSERT ON fact_ad_performance
FOR EACH ROW EXECUTE FUNCTION notify_metrics_updated();
```

```ts
// Node listener
import { Client } from 'pg';
const listener = new Client({ connectionString: process.env.DATABASE_URL });
await listener.connect();
await listener.query('LISTEN metrics_updated');

listener.on('notification', async ({ payload: campaignId }) => {
  const metrics = await fetchCampaignMetrics(Number(campaignId));
  await evaluateAlertRules(Number(campaignId), metrics);
});
```

---

## 6. Alert Persistence and History Queries

```ts
async function persistAlertEvent(rule: AlertRule, actualValue: number) {
  const { rows } = await db.query(
    `INSERT INTO alert_events (rule_id, campaign_id, metric_key, actual_value, threshold_value, severity)
     VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
    [rule.id, rule.campaign_id, rule.metric_key, actualValue, rule.threshold_value, rule.severity]
  );
  return rows[0];
}
```

**Fetch unread alerts for a campaign:**
```sql
SELECT e.*, r.name AS rule_name
FROM alert_events e
JOIN alert_rules r ON r.id = e.rule_id
WHERE e.campaign_id = $1 AND e.read_at IS NULL
ORDER BY e.created_at DESC
LIMIT 50;
```

**Mark alerts as read:**
```sql
UPDATE alert_events
SET read_at = NOW()
WHERE campaign_id = $1 AND read_at IS NULL;
```

**Unread count (used for badge):**
```sql
SELECT COUNT(*) AS unread_count
FROM alert_events
WHERE campaign_id = ANY($1::BIGINT[]) AND read_at IS NULL;
```
