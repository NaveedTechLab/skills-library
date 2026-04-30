import { useState, useMemo } from 'react';

export interface SortState { key: string; dir: 'asc' | 'desc'; }

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
      (searchKeys.length ? searchKeys : Object.keys(row) as (keyof T)[])
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
  const rows = useMemo(
    () => sorted.slice((page - 1) * pageSize, page * pageSize),
    [sorted, page, pageSize]
  );

  function toggleSort(key: string) {
    setSort(prev => prev?.key === key
      ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
      : { key, dir: 'asc' }
    );
    setPage(1);
  }

  function updateSearch(value: string) { setSearch(value); setPage(1); }

  return { rows, sort, toggleSort, search, setSearch: updateSearch, page, setPage, totalPages, totalRows: sorted.length };
}
