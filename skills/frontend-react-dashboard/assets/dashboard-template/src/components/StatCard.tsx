import React from 'react';

interface StatCardProps {
  label: string;
  value: string | number;
  delta?: number;       // percentage change — positive = good
  deltaLabel?: string;  // e.g. "vs last 30 days"
  icon?: React.ReactNode;
}

export function StatCard({ label, value, delta, deltaLabel, icon }: StatCardProps) {
  const isPositive = delta != null && delta >= 0;
  const deltaColor = delta == null ? '' : isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">{label}</span>
        {icon && <span className="text-gray-400 dark:text-gray-500">{icon}</span>}
      </div>

      <div className="flex items-end justify-between gap-2">
        <span className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </span>

        {delta != null && (
          <span className={`text-sm font-medium ${deltaColor} flex items-center gap-0.5`}>
            {isPositive ? '↑' : '↓'} {Math.abs(delta).toFixed(1)}%
          </span>
        )}
      </div>

      {deltaLabel && (
        <span className="text-xs text-gray-400 dark:text-gray-500">{deltaLabel}</span>
      )}
    </div>
  );
}
