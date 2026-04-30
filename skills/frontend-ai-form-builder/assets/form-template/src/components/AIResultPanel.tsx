import React from 'react';
import { exportToPdf } from '../lib/exportPdf';
import '../styles/print.css';

interface GenerateResult {
  raw: string;
  parsed?: Record<string, unknown>;
}

interface AIResultPanelProps {
  result: GenerateResult | null;
  isLoading: boolean;
  error: string | null;
  title?: string;
  filename?: string;
}

export function AIResultPanel({
  result, isLoading, error,
  title = 'Generated Report',
  filename = 'report.pdf',
}: AIResultPanelProps) {
  if (isLoading) return (
    <div style={{ textAlign: 'center', padding: 64 }}>
      <div style={{
        width: 40, height: 40, border: '3px solid #e5e7eb',
        borderTopColor: '#6366f1', borderRadius: '50%',
        animation: 'spin 0.8s linear infinite', margin: '0 auto',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <p style={{ color: '#6b7280', marginTop: 16 }}>Generating your report...</p>
    </div>
  );

  if (error) return (
    <div style={{
      background: '#fef2f2', border: '1px solid #fecaca',
      borderRadius: 8, padding: 16,
    }}>
      <strong style={{ color: '#dc2626' }}>Generation failed</strong>
      <p style={{ margin: '4px 0 0', color: '#7f1d1d', fontSize: 14 }}>{error}</p>
    </div>
  );

  if (!result) return null;

  return (
    <div>
      {/* Export controls — hidden in print */}
      <div className="no-print" style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
        <button
          onClick={() => exportToPdf('ai-result-panel', filename)}
          style={{
            padding: '8px 20px', background: '#6366f1', color: '#fff',
            border: 'none', borderRadius: 6, cursor: 'pointer',
          }}
        >
          Export PDF
        </button>
        <button
          onClick={() => window.print()}
          style={{
            padding: '8px 20px', background: '#fff',
            border: '1px solid #d1d5db', borderRadius: 6, cursor: 'pointer',
          }}
        >
          Print
        </button>
      </div>

      {/* Result content — targeted by PDF export */}
      <div id="ai-result-panel" style={{ background: '#fff', padding: 32 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>{title}</h2>
        <p style={{ fontSize: 12, color: '#9ca3af', marginBottom: 24 }}>
          Generated {new Date().toLocaleDateString()}
        </p>

        {result.parsed
          ? <StructuredOutput data={result.parsed} />
          : <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6 }}>{result.raw}</pre>
        }
      </div>
    </div>
  );
}

function StructuredOutput({ data }: { data: Record<string, unknown> }) {
  return (
    <div>
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="pdf-section" style={{ marginBottom: 24 }}>
          <h3 style={{
            fontSize: 15, fontWeight: 600, textTransform: 'capitalize',
            borderBottom: '1px solid #e5e7eb', paddingBottom: 6, marginBottom: 10,
          }}>
            {key.replace(/([A-Z])/g, ' $1').replace(/_/g, ' ').trim()}
          </h3>
          <FieldValue value={value} />
        </div>
      ))}
    </div>
  );
}

function FieldValue({ value }: { value: unknown }) {
  if (typeof value === 'string')   return <p style={{ margin: 0, lineHeight: 1.6 }}>{value}</p>;
  if (typeof value === 'number')   return <p style={{ margin: 0 }}>{value}</p>;
  if (Array.isArray(value)) return (
    <ul style={{ paddingLeft: 20, margin: 0 }}>
      {value.map((item, i) => (
        <li key={i} style={{ marginBottom: 6 }}>
          {typeof item === 'object' && item !== null
            ? <ObjectItem item={item as Record<string, unknown>} />
            : String(item)
          }
        </li>
      ))}
    </ul>
  );
  if (typeof value === 'object' && value !== null)
    return <ObjectItem item={value as Record<string, unknown>} />;
  return <span>{String(value)}</span>;
}

function ObjectItem({ item }: { item: Record<string, unknown> }) {
  const { title, description, priority, ...rest } = item;
  const priorityColor: Record<string, string> = { high: '#dc2626', medium: '#d97706', low: '#16a34a' };
  return (
    <div style={{ paddingLeft: 12, borderLeft: `3px solid ${priorityColor[priority as string] ?? '#6366f1'}` }}>
      {title && <strong style={{ fontSize: 14 }}>{String(title)}</strong>}
      {priority && <span style={{ fontSize: 11, color: priorityColor[priority as string] ?? '#6366f1', marginLeft: 8 }}>{String(priority).toUpperCase()}</span>}
      {description && <p style={{ margin: '4px 0 0', fontSize: 13 }}>{String(description)}</p>}
      {Object.entries(rest).map(([k, v]) => (
        <p key={k} style={{ margin: '2px 0', fontSize: 13 }}>
          <span style={{ color: '#9ca3af', textTransform: 'capitalize' }}>{k}: </span>
          {String(v)}
        </p>
      ))}
    </div>
  );
}
