import { useState, useCallback } from 'react';

interface GenerateOptions {
  prompt: string;
  systemPrompt?: string;
  model?: string;
}

interface GenerateResult {
  raw: string;
  parsed?: Record<string, unknown>;
}

function tryParseJSON(text: string): Record<string, unknown> | undefined {
  const match = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/) ?? [null, text];
  try { return JSON.parse(match[1]!); } catch { return undefined; }
}

export function useAIGenerate(apiEndpoint = '/api/generate') {
  const [result, setResult]     = useState<GenerateResult | null>(null);
  const [isLoading, setLoading] = useState(false);
  const [error, setError]       = useState<string | null>(null);

  const generate = useCallback(async (options: GenerateOptions) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(apiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: options.prompt,
          system: options.systemPrompt,
          model:  options.model ?? 'gpt-4o-mini',
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as any).message ?? `API error ${res.status}`);
      }

      const { text } = await res.json();
      setResult({ raw: text, parsed: tryParseJSON(text) });
    } catch (err: any) {
      setError(err.message ?? 'Generation failed');
    } finally {
      setLoading(false);
    }
  }, [apiEndpoint]);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setLoading(false);
  }, []);

  return { generate, result, isLoading, error, reset };
}
