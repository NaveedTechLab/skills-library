# Dark Mode Reference

## Table of Contents
1. [Tailwind Configuration](#1-tailwind-configuration)
2. [useDarkMode Hook](#2-usedarkmode-hook)
3. [System Preference Detection](#3-system-preference-detection)
4. [Dark Mode Toggle Component](#4-dark-mode-toggle-component)
5. [Color Palette Conventions](#5-color-palette-conventions)

---

## 1. Tailwind Configuration

```js
// tailwind.config.js — darkMode must be 'class', not 'media'
// 'class' mode: dark: variants activate when <html> has class="dark"
// This gives programmatic control (localStorage persistence + toggle)
module.exports = {
  darkMode: 'class',
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      screens: {
        'xl': '1440px',   // override default 1280px → 1440px wide
      },
    },
  },
};
```

**Why 'class' not 'media':** `'media'` mode follows OS preference only — no toggle button, no persistence. `'class'` enables both: respect OS preference on first load, then let user override.

---

## 2. useDarkMode Hook

```ts
// hooks/useDarkMode.ts
import { useState, useEffect } from 'react';

const STORAGE_KEY = 'dashboard-theme';

function getSystemPreference(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function getInitialDark(): boolean {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) return stored === 'dark';
  } catch {}
  return getSystemPreference();
}

export function useDarkMode() {
  const [isDark, setIsDark] = useState<boolean>(() => {
    // SSR guard — default to false on server
    if (typeof window === 'undefined') return false;
    return getInitialDark();
  });

  // Apply class to <html> and persist
  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    try {
      localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light');
    } catch {}
  }, [isDark]);

  const toggle  = () => setIsDark(v => !v);
  const setDark  = () => setIsDark(true);
  const setLight = () => setIsDark(false);

  return { isDark, toggle, setDark, setLight };
}
```

**Mount order matters:** Call `useDarkMode` at the app root (e.g., `App.tsx` or `Layout.tsx`) and pass `isDark`/`toggle` down, or use a Context. Never call it in multiple components — the `localStorage.setItem` side effect will fire multiple times.

---

## 3. System Preference Detection

Listen for OS theme changes while the app is open:

```ts
useEffect(() => {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored !== null) return; // user has explicitly chosen — respect their choice

  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
  mq.addEventListener('change', handler);
  return () => mq.removeEventListener('change', handler);
}, []);
```

Add this inside `useDarkMode` after the main `useEffect`.

---

## 4. Dark Mode Toggle Component

```tsx
interface DarkModeToggleProps {
  isDark: boolean;
  onToggle: () => void;
}

export function DarkModeToggle({ isDark, onToggle }: DarkModeToggleProps) {
  return (
    <button
      onClick={onToggle}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
    >
      {isDark ? (
        // Sun icon
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
        </svg>
      ) : (
        // Moon icon
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      )}
    </button>
  );
}
```

---

## 5. Color Palette Conventions

Use these Tailwind class pairs consistently across all dashboard components:

| Element | Light | Dark |
|---|---|---|
| Page background | `bg-gray-50` | `dark:bg-gray-950` |
| Card/panel background | `bg-white` | `dark:bg-gray-800` |
| Secondary surface | `bg-gray-100` | `dark:bg-gray-700` |
| Border | `border-gray-200` | `dark:border-gray-700` |
| Primary text | `text-gray-900` | `dark:text-gray-100` |
| Secondary text | `text-gray-600` | `dark:text-gray-400` |
| Muted text | `text-gray-400` | `dark:text-gray-600` |
| Input background | `bg-white` | `dark:bg-gray-700` |
| Hover row | `hover:bg-gray-50` | `dark:hover:bg-gray-750` |
| Divider | `divide-gray-100` | `dark:divide-gray-700` |

**Accent color:** `text-indigo-600 dark:text-indigo-400` for links and interactive elements.

Avoid arbitrary dark values — use only the palette above for consistency. If a color isn't in the table, add a new row rather than using a one-off value.
