# Data Table Reference

## Table of Contents
1. [useTableData Hook](#1-usetabledata-hook)
2. [Column Definition Pattern](#2-column-definition-pattern)
3. [DataTable Component](#3-datatable-component)
4. [Filter Patterns](#4-filter-patterns)
5. [Sorting Indicator](#5-sorting-indicator)

---

## 1. useTableData Hook

Manages sort, filter, and pagination state. Data enters as a prop — never hardcoded.

```ts
// hooks/useTableData.ts
import { useState, useMemo } from 'react';

export interface SortState {
  key: string;
  dir: 'asc' | 'desc';
}

export function useTableData<T extends Record<string, unknown>>(
  data: T[],
  options: { pageSize?: number; searchKeys?: (keyof T)[] } = {}
) {
  const { pageSize = 20, searchKeys = [] } = options;
  const [sort, setSort]     = useState<SortState | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage]     = useState(1);

  const filtered = useMemo(() => {
    if (!search) return data;
    const q = search.toLowerCase();
    return data.filter(row =>
      (searchKeys.length > 0 ? searchKeys : Object.keys(row) as (keyof T)[])
        .some(k => String(row[k] ?? '').toLowerCase().includes(q))
    );
  }, [data, search, searchKeys]);

  const sorted = useMemo(() => {
    if (!sort) return filtered;
    return [...filtered].sort((a, b) => {
      const av = a[sort.key], bv = b[sort.key];
      if (av === bv) return 0;
      const cmp = av == null ? -1 : bv == null ? 1
        : typeof av === 'number' && typeof bv === 'number' ? av - bv
        : String(av).localeCompare(String(bv));
      return sort.dir === 'asc' ? cmp : -cmp;
    });
  }, [filtered, sort]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const paginated  = useMemo(
    () => sorted.slice((page - 1) * pageSize, page * pageSize),
    [sorted, page, pageSize]
  );

  function toggleSort(key: string) {
    setSort(prev =>
      prev?.key === key
        ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: 'asc' }
    );
    setPage(1);
  }

  function updateSearch(value: string) {
    setSearch(value);
    setPage(1);
  }

  return {
    rows: paginated,
    sort, toggleSort,
    search, setSearch: updateSearch,
    page, setPage,
    totalPages,
    totalRows: sorted.length,
  };
}
```

---

## 2. Column Definition Pattern

```ts
export interface ColumnDef<T> {
  key:       keyof T;
  header:    string;
  sortable?: boolean;
  width?:    string;           // Tailwind width class e.g. 'w-32'
  render?:   (value: T[keyof T], row: T) => React.ReactNode;
}

// Example column definitions — defined outside the component, not inline
const CAMPAIGN_COLUMNS: ColumnDef<Campaign>[] = [
  { key: 'name',     header: 'Campaign',   sortable: true, width: 'w-48' },
  { key: 'spend',    header: 'Spend',      sortable: true, render: (v) => `$${Number(v).toLocaleString()}` },
  { key: 'revenue',  header: 'Revenue',    sortable: true, render: (v) => `$${Number(v).toLocaleString()}` },
  { key: 'roas',     header: 'ROAS',       sortable: true, render: (v) => `${Number(v).toFixed(2)}x` },
  { key: 'status',   header: 'Status',     render: (v) => <StatusBadge status={String(v)} /> },
];
```

**Rule:** Define column arrays as module-level constants or `useMemo` — never as JSX literals.

---

## 3. DataTable Component

```tsx
// components/DataTable.tsx
import { ColumnDef, useTableData } from '../hooks/useTableData';

interface DataTableProps<T extends Record<string, unknown>> {
  data: T[];
  columns: ColumnDef<T>[];
  searchKeys?: (keyof T)[];
  pageSize?: number;
  title?: string;
}

export function DataTable<T extends Record<string, unknown>>({
  data, columns, searchKeys, pageSize = 20, title,
}: DataTableProps<T>) {
  const { rows, sort, toggleSort, search, setSearch, page, setPage, totalPages, totalRows } =
    useTableData(data, { pageSize, searchKeys });

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 border-b border-gray-200 dark:border-gray-700">
        {title && <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>}
        <input
          type="text"
          placeholder="Search..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full sm:w-64 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              {columns.map(col => (
                <th
                  key={String(col.key)}
                  onClick={col.sortable ? () => toggleSort(String(col.key)) : undefined}
                  className={`px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider ${col.sortable ? 'cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-200' : ''} ${col.width ?? ''}`}
                >
                  <span className="flex items-center gap-1">
                    {col.header}
                    {col.sortable && (
                      <span className="text-gray-300 dark:text-gray-600">
                        {sort?.key === String(col.key) ? (sort.dir === 'asc' ? '↑' : '↓') : '↕'}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {rows.length === 0 ? (
              <tr><td colSpan={columns.length} className="px-4 py-8 text-center text-gray-400">No results found</td></tr>
            ) : rows.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors">
                {columns.map(col => (
                  <td key={String(col.key)} className="px-4 py-3 text-gray-900 dark:text-gray-100">
                    {col.render ? col.render(row[col.key], row) : String(row[col.key] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {totalRows} results — page {page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="px-3 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700">
              Prev
            </button>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="px-3 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700">
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## 4. Filter Patterns

**Dropdown filter (category)**:

```tsx
function StatusFilter({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      className="px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
      <option value="">All statuses</option>
      <option value="active">Active</option>
      <option value="paused">Paused</option>
      <option value="archived">Archived</option>
    </select>
  );
}
```

For multi-column filtering, add a `filters` state to `useTableData` and apply in the `useMemo` filtered step:
```ts
const filtered = useMemo(() => {
  return data
    .filter(row => !search || searchKeys.some(k => String(row[k]).toLowerCase().includes(search.toLowerCase())))
    .filter(row => !statusFilter || row.status === statusFilter);
}, [data, search, statusFilter]);
```

---

## 5. Sorting Indicator

```tsx
function SortIcon({ active, dir }: { active: boolean; dir: 'asc' | 'desc' }) {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" className={active ? 'text-indigo-500' : 'text-gray-300 dark:text-gray-600'}>
      <path d="M6 2L9 6H3L6 2Z" fill={active && dir === 'asc' ? 'currentColor' : '#d1d5db'} />
      <path d="M6 10L3 6H9L6 10Z" fill={active && dir === 'desc' ? 'currentColor' : '#d1d5db'} />
    </svg>
  );
}
```
