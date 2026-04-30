import { Request, Response, NextFunction } from 'express';

export function errorHandler(err: any, req: Request, res: Response, _next: NextFunction) {
  (req as any).log?.error({ err }, 'Unhandled error');

  // PostgreSQL constraint violations
  if (err.code === '23505') return res.status(409).json({ error: 'DUPLICATE_ENTRY', message: err.detail });
  if (err.code === '23503') return res.status(409).json({ error: 'REFERENCE_ERROR', message: err.detail });
  if (err.code === '22P02') return res.status(400).json({ error: 'INVALID_ID', message: 'Invalid ID format' });

  res.status(err.status ?? 500).json({
    error: err.code ?? 'INTERNAL_ERROR',
    message: err.expose ? err.message : 'Internal server error',
    requestId: (req as any).id,
  });
}
