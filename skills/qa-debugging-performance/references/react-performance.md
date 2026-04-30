# React Performance Reference

## Table of Contents
1. [Diagnosing Re-renders](#1-diagnosing-re-renders)
2. [React.memo](#2-reactmemo)
3. [useMemo](#3-usememo)
4. [useCallback](#4-usecallback)
5. [Custom Hook Recipes](#5-custom-hook-recipes)
6. [Context Performance](#6-context-performance)
7. [List Rendering](#7-list-rendering)

---

## 1. Diagnosing Re-renders

**Tooling:**
- React DevTools Profiler: record interaction, inspect flame graph for unexpected renders
- `why-did-you-render` library: logs props/state diffs that triggered renders

**Inline debug technique:**
```jsx
// Temporary — remove after diagnosis
const renderCount = useRef(0);
console.log(`MyComponent render #${++renderCount.current}`, { props, state });
```

**Root cause categories:**
| Cause | Signal | Fix |
|---|---|---|
| New object/array reference each render | `{}` or `[]` literal in JSX or render body | `useMemo` |
| New function reference each render | Arrow fn in JSX or render body | `useCallback` |
| Parent re-renders with irrelevant state | Component has no changed props/state | `React.memo` |
| Expensive calculation inline | Profiler shows long "self time" | `useMemo` |
| High-frequency event update | Typing, scrolling, resizing | `useDebounce` / `useThrottle` |
| Context consumer re-renders on unrelated change | All consumers re-render on any context change | Split context |

---

## 2. React.memo

Skips re-render when all props are shallowly equal.

```jsx
// Wrap pure presentational components
const Avatar = React.memo(({ src, alt }) => (
  <img src={src} alt={alt} className="avatar" />
));

// Custom comparator for deep/partial equality
const UserCard = React.memo(
  ({ user }) => <div>{user.name}</div>,
  (prev, next) => prev.user.id === next.user.id
);
```

**When NOT to use React.memo:**
- Component always receives different props (memoization overhead with no benefit)
- Component is very cheap to render
- Props are complex objects that are always new references (fix the reference instead)

---

## 3. useMemo

Memoizes a computed value. Recalculates only when dependencies change.

```jsx
// Expensive computation
const sortedList = useMemo(
  () => items.slice().sort((a, b) => a.score - b.score),
  [items]
);

// Stable object reference (prevents child re-render)
const config = useMemo(
  () => ({ color: theme.primary, size: 'md' }),
  [theme.primary]
);
```

**Rule of thumb:** Use `useMemo` when:
1. The computation is measurably slow (>1ms), OR
2. The result is passed to a `React.memo` child as a prop

---

## 4. useCallback

Memoizes a function reference. Mainly useful when passing callbacks to memoized children.

```jsx
const handleSubmit = useCallback((event) => {
  event.preventDefault();
  onSave(formData);
}, [formData, onSave]);

// Pass to memoized child — without useCallback, child re-renders every time
<SubmitButton onClick={handleSubmit} />
```

**Avoid over-using:** `useCallback` only helps when the receiving component is wrapped in `React.memo` or uses the function as a `useEffect`/`useMemo` dependency.

---

## 5. Custom Hook Recipes

### useDebounce
```ts
import { useState, useEffect } from 'react';

export function useDebounce<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState<T>(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}
```

Usage:
```tsx
const debouncedSearch = useDebounce(searchTerm, 300);
useEffect(() => { fetchResults(debouncedSearch); }, [debouncedSearch]);
```

### useThrottle
```ts
import { useState, useRef, useEffect } from 'react';

export function useThrottle<T>(value: T, intervalMs: number): T {
  const [throttled, setThrottled] = useState<T>(value);
  const lastUpdated = useRef<number>(Date.now());

  useEffect(() => {
    const now = Date.now();
    if (now - lastUpdated.current >= intervalMs) {
      lastUpdated.current = now;
      setThrottled(value);
    } else {
      const timer = setTimeout(() => {
        lastUpdated.current = Date.now();
        setThrottled(value);
      }, intervalMs - (now - lastUpdated.current));
      return () => clearTimeout(timer);
    }
  }, [value, intervalMs]);

  return throttled;
}
```

### usePrevious
```ts
import { useRef, useEffect } from 'react';

export function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T>();
  useEffect(() => { ref.current = value; }, [value]);
  return ref.current;
}
```

---

## 6. Context Performance

Every consumer re-renders when any context value changes. For contexts with multiple values:

```tsx
// PROBLEM: UserContext holds user + theme; any change re-renders all consumers
const UserContext = createContext({ user, theme, setTheme });

// SOLUTION: Split into separate contexts
const UserContext = createContext(user);
const ThemeContext = createContext({ theme, setTheme });
```

Alternatively, memoize the context value:
```tsx
const value = useMemo(() => ({ user, updateUser }), [user, updateUser]);
return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
```

---

## 7. List Rendering

```jsx
// REQUIRED: stable, unique key (not array index for reorderable lists)
items.map(item => <Row key={item.id} data={item} />)

// For large lists (1000+ items): virtualization
import { FixedSizeList } from 'react-window';

<FixedSizeList height={600} itemCount={items.length} itemSize={50} width="100%">
  {({ index, style }) => (
    <div style={style}><Row data={items[index]} /></div>
  )}
</FixedSizeList>
```

**Key stability:** If keys change on every render (e.g., `key={Math.random()}`), React unmounts and remounts every item — this is a major performance bug.
