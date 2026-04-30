import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { env } from '../config/env';

export interface TokenPayload {
  sub: string;
  email: string;
  role: string;
}

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

  try {
    req.user = jwt.verify(header.slice(7), env.JWT_SECRET, {
      issuer: 'api',
      audience: 'client',
    }) as TokenPayload;
    next();
  } catch (err: any) {
    const code = err.name === 'TokenExpiredError' ? 'TOKEN_EXPIRED' : 'TOKEN_INVALID';
    res.status(401).json({ error: code, message: err.message });
  }
}

export function requireRole(...roles: string[]) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!req.user || !roles.includes(req.user.role)) {
      return res.status(403).json({ error: 'FORBIDDEN', message: 'Insufficient permissions' });
    }
    next();
  };
}
