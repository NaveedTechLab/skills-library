import { z } from 'zod';

const EnvSchema = z.object({
  LLM_API_KEY:    z.string().min(1, 'LLM_API_KEY is required'),
  LLM_BASE_URL:   z.string().url().default('https://api.openai.com/v1'),
  LLM_MODEL:      z.string().default('gpt-4o-mini'),
  PORT:           z.coerce.number().int().positive().default(3000),
  LOG_LEVEL:      z.enum(['trace', 'debug', 'info', 'warn', 'error']).default('info'),
  NODE_ENV:       z.enum(['development', 'production', 'test']).default('development'),
});

const parsed = EnvSchema.safeParse(process.env);

if (!parsed.success) {
  console.error('Invalid environment variables:');
  console.error(parsed.error.flatten().fieldErrors);
  process.exit(1);
}

export const env = parsed.data;
