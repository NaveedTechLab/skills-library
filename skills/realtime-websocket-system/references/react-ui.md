# React Notification UI Reference

## Table of Contents
1. [useNotifications Hook](#1-usenotifications-hook)
2. [Notification Badge](#2-notification-badge)
3. [Notification Dropdown](#3-notification-dropdown)
4. [Mark-as-Read API Integration](#4-mark-as-read-api-integration)
5. [Missed Alerts on Reconnect](#5-missed-alerts-on-reconnect)

---

## 1. useNotifications Hook

Manages the Socket.io connection, incoming alerts, and unread count. One instance per app (place at layout level).

```ts
// hooks/useNotifications.ts
import { useEffect, useRef, useCallback, useReducer } from 'react';
import { io, Socket } from 'socket.io-client';

export interface AlertEvent {
  eventId: number;
  ruleId: number;
  campaignId: number;
  metricKey: string;
  actualValue: number;
  thresholdValue: number;
  operator: string;
  severity: 'info' | 'warning' | 'critical';
  triggeredAt: string;
  read: boolean;
}

interface State {
  alerts: AlertEvent[];
  connected: boolean;
}

type Action =
  | { type: 'CONNECTED' }
  | { type: 'DISCONNECTED' }
  | { type: 'ALERT_RECEIVED'; payload: AlertEvent }
  | { type: 'ALERTS_LOADED'; payload: AlertEvent[] }
  | { type: 'MARK_READ'; payload: { campaignId: number } };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'CONNECTED':    return { ...state, connected: true };
    case 'DISCONNECTED': return { ...state, connected: false };
    case 'ALERT_RECEIVED':
      return { ...state, alerts: [{ ...action.payload, read: false }, ...state.alerts] };
    case 'ALERTS_LOADED':
      return { ...state, alerts: action.payload };
    case 'MARK_READ':
      return {
        ...state,
        alerts: state.alerts.map(a =>
          a.campaignId === action.payload.campaignId ? { ...a, read: true } : a
        ),
      };
    default: return state;
  }
}

interface Options {
  campaignIds: number[];
  token: string;
}

export function useNotifications({ campaignIds, token }: Options) {
  const [state, dispatch] = useReducer(reducer, { alerts: [], connected: false });
  const socketRef = useRef<Socket | null>(null);

  // Load existing unread alerts from REST API on mount
  useEffect(() => {
    if (campaignIds.length === 0) return;
    fetch(`/api/alerts?campaigns=${campaignIds.join(',')}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then((alerts: AlertEvent[]) => dispatch({ type: 'ALERTS_LOADED', payload: alerts }));
  }, [campaignIds.join(','), token]);

  // Connect WebSocket
  useEffect(() => {
    if (campaignIds.length === 0 || !token) return;

    const socket = io(`${process.env.NEXT_PUBLIC_WS_URL ?? ''}/alerts`, {
      auth: { token },
      query: { campaigns: campaignIds.join(',') },
      transports: ['websocket', 'polling'],
    });

    socketRef.current = socket;

    socket.on('connect',    () => dispatch({ type: 'CONNECTED' }));
    socket.on('disconnect', () => dispatch({ type: 'DISCONNECTED' }));

    socket.on('alert:triggered', (alert: AlertEvent) => {
      dispatch({ type: 'ALERT_RECEIVED', payload: alert });
    });

    return () => { socket.disconnect(); };
  }, [campaignIds.join(','), token]);

  const markRead = useCallback(async (campaignId: number) => {
    await fetch(`/api/campaigns/${campaignId}/alerts/read`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    dispatch({ type: 'MARK_READ', payload: { campaignId } });
  }, [token]);

  const unreadCount = state.alerts.filter(a => !a.read).length;

  return { alerts: state.alerts, unreadCount, connected: state.connected, markRead };
}
```

---

## 2. Notification Badge

```tsx
// components/NotificationBell.tsx
import { useState } from 'react';
import { BellIcon } from '@heroicons/react/24/outline';
import { NotificationDropdown } from './NotificationDropdown';
import { useNotifications } from '../hooks/useNotifications';

interface Props {
  campaignIds: number[];
  token: string;
}

export function NotificationBell({ campaignIds, token }: Props) {
  const [open, setOpen] = useState(false);
  const { alerts, unreadCount, markRead } = useNotifications({ campaignIds, token });

  function handleOpen() {
    setOpen(prev => !prev);
  }

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={handleOpen}
        aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
        style={{ background: 'none', border: 'none', cursor: 'pointer', position: 'relative' }}
      >
        <BellIcon style={{ width: 24, height: 24 }} />
        {unreadCount > 0 && (
          <span style={{
            position: 'absolute', top: -4, right: -4,
            background: '#ef4444', color: '#fff',
            borderRadius: '9999px', fontSize: 11,
            minWidth: 18, height: 18,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '0 4px',
          }}>
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <NotificationDropdown
          alerts={alerts}
          onMarkRead={markRead}
          onClose={() => setOpen(false)}
        />
      )}
    </div>
  );
}
```

---

## 3. Notification Dropdown

```tsx
// components/NotificationDropdown.tsx
import { useEffect, useRef } from 'react';
import type { AlertEvent } from '../hooks/useNotifications';

const SEVERITY_COLOR: Record<string, string> = {
  info:     '#3b82f6',
  warning:  '#f59e0b',
  critical: '#ef4444',
};

function formatAlert(alert: AlertEvent): string {
  const op = { gt: '>', lt: '<', gte: '>=', lte: '<=', eq: '=' }[alert.operator] ?? alert.operator;
  return `${alert.metricKey} ${op} ${alert.thresholdValue} (actual: ${alert.actualValue})`;
}

interface Props {
  alerts: AlertEvent[];
  onMarkRead: (campaignId: number) => void;
  onClose: () => void;
}

export function NotificationDropdown({ alerts, onMarkRead, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [onClose]);

  return (
    <div ref={ref} style={{
      position: 'absolute', right: 0, top: '110%',
      width: 360, maxHeight: 480, overflowY: 'auto',
      background: '#fff', border: '1px solid #e5e7eb',
      borderRadius: 8, boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
      zIndex: 1000,
    }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong>Notifications</strong>
        {alerts.some(a => !a.read) && (
          <button onClick={() => alerts.forEach(a => !a.read && onMarkRead(a.campaignId))}
            style={{ fontSize: 12, color: '#6366f1', background: 'none', border: 'none', cursor: 'pointer' }}>
            Mark all read
          </button>
        )}
      </div>

      {alerts.length === 0 && (
        <p style={{ padding: 16, color: '#9ca3af', textAlign: 'center' }}>No notifications</p>
      )}

      {alerts.map(alert => (
        <div key={alert.eventId} style={{
          padding: '10px 16px',
          borderBottom: '1px solid #f3f4f6',
          background: alert.read ? '#fff' : '#f0f9ff',
          display: 'flex', gap: 10, alignItems: 'flex-start',
        }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%', flexShrink: 0, marginTop: 6,
            background: SEVERITY_COLOR[alert.severity] ?? '#9ca3af',
          }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13 }}>{formatAlert(alert)}</div>
            <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>
              Campaign {alert.campaignId} &middot; {new Date(alert.triggeredAt).toLocaleString()}
            </div>
          </div>
          {!alert.read && (
            <button onClick={() => onMarkRead(alert.campaignId)}
              style={{ fontSize: 11, color: '#6366f1', background: 'none', border: 'none', cursor: 'pointer', flexShrink: 0 }}>
              Read
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
```

---

## 4. Mark-as-Read API Integration

```ts
// server: POST /api/campaigns/:campaignId/alerts/read
router.post('/:campaignId/alerts/read', async (req, res) => {
  await db.query(
    `UPDATE alert_events SET read_at = NOW()
     WHERE campaign_id = $1 AND read_at IS NULL`,
    [req.params.campaignId]
  );
  res.json({ ok: true });
});

// server: GET /api/alerts?campaigns=1,2,3
router.get('/', async (req, res) => {
  const ids = String(req.query.campaigns ?? '').split(',').map(Number).filter(Boolean);
  if (ids.length === 0) return res.json([]);
  const { rows } = await db.query(
    `SELECT e.*, r.name AS rule_name
     FROM alert_events e
     JOIN alert_rules r ON r.id = e.rule_id
     WHERE e.campaign_id = ANY($1::BIGINT[])
     ORDER BY e.created_at DESC
     LIMIT 100`,
    [ids]
  );
  res.json(rows.map(r => ({ ...r, read: r.read_at !== null })));
});
```

---

## 5. Missed Alerts on Reconnect

When a client reconnects after a disconnect, it may have missed emitted events. Fetch unread alerts from the REST API and merge with local state.

```ts
socket.io.on('reconnect', async () => {
  const missed = await fetch(`/api/alerts?campaigns=${campaignIds.join(',')}`)
    .then(r => r.json()) as AlertEvent[];
  dispatch({ type: 'ALERTS_LOADED', payload: missed });
});
```

This REST-reconciliation approach keeps the WS layer fire-and-forget and the REST API as the source of truth for persistent state.
