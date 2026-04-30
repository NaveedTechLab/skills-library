import { z } from 'zod';

const EnvSchema = z.object({
  DATABASE_URL:       z.string().min(1, 'DATABASE_URL is required'),
  JWT_SECRET:         z.string().min(32, 'JWT_SECRET must be at least 32 chars'),
  JWT_REFRESH_SECRET: z.string().min(32, 'JWT_REFRESH_SECRET must be at least 32 chars'),
  JWT_EXPIRES_IN:     z.string().default('15m'),
  PORT:               z.coerce.number().int().positive().default(3000),
  LOG_LEVEL:          z.enum(['trace', 'debug', 'info', 'warn', 'error']).default('info'),
  NODE_ENV:           z.enum(['development', 'production', 'test']).default('development'),
});

const parsed = EnvSchema.safeParse(process.env);
if (!parsed.success) {
  console.error('Invalid environment variables:', parsed.error.flatten().fieldErrors);
  process.exit(1);
}

export const env = parsed.data;
