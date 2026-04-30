---
name: realtime-websocket-system
description: "Build WebSocket-based real-time notification systems with persistence. Use when the user needs to: (1) set up a Socket.io or native WS server for real-time events, (2) design an event-driven alert engine that evaluates campaign thresholds, (3) store and query alerts in PostgreSQL, (4) build a React notification UI with badge count and dropdown, or (5) connect campaign data changes to per-campaign configurable alerts. Triggers on keywords like: WebSocket, Socket.io, real-time, notifications, alerts, threshold, badge, live updates, campaign alerts, event-driven."
---

# Real-Time WebSocket System

Build in layers: transport first, then alert logic, then persistence, then UI.

## Architecture

```
Campaign Data Source
       |
       v
  Alert Engine  -----> PostgreSQL (alert_rules, alert_events)
       |
       v
 Socket.io Server
       |
    [rooms per campaign_id]
       |
       v
  React Client  <-- useNotifications hook
       |
  [Badge + Dropdown UI]
```

## Build Workflow

```
1. Choose transport (Socket.io vs native ws)
2. Set up WebSocket server with per-campaign rooms
3. Design PostgreSQL schema for alert rules and events
4. Implement threshold evaluation engine
5. Wire campaign data source to engine
6. Build React client hook and notification UI
```

---

## 1. Transport Selection

**Use Socket.io when:**
- Browser clients need auto-reconnect
- You need per-campaign rooms (Socket.io rooms are built-in)
- HTTP long-poll fallback is required
- Namespaces help separate concerns (e.g., `/alerts` vs `/metrics`)

**Use native `ws` when:**
- Server-to-server only (no browser clients)
- Minimal dependency footprint is required
- Custom binary protocol is needed

**Default choice: Socket.io.** All patterns below use Socket.io.

---

## 2. WebSocket Server — Key Patterns

```ts
// Namespace for alerts
const alertsNs = io.of('/alerts');

// Auth middleware
alertsNs.use((socket, next) => {
  const token = socket.handshake.auth.token;
  if (!verifyToken(token)) return next(new Error('Unauthorized'));
  next();
});

// Join per-campaign room on connect
alertsNs.on('connection', (socket) => {
  const campaignIds: string[] = socket.handshake.query.campaigns as string[];
  campaignIds.forEach(id => socket.join(`campaign:${id}`));
});

// Emit alert to campaign room
function emitAlert(campaignId: string, alert: AlertPayload) {
  alertsNs.to(`campaign:${campaignId}`).emit('alert:triggered', alert);
}
```

For full server setup, CORS config, and scaling with Redis adapter, see [references/websocket-server.md](references/websocket-server.md).

---

## 3. Alert Engine — Key Patterns

**Threshold evaluation (called after each data refresh):**

```ts
async function evaluateThresholds(campaignId: string, metrics: CampaignMetrics) {
  const rules = await db.query(
    'SELECT * FROM alert_rules WHERE campaign_id = $1 AND enabled = true',
    [campaignId]
  );
  for (const rule of rules.rows) {
    const value = metrics[rule.metric_key];
    if (exceedsThreshold(value, rule.operator, rule.threshold_value)) {
      await persistAlert(campaignId, rule, value);
      emitAlert(campaignId, { ruleId: rule.id, metric: rule.metric_key, value });
    }
  }
}
```

For the full PostgreSQL schema (`alert_rules`, `alert_events`), cooldown logic, and operator types, see [references/alert-engine.md](references/alert-engine.md).

---

## 4. React Notification UI — Key Patterns

```tsx
// Notification badge
<button onClick={toggleDropdown}>
  <BellIcon />
  {unreadCount > 0 && <span className="badge">{unreadCount}</span>}
</button>
```

For `useNotifications` hook (Socket.io client + state), dropdown component, and mark-as-read API pattern, see [references/react-ui.md](references/react-ui.md).

---

## Resources

- [references/websocket-server.md](references/websocket-server.md) — Full server setup, Redis adapter for scaling, auth, CORS, error handling
- [references/alert-engine.md](references/alert-engine.md) — PostgreSQL schema, threshold operators, cooldown logic, campaign-level config
- [references/react-ui.md](references/react-ui.md) — useNotifications hook, badge component, dropdown, mark-as-read
