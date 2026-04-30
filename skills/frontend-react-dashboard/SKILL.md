---
name: frontend-react-dashboard
description: "Build responsive React 18+ dashboards using hooks, TailwindCSS, charts, tables, and state management. Use when the user needs to: (1) build a dashboard layout with sidebar and KPI stat cards using Tailwind responsive classes, (2) add data visualizations with Recharts or Chart.js (line, bar, pie, area), (3) implement a data table with sorting, filtering, and pagination, (4) add dark mode with localStorage persistence and system preference detection, (5) integrate JSON data sources without hardcoding values in JSX. Triggers on keywords like: React dashboard, Tailwind dashboard, Recharts, Chart.js, data table, dark mode, KPI cards, responsive layout, sorting, filtering, pagination."
---

# Frontend React Dashboard

Build data-driven, responsive dashboards from external data sources — never from JSX literals.

## Build Workflow

```
1. Set up Tailwind with darkMode: 'class' in tailwind.config.js
2. Create layout (DashboardLayout: sidebar + main) with responsive breakpoints
3. Wire useDarkMode hook — toggle class on <html>, persist to localStorage
4. Fetch/import data via hook — never inline in JSX
5. Build stat cards (StatCard) from data props
6. Add chart panels (ChartPanel) with ResponsiveContainer
7. Add DataTable with useSortFilter hook
```

**Constraints — enforce always:**
- Every component is a function; `class` keyword never appears in component definitions
- All data passed as props or fetched via hooks; no object/array literals in JSX render output

---

## Boilerplate Template

Complete scaffold in `assets/dashboard-template/`. Files:

```
dashboard-template/src/
├── components/
│   ├── DashboardLayout.tsx   Sidebar + main content, responsive
│   ├── StatCard.tsx          KPI metric card (value, label, delta)
│   ├── ChartPanel.tsx        Recharts wrapper with ResponsiveContainer
│   └── DataTable.tsx         Sortable + filterable + paginated table
├── hooks/
│   ├── useDarkMode.ts        Dark mode toggle + localStorage persistence
│   ├── useTableData.ts       Sort, filter, paginate state machine
│   └── useDataFetch.ts       Generic JSON fetch hook (loading, error, data)
├── data/
│   └── sample.json           Shape example — replace with real source
└── tailwind.config.js        darkMode: 'class' + custom breakpoints
```

---

## 1. Tailwind Responsive Breakpoints

```
Mobile:  default (< 768px)   — single column, collapsed sidebar
Tablet:  md: (768px+)        — 2-column grid
Desktop: lg: (1024px+)       — full sidebar visible, 3-4 columns
Wide:    xl: (1440px+)       — wider content, larger charts
```

```tsx
// Responsive grid pattern for stat cards
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-4 gap-4 md:gap-6">
  {metrics.map(m => <StatCard key={m.id} {...m} />)}
</div>
```

---

## 2. Dark Mode

```ts
// All Tailwind dark: variants work when <html class="dark"> is present
// See assets/dashboard-template/src/hooks/useDarkMode.ts for full hook
const { isDark, toggle } = useDarkMode();

// Component usage
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
```

---

## 3. Chart Selection

| Need | Component |
|---|---|
| Trend over time | `<LineChart>` with `<Line>` |
| Category comparison | `<BarChart>` with `<Bar>` |
| Part-of-whole | `<PieChart>` or `<RadialBarChart>` |
| Volume + trend | `<AreaChart>` with `<Area>` |
| Multi-metric | `<ComposedChart>` |

All charts must be wrapped in `<ResponsiveContainer width="100%" height={300}>`.

For full Recharts and Chart.js patterns, see [references/charts.md](references/charts.md).

---

## 4. Data Integration Rule

Data enters through one of three patterns — never through JSX literals:

```ts
// Pattern A — JSON import (static)
import data from '../data/metrics.json';

// Pattern B — fetch hook (dynamic)
const { data, isLoading, error } = useDataFetch('/api/metrics');

// Pattern C — prop drilling from parent fetch
<DataTable rows={rows} columns={columns} />
```

---

## Resources

- [references/charts.md](references/charts.md) — Recharts components, Chart.js setup, responsive patterns, dark-mode chart colors
- [references/table.md](references/table.md) — useTableData hook, DataTable component, column definitions, filter patterns
- [references/dark-mode.md](references/dark-mode.md) — useDarkMode hook, system preference detection, Tailwind class strategy, color palette
- `assets/dashboard-template/` — Complete boilerplate to copy and adapt
