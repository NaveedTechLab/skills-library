import { useState, useEffect } from 'react';

interface FetchState<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useDataFetch<T>(url: string, options?: RequestInit): FetchState<T> {
  const [data, setData]         = useState<T | null>(null);
  const [isLoading, setLoading] = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [tick, setTick]         = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(url, options)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<T>;
      })
      .then(json => { if (!cancelled) setData(json); })
      .catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [url, tick]);

  return { data, isLoading, error, refetch: () => setTick(t => t + 1) };
}
