import { z } from 'zod';
import { Request, Response, NextFunction } from 'express';

export function validate<T extends z.ZodTypeAny>(
  source: 'body' | 'query' | 'params',
  schema: T
) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req[source]);
    if (!result.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        details: result.error.flatten(),
      });
    }
    (req as any)[source] = result.data;
    next();
  };
}
