# LLM Integration Reference

## Table of Contents
1. [Provider Client Setup](#1-provider-client-setup)
2. [Non-Streaming Endpoint](#2-non-streaming-endpoint)
3. [SSE Streaming Endpoint](#3-sse-streaming-endpoint)
4. [Retry and Timeout Logic](#4-retry-and-timeout-logic)
5. [Error Taxonomy and Handling](#5-error-taxonomy-and-handling)
6. [Prompt Construction Patterns](#6-prompt-construction-patterns)

---

## 1. Provider Client Setup

### OpenAI / OpenAI-compatible (default)

```ts
// src/clients/llm.ts
import OpenAI from 'openai';
import { env } from '../config/env';

export const llm = new OpenAI({
  apiKey: env.LLM_API_KEY,
  baseURL: env.LLM_BASE_URL,  // swap for any OpenAI-compatible API
  timeout: 30_000,
  maxRetries: 2,
});
```

### Anthropic Claude

```ts
import Anthropic from '@anthropic-ai/sdk';

export const llm = new Anthropic({
  apiKey: env.LLM_API_KEY,
  timeout: 30_000,
  maxRetries: 2,
});
```

**Switching providers:** Change only the client instantiation and the request shape. Keep the route handler provider-agnostic by wrapping in an adapter function (see Section 2).

---

## 2. Non-Streaming Endpoint

```ts
// src/routes/generate.ts
import { Router } from 'express';
import { z } from 'zod';
import { llm } from '../clients/llm';
import { env } from '../config/env';

const router = Router();

const GenerateSchema = z.object({
  prompt:      z.string().min(1).max(8000),
  system:      z.string().optional(),
  max_tokens:  z.coerce.number().int().min(1).max(4096).default(1024),
  temperature: z.coerce.number().min(0).max(2).default(0.7),
});

router.post('/generate', async (req, res, next) => {
  const parsed = GenerateSchema.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ errors: parsed.error.flatten() });

  const { prompt, system, max_tokens, temperature } = parsed.data;

  req.log.info({ model: env.LLM_MODEL, max_tokens }, 'LLM request started');

  try {
    const completion = await llm.chat.completions.create({
      model: env.LLM_MODEL,
      messages: [
        ...(system ? [{ role: 'system' as const, content: system }] : []),
        { role: 'user', content: prompt },
      ],
      max_tokens,
      temperature,
    });

    const text = completion.choices[0]?.message?.content ?? '';
    req.log.info({ tokens: completion.usage }, 'LLM request completed');
    res.json({ text, usage: completion.usage });
  } catch (err) {
    next(err); // handled by error middleware
  }
});

export { router as generateRouter };
```

---

## 3. SSE Streaming Endpoint

```ts
router.post('/generate/stream', async (req, res, next) => {
  const parsed = GenerateSchema.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ errors: parsed.error.flatten() });

  const { prompt, system, max_tokens, temperature } = parsed.data;

  // SSE headers — must set before writing any body
  res.setHeader('Content-Type',  'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection',    'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no'); // disable nginx buffering
  res.flushHeaders();

  function sendEvent(data: object) {
    res.write(`data: ${JSON.stringify(data)}\n\n`);
  }

  req.log.info({ model: env.LLM_MODEL }, 'SSE stream started');

  try {
    const stream = await llm.chat.completions.create({
      model: env.LLM_MODEL,
      stream: true,
      messages: [
        ...(system ? [{ role: 'system' as const, content: system }] : []),
        { role: 'user', content: prompt },
      ],
      max_tokens,
      temperature,
    });

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta?.content;
      if (delta) sendEvent({ type: 'delta', text: delta });
    }

    sendEvent({ type: 'done' });
    req.log.info('SSE stream completed');
  } catch (err) {
    // Send error over SSE so client can handle it; then end
    sendEvent({ type: 'error', message: (err as Error).message });
    req.log.error({ err }, 'SSE stream error');
  } finally {
    res.end();
  }
});
```

**Client-side consumption:**
```ts
const es = new EventSource('/generate/stream?...');  // or use fetch + ReadableStream
es.onmessage = ({ data }) => {
  const event = JSON.parse(data);
  if (event.type === 'delta') appendText(event.text);
  if (event.type === 'done')  es.close();
  if (event.type === 'error') handleError(event.message);
};
```

---

## 4. Retry and Timeout Logic

The OpenAI/Anthropic SDKs have built-in retry (`maxRetries`) and timeout (`timeout`). For custom retry with backoff around any async call:

```ts
async function withRetry<T>(
  fn: () => Promise<T>,
  maxAttempts = 3,
  baseDelayMs = 500,
): Promise<T> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (err: any) {
      lastError = err;
      const isRetryable = err?.status === 429 || err?.status >= 500;
      if (!isRetryable || attempt === maxAttempts) throw err;
      const delay = baseDelayMs * 2 ** (attempt - 1); // exponential backoff
      await new Promise(r => setTimeout(r, delay));
    }
  }
  throw lastError;
}
```

**When to retry:** 429 (rate limit), 502/503/504 (upstream unavailable). Never retry 400/401/422 (client errors).

---

## 5. Error Taxonomy and Handling

```ts
// src/middleware/errorHandler.ts
import { APIError } from 'openai'; // or Anthropic equivalent

export function errorHandler(err: any, req: any, res: any, next: any) {
  req.log?.error({ err }, 'Unhandled error');

  if (err instanceof APIError) {
    // LLM provider error
    const status = err.status ?? 502;
    return res.status(status).json({
      error: 'LLM_API_ERROR',
      message: err.message,
      code: err.code,
    });
  }

  if (err?.name === 'ZodError') {
    return res.status(400).json({ error: 'VALIDATION_ERROR', details: err.flatten() });
  }

  res.status(500).json({ error: 'INTERNAL_ERROR', message: 'Internal server error' });
}
```

| HTTP status from LLM | Meaning | Action |
|---|---|---|
| 400 | Bad request (invalid model, malformed messages) | Fix request; do not retry |
| 401 | Invalid API key | Check `LLM_API_KEY` env var |
| 422 | Content policy / context length exceeded | Truncate prompt or change model |
| 429 | Rate limit | Retry with exponential backoff |
| 500/502/503 | Provider outage | Retry; alert if persistent |

---

## 6. Prompt Construction Patterns

```ts
// Keep prompts as typed template functions — never inline raw strings in routes
function buildGenerationPrompt(input: { topic: string; tone: string }): string {
  return `Write a ${input.tone} summary about: ${input.topic}`;
}

// System prompt as a constant — version-controlled, not in env vars
const SYSTEM_PROMPT = `You are a helpful assistant. Be concise and accurate.
Return JSON when asked for structured output. Never make up facts.`;
```

**Prompt injection prevention:** Sanitize user input that will be embedded in system prompts. Treat user content as data, not instructions:
```ts
// Wrap user content in explicit delimiters
const safePrompt = `Process the following user input:
<user_input>
${userInput.replace(/<\/user_input>/g, '')}
</user_input>`;
```
