# AI Integration Reference

## Table of Contents
1. [useAIGenerate Hook](#1-useaigenerate-hook)
2. [Prompt Construction from Form Data](#2-prompt-construction-from-form-data)
3. [Structured JSON Response Parsing](#3-structured-json-response-parsing)
4. [Streaming with SSE](#4-streaming-with-sse)
5. [AIResultPanel Component](#5-airesultpanel-component)
6. [Error and Loading States](#6-error-and-loading-states)

---

## 1. useAIGenerate Hook

```ts
// hooks/useAIGenerate.ts
import { useState, useCallback } from 'react';

interface GenerateOptions {
  prompt: string;
  systemPrompt?: string;
  model?: string;
  stream?: boolean;
}

interface GenerateResult {
  raw: string;
  parsed?: Record<string, unknown>;
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
        throw new Error(err.message ?? `API error ${res.status}`);
      }

      const { text } = await res.json();
      const parsed = tryParseJSON(text);
      setResult({ raw: text, parsed });
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

function tryParseJSON(text: string): Record<string, unknown> | undefined {
  // Extract JSON from markdown code blocks if present
  const match = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/) ?? [null, text];
  try { return JSON.parse(match[1]!); } catch { return undefined; }
}
```

---

## 2. Prompt Construction from Form Data

Prompt engineering for structured output — instruct the model to return JSON:

```ts
interface FormData {
  name: string;
  company: string;
  industry: string;
  goals: string;
  budget: number;
}

export function buildAnalysisPrompt(data: FormData): string {
  return `Analyze the following business information and generate a structured report.

**Company:** ${data.company}
**Industry:** ${data.industry}
**Goals:** ${data.goals}
**Budget:** $${data.budget.toLocaleString()}

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{
  "summary": "2-3 sentence executive summary",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "recommendations": [
    { "title": "recommendation title", "description": "detailed description", "priority": "high|medium|low" }
  ],
  "nextSteps": ["step 1", "step 2", "step 3"],
  "estimatedTimeline": "e.g. 3-6 months"
}`;
}

export const SYSTEM_PROMPT = `You are a business strategy consultant.
Always respond with valid JSON only. Never include markdown, prose, or code fences outside the JSON.
Be specific and actionable in recommendations.`;
```

**Key pattern:** Ask for a specific JSON schema in the prompt. Use `tryParseJSON` (Section 1) to extract it even if the model wraps it in code fences.

---

## 3. Structured JSON Response Parsing

Render parsed JSON as formatted sections:

```tsx
interface AnalysisResult {
  summary: string;
  strengths: string[];
  recommendations: Array<{ title: string; description: string; priority: 'high' | 'medium' | 'low' }>;
  nextSteps: string[];
  estimatedTimeline: string;
}

const PRIORITY_COLOR = { high: '#dc2626', medium: '#d97706', low: '#16a34a' };

export function AnalysisOutput({ result }: { result: AnalysisResult }) {
  return (
    <div>
      <Section title="Executive Summary">
        <p>{result.summary}</p>
      </Section>

      <Section title="Strengths">
        <ul>{result.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
      </Section>

      <Section title="Recommendations">
        {result.recommendations.map((r, i) => (
          <div key={i} style={{ marginBottom: 12, paddingLeft: 12, borderLeft: `3px solid ${PRIORITY_COLOR[r.priority]}` }}>
            <strong>{r.title}</strong>
            <span style={{ fontSize: 11, color: PRIORITY_COLOR[r.priority], marginLeft: 8 }}>{r.priority.toUpperCase()}</span>
            <p style={{ margin: '4px 0 0', fontSize: 14 }}>{r.description}</p>
          </div>
        ))}
      </Section>

      <Section title="Next Steps">
        <ol>{result.nextSteps.map((s, i) => <li key={i}>{s}</li>)}</ol>
      </Section>

      <Section title="Estimated Timeline">
        <p>{result.estimatedTimeline}</p>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, borderBottom: '1px solid #e5e7eb', paddingBottom: 4 }}>{title}</h3>
      {children}
    </div>
  );
}
```

---

## 4. Streaming with SSE

For long AI responses, stream tokens to the UI:

```ts
export async function generateStreaming(
  prompt: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
  apiEndpoint = '/api/generate/stream'
) {
  const res = await fetch(apiEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });

  if (!res.ok || !res.body) { onError(`API error ${res.status}`); return; }

  const reader  = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const lines = decoder.decode(value).split('\n');
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const data = line.slice(6);
      if (data === '[DONE]') { onDone(); return; }
      try {
        const { text } = JSON.parse(data);
        if (text) onChunk(text);
      } catch {}
    }
  }
  onDone();
}
```

Hook usage with streaming:
```ts
const [streamText, setStreamText] = useState('');
await generateStreaming(
  prompt,
  (chunk) => setStreamText(prev => prev + chunk),
  () => setLoading(false),
  (err) => { setError(err); setLoading(false); }
);
```

---

## 5. AIResultPanel Component

```tsx
export function AIResultPanel({ result, isLoading, error }: {
  result: GenerateResult | null;
  isLoading: boolean;
  error: string | null;
}) {
  if (isLoading) return (
    <div style={{ textAlign: 'center', padding: 48 }}>
      <div className="spinner" />
      <p style={{ color: '#6b7280', marginTop: 16 }}>Generating your report...</p>
    </div>
  );

  if (error) return (
    <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: 16 }}>
      <strong style={{ color: '#dc2626' }}>Generation failed</strong>
      <p style={{ margin: '4px 0 0', color: '#7f1d1d', fontSize: 14 }}>{error}</p>
    </div>
  );

  if (!result) return null;

  return (
    <div id="ai-result-panel" style={{ background: '#fff', padding: 32 }}>
      {result.parsed
        ? <AnalysisOutput result={result.parsed as AnalysisResult} />
        : <pre style={{ whiteSpace: 'pre-wrap', fontSize: 14 }}>{result.raw}</pre>
      }
    </div>
  );
}
```

The `id="ai-result-panel"` attribute is required by the PDF export utility.

---

## 6. Error and Loading States

| State | UI Pattern |
|---|---|
| Loading (non-stream) | Spinner + "Generating..." message — disable all buttons |
| Loading (stream) | Streaming text renders incrementally — show cursor animation |
| API error (4xx) | Inline error banner with message — allow retry |
| Parse error (bad JSON) | Fall back to rendering `result.raw` as preformatted text |
| Network error | "Could not connect to server" — suggest checking connection |
