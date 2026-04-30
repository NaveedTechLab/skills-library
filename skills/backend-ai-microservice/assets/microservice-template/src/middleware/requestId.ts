import { randomUUID } from 'crypto';
import type { Request, Response, NextFunction } from 'express';
import { rootLogger } from './logger';

declare global {
  namespace Express {
    interface Request {
      id: string;
      log: ReturnType<typeof rootLogger.child>;
    }
  }
}

export function requestIdMiddleware(req: Request, res: Response, next: NextFunction) {
  req.id = (req.headers['x-request-id'] as string) ?? randomUUID();
  res.setHeader('x-request-id', req.id);
  req.log = rootLogger.child({ requestId: req.id });
  next();
}
