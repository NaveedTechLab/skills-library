import rateLimit from 'express-rate-limit';

const base = {
  standardHeaders: true,
  legacyHeaders: false,
};

// Global: 100 requests/minute/IP
export const globalLimiter = rateLimit({
  ...base,
  windowMs: 60_000,
  max: 100,
  message: { error: 'RATE_LIMIT_EXCEEDED', message: 'Too many requests, please try again in a minute' },
});

// Auth endpoints: 10 requests/minute/IP (brute-force protection)
export const authLimiter = rateLimit({
  ...base,
  windowMs: 60_000,
  max: 10,
  message: { error: 'RATE_LIMIT_EXCEEDED', message: 'Too many auth attempts, please try again in a minute' },
});
