import React from 'react';
import { ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { useDarkMode } from '../hooks/useDarkMode';

interface ChartPanelProps {
  title: string;
  data: Record<string, unknown>[];
  type?: 'line' | 'bar';
  dataKeys: Array<{ key: string; color?: string; label?: string }>;
  xKey: string;
  height?: number;
  formatY?: (v: number) => string;
}

const DEFAULT_COLORS = ['#6366f1', '#8b5cf6', '#06b6d4', '#f59e0b', '#10b981'];

export function ChartPanel({
  title, data, type = 'line', dataKeys, xKey,
  height = 300, formatY,
}: ChartPanelProps) {
  const { isDark } = useDarkMode();

  const colors = {
    grid:    isDark ? '#374151' : '#e5e7eb',
    text:    isDark ? '#9ca3af' : '#6b7280',
    tooltip: { bg: isDark ? '#1f2937' : '#fff', border: isDark ? '#374151' : '#e5e7eb', text: isDark ? '#f9fafb' : '#111827' },
  };

  const tickStyle = { fill: colors.text, fontSize: 12 };
  const tooltipStyle = { background: colors.tooltip.bg, borderColor: colors.tooltip.border, color: colors.tooltip.text, fontSize: 13 };

  const commonProps = {
    data,
    margin: { top: 8, right: 16, left: 0, bottom: 0 },
  };

  const axisElements = (
    <>
      <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} />
      <XAxis dataKey={xKey} tick={tickStyle} axisLine={false} tickLine={false} />
      <YAxis tick={tickStyle} axisLine={false} tickLine={false} tickFormatter={formatY} />
      <Tooltip contentStyle={tooltipStyle} formatter={(v: unknown) => formatY ? formatY(Number(v)) : v} />
      <Legend wrapperStyle={{ fontSize: 12 }} />
    </>
  );

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        {type === 'bar' ? (
          <BarChart {...commonProps}>
            {axisElements}
            {dataKeys.map((dk, i) => (
              <Bar key={dk.key} dataKey={dk.key} name={dk.label ?? dk.key}
                fill={dk.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length]}
                radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        ) : (
          <LineChart {...commonProps}>
            {axisElements}
            {dataKeys.map((dk, i) => (
              <Line key={dk.key} type="monotone" dataKey={dk.key} name={dk.label ?? dk.key}
                stroke={dk.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length]}
                strokeWidth={2} dot={false} />
            ))}
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
