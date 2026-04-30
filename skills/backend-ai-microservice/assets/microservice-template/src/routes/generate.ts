import { Router } from 'express';
import { z } from 'zod';
import OpenAI from 'openai';
import { env } from '../config/env';

const router = Router();

const llm = new OpenAI({
  apiKey: env.LLM_API_KEY,
  baseURL: env.LLM_BASE_URL,
  timeout: 30_000,
  maxRetries: 2,
});

const GenerateSchema = z.object({
  prompt:      z.string().min(1).max(8000),
  system:      z.string().optional(),
  max_tokens:  z.coerce.number().int().min(1).max(4096).default(1024),
  temperature: z.coerce.number().min(0).max(2).default(0.7),
});

// POST /generate — batch (waits for full response)
router.post('/', async (req, res, next) => {
  const parsed = GenerateSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: 'VALIDATION_ERROR', details: parsed.error.flatten() });
  }

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
    req.log.info({ usage: completion.usage }, 'LLM request completed');
    res.json({ text, usage: completion.usage });
  } catch (err) {
    next(err);
  }
});

// POST /generate/stream — SSE streaming
router.post('/stream', async (req, res, next) => {
  const parsed = GenerateSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: 'VALIDATION_ERROR', details: parsed.error.flatten() });
  }

  const { prompt, system, max_tokens, temperature } = parsed.data;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
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
  } catch (err: any) {
    sendEvent({ type: 'error', message: err.message ?? 'Stream error' });
    req.log.error({ err }, 'SSE stream error');
  } finally {
    res.end();
  }
});

export { router as generateRouter };
