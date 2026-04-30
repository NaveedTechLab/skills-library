# JWT Authentication Reference

## Table of Contents
1. [Token Generation and Signing](#1-token-generation-and-signing)
2. [Auth Middleware](#2-auth-middleware)
3. [Protected Route Pattern](#3-protected-route-pattern)
4. [Refresh Token Flow](#4-refresh-token-flow)
5. [Password Hashing](#5-password-hashing)
6. [Auth Endpoints](#6-auth-endpoints)

---

## 1. Token Generation and Signing

```ts
// src/lib/tokens.ts
import jwt from 'jsonwebtoken';
import { env } from '../config/env';

export interface TokenPayload {
  sub: string;       // user ID
  email: string;
  role: string;
}

export function signAccessToken(payload: TokenPayload): string {
  return jwt.sign(payload, env.JWT_SECRET, {
    expiresIn: env.JWT_EXPIRES_IN,  // e.g. '15m'
    issuer: 'api',
    audience: 'client',
  });
}

export function signRefreshToken(userId: string): string {
  return jwt.sign({ sub: userId }, env.JWT_REFRESH_SECRET, {
    expiresIn: '7d',
    issuer: 'api',
    audience: 'refresh',
  });
}

export function verifyAccessToken(token: string): TokenPayload {
  return jwt.verify(token, env.JWT_SECRET, {
    issuer: 'api',
    audience: 'client',
  }) as TokenPayload;
}

export function verifyRefreshToken(token: string): { sub: string } {
  return jwt.verify(token, env.JWT_REFRESH_SECRET, {
    issuer: 'api',
    audience: 'refresh',
  }) as { sub: string };
}
```

**Environment variables required:**
```
JWT_SECRET=<64+ random chars>
JWT_REFRESH_SECRET=<different 64+ random chars>
JWT_EXPIRES_IN=15m
```

Generate secrets: `node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"`

---

## 2. Auth Middleware

```ts
// src/middleware/auth.ts
import { Request, Response, NextFunction } from 'express';
import { verifyAccessToken, TokenPayload } from '../lib/tokens';

declare global {
  namespace Express {
    interface Request {
      user?: TokenPayload;
    }
  }
}

export function authenticate(req: Request, res: Response, next: NextFunction) {
  const header = req.headers.authorization;
  if (!header?.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'AUTH_MISSING', message: 'Authorization header required' });
  }

  const token = header.slice(7);
  try {
    req.user = verifyAccessToken(token);
    next();
  } catch (err: any) {
    const code = err.name === 'TokenExpiredError' ? 'TOKEN_EXPIRED' : 'TOKEN_INVALID';
    res.status(401).json({ error: code, message: err.message });
  }
}

// Role-based access control — call after authenticate
export function requireRole(...roles: string[]) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!req.user || !roles.includes(req.user.role)) {
      return res.status(403).json({ error: 'FORBIDDEN', message: 'Insufficient permissions' });
    }
    next();
  };
}
```

---

## 3. Protected Route Pattern

```ts
import { authenticate, requireRole } from '../middleware/auth';

// Any authenticated user
router.get('/profile', authenticate, handler);

// Specific role
router.delete('/users/:id', authenticate, requireRole('admin'), handler);

// Optional auth (public + authenticated variants)
router.get('/feed', optionalAuthenticate, handler);

function optionalAuthenticate(req: Request, res: Response, next: NextFunction) {
  const header = req.headers.authorization;
  if (!header) return next(); // continue unauthenticated
  authenticate(req, res, next);
}
```

---

## 4. Refresh Token Flow

Store refresh tokens in the database to enable revocation:

```sql
CREATE TABLE refresh_tokens (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  TEXT   NOT NULL UNIQUE,   -- store hash, not plain token
  expires_at  TIMESTAMPTZ NOT NULL,
  revoked_at  TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens (user_id) WHERE revoked_at IS NULL;
```

```ts
import crypto from 'crypto';

async function saveRefreshToken(userId: string, token: string) {
  const hash = crypto.createHash('sha256').update(token).digest('hex');
  await db.query(
    `INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
     VALUES ($1, $2, NOW() + INTERVAL '7 days')`,
    [userId, hash]
  );
}

// POST /auth/refresh
router.post('/refresh', async (req, res, next) => {
  const { refreshToken } = req.body;
  if (!refreshToken) return res.status(400).json({ error: 'MISSING_TOKEN' });

  try {
    const { sub: userId } = verifyRefreshToken(refreshToken);
    const hash = crypto.createHash('sha256').update(refreshToken).digest('hex');

    const { rows } = await db.query(
      `SELECT id FROM refresh_tokens
       WHERE token_hash = $1 AND user_id = $2
         AND revoked_at IS NULL AND expires_at > NOW()`,
      [hash, userId]
    );

    if (rows.length === 0) return res.status(401).json({ error: 'TOKEN_INVALID' });

    // Rotate: revoke old, issue new
    await db.query('UPDATE refresh_tokens SET revoked_at = NOW() WHERE token_hash = $1', [hash]);

    const user = await getUserById(userId);
    const newAccessToken  = signAccessToken({ sub: user.id, email: user.email, role: user.role });
    const newRefreshToken = signRefreshToken(user.id);
    await saveRefreshToken(user.id, newRefreshToken);

    res.json({ accessToken: newAccessToken, refreshToken: newRefreshToken });
  } catch (err) {
    next(err);
  }
});
```

---

## 5. Password Hashing

```ts
import bcrypt from 'bcrypt';

const SALT_ROUNDS = 12;

export async function hashPassword(plain: string): Promise<string> {
  return bcrypt.hash(plain, SALT_ROUNDS);
}

export async function verifyPassword(plain: string, hash: string): Promise<boolean> {
  return bcrypt.compare(plain, hash);
}
```

**Never:**
- Store plain passwords
- Use MD5 or SHA for passwords
- Log passwords or tokens

---

## 6. Auth Endpoints

```ts
// POST /auth/register
router.post('/register', authLimiter, async (req, res, next) => {
  const parsed = RegisterSchema.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ error: 'VALIDATION_ERROR', details: parsed.error.flatten() });

  const { email, password, name } = parsed.data;
  const existing = await db.query('SELECT id FROM users WHERE email = $1', [email]);
  if (existing.rows.length > 0) return res.status(409).json({ error: 'EMAIL_TAKEN' });

  const passwordHash = await hashPassword(password);
  const { rows: [user] } = await db.query(
    'INSERT INTO users (email, password_hash, name) VALUES ($1, $2, $3) RETURNING id, email, name, role',
    [email, passwordHash, name]
  );

  const accessToken  = signAccessToken({ sub: user.id, email: user.email, role: user.role });
  const refreshToken = signRefreshToken(user.id);
  await saveRefreshToken(user.id, refreshToken);

  res.status(201).json({ data: { user, accessToken, refreshToken } });
});

// POST /auth/login
router.post('/login', authLimiter, async (req, res, next) => {
  const parsed = LoginSchema.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ error: 'VALIDATION_ERROR' });

  const { email, password } = parsed.data;
  const { rows: [user] } = await db.query(
    'SELECT id, email, name, role, password_hash FROM users WHERE email = $1 AND deleted_at IS NULL',
    [email]
  );

  // Constant-time response to prevent user enumeration
  const valid = user ? await verifyPassword(password, user.password_hash) : await bcrypt.hash('dummy', 1);
  if (!user || !valid) return res.status(401).json({ error: 'INVALID_CREDENTIALS' });

  const accessToken  = signAccessToken({ sub: user.id, email: user.email, role: user.role });
  const refreshToken = signRefreshToken(user.id);
  await saveRefreshToken(user.id, refreshToken);

  const { password_hash: _, ...safeUser } = user;
  res.json({ data: { user: safeUser, accessToken, refreshToken } });
});
```
