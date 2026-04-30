import express from 'express';
import { env } from './config/env';
import { requestIdMiddleware } from './middleware/requestId';
import { rootLogger } from './middleware/logger';
import { generateRouter } from './routes/generate';
import { APIError } from 'openai';

const app = express();

// ---- Middleware (order matters) ----
app.use(requestIdMiddleware);           // 1. attach request ID first
app.use(express.json({ limit: '1mb' }));

// ---- Routes ----
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/ready', (_req, res) => {
  if (!env.LLM_API_KEY) {
    return res.status(503).json({ status: 'not_ready', reason: 'LLM_API_KEY not set' });
  }
  res.json({ status: 'ready' });
});

app.use('/generate', generateRouter);

// ---- Error handler (must be last, 4-param signature) ----
app.use((err: any, req: any, res: any, _next: any) => {
  req.log?.error({ err }, 'Unhandled error');

  if (err instanceof APIError) {
    return res.status(err.status ?? 502).json({
      error: 'LLM_API_ERROR',
      message: err.message,
      code: err.code,
    });
  }

  res.status(500).json({ error: 'INTERNAL_ERROR', message: 'Internal server error' });
});

// ---- Start ----
app.listen(env.PORT, () => {
  rootLogger.info({ port: env.PORT, model: env.LLM_MODEL }, 'Server started');
});

export { app };
