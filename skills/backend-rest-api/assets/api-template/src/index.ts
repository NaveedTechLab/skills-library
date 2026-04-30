import express from 'express';
import { env } from './config/env';
import { globalLimiter, authLimiter } from './middleware/rateLimiter';
import { errorHandler } from './middleware/errorHandler';
import { resourceRouter } from './routes/resource';

const app = express();

// ---- Middleware (order matters) ----
app.use(globalLimiter);                     // 1. rate limit first
app.use(express.json({ limit: '1mb' }));

// ---- Health ----
app.get('/health', (_req, res) => res.json({ status: 'ok', timestamp: new Date().toISOString() }));

// ---- Routes ----
// app.use('/auth', authLimiter, authRouter);   // stricter limit on auth
app.use('/resources', resourceRouter);

// ---- Error handler (must be last) ----
app.use(errorHandler);

app.listen(env.PORT, () => {
  console.log(`Server running on port ${env.PORT} [${env.NODE_ENV}]`);
});

export { app };
