# WebSocket Server Reference

## Table of Contents
1. [Socket.io Server Setup](#1-socketio-server-setup)
2. [CORS and Auth Configuration](#2-cors-and-auth-configuration)
3. [Room Management (per-campaign)](#3-room-management-per-campaign)
4. [Error Handling and Reconnection](#4-error-handling-and-reconnection)
5. [Scaling with Redis Adapter](#5-scaling-with-redis-adapter)
6. [Native ws Alternative](#6-native-ws-alternative)

---

## 1. Socket.io Server Setup

```ts
// server/websocket.ts
import { Server } from 'socket.io';
import { createServer } from 'http';
import express from 'express';

const app = express();
const httpServer = createServer(app);

export const io = new Server(httpServer, {
  cors: {
    origin: process.env.CLIENT_URL || 'http://localhost:3000',
    methods: ['GET', 'POST'],
    credentials: true,
  },
  transports: ['websocket', 'polling'], // websocket first, polling fallback
  pingTimeout: 20000,
  pingInterval: 10000,
});

// Alerts namespace — isolate from other WS concerns
export const alertsNs = io.of('/alerts');

export { httpServer };
```

Attach to Express app:
```ts
// server/index.ts
import { httpServer } from './websocket';
httpServer.listen(process.env.PORT || 4000);
```

---

## 2. CORS and Auth Configuration

```ts
import jwt from 'jsonwebtoken';

alertsNs.use((socket, next) => {
  const token = socket.handshake.auth?.token
    ?? socket.handshake.headers?.authorization?.replace('Bearer ', '');

  if (!token) return next(new Error('AUTH_MISSING'));

  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET!) as { userId: string };
    socket.data.userId = payload.userId;
    next();
  } catch {
    next(new Error('AUTH_INVALID'));
  }
});
```

Client must send token on connect:
```ts
const socket = io('http://localhost:4000/alerts', {
  auth: { token: localStorage.getItem('authToken') },
  query: { campaigns: '1,2,3' }, // campaign IDs to subscribe to
});
```

---

## 3. Room Management (per-campaign)

Each socket joins rooms for its subscribed campaigns. Alerts are emitted to campaign rooms, so only subscribed clients receive them.

```ts
alertsNs.on('connection', (socket) => {
  // Parse campaign IDs from query string
  const raw = socket.handshake.query.campaigns as string | undefined;
  const campaignIds = raw ? raw.split(',').map(id => id.trim()).filter(Boolean) : [];

  // Join one room per campaign
  campaignIds.forEach(id => {
    socket.join(`campaign:${id}`);
  });

  // Allow client to subscribe to additional campaigns after connect
  socket.on('subscribe:campaign', (campaignId: string) => {
    socket.join(`campaign:${campaignId}`);
    socket.emit('subscribed', { campaignId });
  });

  socket.on('unsubscribe:campaign', (campaignId: string) => {
    socket.leave(`campaign:${campaignId}`);
  });

  socket.on('disconnect', (reason) => {
    console.log(`Socket ${socket.id} disconnected: ${reason}`);
  });
});

// Utility — emit to all subscribers of a campaign
export function emitToCampaign(campaignId: string | number, event: string, payload: unknown) {
  alertsNs.to(`campaign:${campaignId}`).emit(event, payload);
}
```

---

## 4. Error Handling and Reconnection

**Server-side — emit structured errors:**
```ts
socket.emit('error', { code: 'ALERT_FETCH_FAILED', message: 'Could not load alerts' });
```

**Client-side — handle reconnection:**
```ts
socket.on('connect_error', (err) => {
  console.error('WS connect error:', err.message);
  // err.message will be 'AUTH_MISSING' or 'AUTH_INVALID' from middleware
  if (err.message === 'AUTH_INVALID') {
    // Refresh token and reconnect
    socket.auth = { token: await refreshToken() };
    socket.connect();
  }
});

socket.io.on('reconnect', (attempt) => {
  console.log(`Reconnected after ${attempt} attempt(s)`);
  // Re-fetch missed alerts from REST API
  fetchMissedAlerts(lastSeenAt);
});
```

---

## 5. Scaling with Redis Adapter

When running multiple server instances (e.g., behind a load balancer), use the Redis adapter so rooms work across instances.

```bash
npm install @socket.io/redis-adapter ioredis
```

```ts
import { createAdapter } from '@socket.io/redis-adapter';
import { Redis } from 'ioredis';

const pubClient = new Redis(process.env.REDIS_URL!);
const subClient = pubClient.duplicate();

io.adapter(createAdapter(pubClient, subClient));
```

No other code changes needed — `emitToCampaign` works across all instances after this.

---

## 6. Native ws Alternative

Use when Socket.io overhead is not acceptable (server-to-server, CLI clients, binary protocols).

```ts
import { WebSocketServer, WebSocket } from 'ws';

const wss = new WebSocketServer({ port: 4001 });

// Track campaign subscriptions manually
const roomMap = new Map<string, Set<WebSocket>>(); // campaignId -> sockets

wss.on('connection', (ws, req) => {
  const params = new URL(req.url!, 'http://localhost').searchParams;
  const campaigns = params.get('campaigns')?.split(',') ?? [];

  campaigns.forEach(id => {
    if (!roomMap.has(id)) roomMap.set(id, new Set());
    roomMap.get(id)!.add(ws);
  });

  ws.on('close', () => {
    roomMap.forEach(sockets => sockets.delete(ws));
  });
});

function broadcastToCampaign(campaignId: string, payload: unknown) {
  const sockets = roomMap.get(campaignId) ?? new Set();
  const message = JSON.stringify(payload);
  sockets.forEach(ws => {
    if (ws.readyState === WebSocket.OPEN) ws.send(message);
  });
}
```
