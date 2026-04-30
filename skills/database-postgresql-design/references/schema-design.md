# PostgreSQL Schema Design Reference

## Table of Contents
1. [Normalization Guidelines](#1-normalization-guidelines)
2. [Analytics-Optimized Schema Patterns](#2-analytics-optimized-schema-patterns)
3. [Table Partitioning](#3-table-partitioning)
4. [Materialized Views](#4-materialized-views)
5. [Data Types Cheat Sheet](#5-data-types-cheat-sheet)
6. [Constraints and Defaults](#6-constraints-and-defaults)

---

## 1. Normalization Guidelines

**Start at 3NF for OLTP, denormalize deliberately for OLAP.**

| Scenario | Approach |
|---|---|
| High write throughput | Normalize (3NF) — minimize write amplification |
| Read-heavy analytics | Denormalize into wide fact tables — minimize JOINs |
| Mixed (most web apps) | Normalized core + materialized views for reports |

**3NF checklist:**
- Every column depends on the primary key only
- No repeating groups (no `tag1`, `tag2`, `tag3` columns — use a join table)
- No transitive dependencies (`order` table should not store `customer_email` — derive it via JOIN)

**When to deliberately denormalize:**
- Aggregation queries JOIN > 4 tables
- Report queries run > 1s on normalized schema
- Data is immutable after insert (event logs, ad impressions)

---

## 2. Analytics-Optimized Schema Patterns

### Star Schema (recommended for metrics dashboards)

```sql
-- Fact table: one row per event, foreign keys to dimensions
CREATE TABLE fact_ad_performance (
  id            BIGSERIAL PRIMARY KEY,
  date          DATE        NOT NULL,
  campaign_id   INT         NOT NULL REFERENCES dim_campaign(id),
  platform_id   SMALLINT    NOT NULL REFERENCES dim_platform(id),
  impressions   INT         NOT NULL DEFAULT 0,
  clicks        INT         NOT NULL DEFAULT 0,
  spend         NUMERIC(12,4) NOT NULL DEFAULT 0,
  revenue       NUMERIC(12,4) NOT NULL DEFAULT 0
);

-- Dimension table: slowly changing attributes
CREATE TABLE dim_campaign (
  id         SERIAL PRIMARY KEY,
  name       TEXT    NOT NULL,
  channel    TEXT    NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Indexes for this pattern:
```sql
CREATE INDEX idx_fact_date          ON fact_ad_performance (date);
CREATE INDEX idx_fact_campaign_date ON fact_ad_performance (campaign_id, date);
CREATE INDEX idx_fact_platform_date ON fact_ad_performance (platform_id, date);
```

### Event Log Pattern (append-only)

```sql
CREATE TABLE events (
  id         BIGSERIAL,
  user_id    BIGINT      NOT NULL,
  event_type TEXT        NOT NULL,
  properties JSONB,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (occurred_at);

-- Monthly partitions
CREATE TABLE events_2024_01 PARTITION OF events
  FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

---

## 3. Table Partitioning

Use range partitioning on a time column when:
- Table exceeds ~10M rows AND queries always filter on the time column
- You need fast DROP of old data (drop the partition, not DELETE)

```sql
-- Create partitioned parent
CREATE TABLE ad_impressions (
  id          BIGSERIAL,
  campaign_id INT         NOT NULL,
  viewed_at   TIMESTAMPTZ NOT NULL,
  cost        NUMERIC(10,4)
) PARTITION BY RANGE (viewed_at);

-- Quarterly partitions
CREATE TABLE ad_impressions_2024_q1 PARTITION OF ad_impressions
  FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE ad_impressions_2024_q2 PARTITION OF ad_impressions
  FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

-- Indexes are created per partition
CREATE INDEX ON ad_impressions_2024_q1 (campaign_id, viewed_at);
CREATE INDEX ON ad_impressions_2024_q2 (campaign_id, viewed_at);
```

**Constraint:** Queries MUST include the partition key in WHERE to benefit from partition pruning. `EXPLAIN` output shows `Partitions selected` when pruning works.

---

## 4. Materialized Views

Pre-aggregate expensive queries and refresh on a schedule.

```sql
-- Pre-aggregated daily campaign metrics
CREATE MATERIALIZED VIEW mv_daily_campaign_metrics AS
SELECT
  date,
  campaign_id,
  SUM(impressions)  AS impressions,
  SUM(clicks)       AS clicks,
  SUM(spend)        AS spend,
  SUM(revenue)      AS revenue,
  ROUND(SUM(revenue) / NULLIF(SUM(spend), 0), 4) AS roas
FROM fact_ad_performance
GROUP BY date, campaign_id
WITH DATA;

-- Index the materialized view for fast lookups
CREATE INDEX ON mv_daily_campaign_metrics (campaign_id, date);

-- Refresh (run via cron or pg_cron)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_campaign_metrics;
```

`CONCURRENTLY` requires a unique index and does not lock reads — use it in production.

---

## 5. Data Types Cheat Sheet

| Use case | Preferred type | Avoid |
|---|---|---|
| Monetary values | `NUMERIC(precision, scale)` | `FLOAT` (rounding errors) |
| Timestamps with timezone | `TIMESTAMPTZ` | `TIMESTAMP` (no tz = bugs) |
| Date only | `DATE` | `TIMESTAMPTZ` (unnecessary overhead) |
| IDs (high volume) | `BIGSERIAL` / `BIGINT` | `SERIAL` (exhausts at 2B) |
| Short status codes | `TEXT` with CHECK constraint | `VARCHAR(n)` (no performance benefit in PG) |
| Boolean flags | `BOOLEAN NOT NULL DEFAULT false` | `SMALLINT` |
| Flexible attributes | `JSONB` | `JSON` (JSONB is indexed and binary) |
| Enumerations | `TEXT` + CHECK or `ENUM` type | Unconstrained `TEXT` |

---

## 6. Constraints and Defaults

Always express invariants as constraints — the database is the last line of defense.

```sql
CREATE TABLE campaigns (
  id         BIGSERIAL PRIMARY KEY,
  name       TEXT        NOT NULL CHECK (length(name) > 0),
  status     TEXT        NOT NULL DEFAULT 'draft'
               CHECK (status IN ('draft', 'active', 'paused', 'archived')),
  budget     NUMERIC(12,2) NOT NULL CHECK (budget >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger to maintain updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_campaigns_updated_at
BEFORE UPDATE ON campaigns
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```
