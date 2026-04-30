import { useState, useEffect } from 'react';

const STORAGE_KEY = 'dashboard-theme';

export function useDarkMode() {
  const [isDark, setIsDark] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored !== null) return stored === 'dark';
    } catch {}
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    try { localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light'); } catch {}
  }, [isDark]);

  // Follow OS changes only if user hasn't set a preference
  useEffect(() => {
    if (localStorage.getItem(STORAGE_KEY) !== null) return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  return { isDark, toggle: () => setIsDark(v => !v) };
}
