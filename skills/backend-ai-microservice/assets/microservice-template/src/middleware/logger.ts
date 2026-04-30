import pino from 'pino';
import { env } from '../config/env';

export const rootLogger = pino({
  level: env.LOG_LEVEL,
  ...(env.NODE_ENV === 'development'
    ? { transport: { target: 'pino-pretty', options: { colorize: true } } }
    : {}),
  base: { service: 'ai-microservice', env: env.NODE_ENV },
  timestamp: pino.stdTimeFunctions.isoTime,
  redact: ['req.headers.authorization', 'body.password'],
});
