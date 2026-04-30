import { Pool } from 'pg';
import { env } from './config/env';

export const db = new Pool({
  connectionString: env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
});

db.on('error', (err) => {
  console.error('Unexpected pg pool error:', err);
});
