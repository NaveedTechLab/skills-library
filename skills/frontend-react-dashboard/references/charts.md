# Charts Reference

## Table of Contents
1. [Recharts Setup and Patterns](#1-recharts-setup-and-patterns)
2. [Chart Types Quick Reference](#2-chart-types-quick-reference)
3. [Dark Mode Chart Colors](#3-dark-mode-chart-colors)
4. [Chart.js Alternative](#4-chartjs-alternative)
5. [Responsive Container Rules](#5-responsive-container-rules)

---

## 1. Recharts Setup and Patterns

```bash
npm install recharts
```

### Line Chart (trend over time)

```tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function TrendChart({ data }: { data: Array<{ date: string; value: number }> }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

### Bar Chart (category comparison)

```tsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function CategoryChart({ data }: { data: Array<{ name: string; revenue: number; cost: number }> }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip formatter={(value: number) => `$${value.toLocaleString()}`} />
        <Bar dataKey="revenue" fill="#6366f1" radius={[4, 4, 0, 0]} />
        <Bar dataKey="cost" fill="#a5b4fc" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

### Area Chart (volume over time)

```tsx
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

function AreaTrend({ data }: { data: Array<{ date: string; spend: number }> }) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Area type="monotone" dataKey="spend" stroke="#6366f1" fill="url(#spendGradient)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
```

### Pie Chart (part-of-whole)

```tsx
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe'];

function SharePie({ data }: { data: Array<{ name: string; value: number }> }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" outerRadius={100} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
          {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Pie>
        <Tooltip formatter={(v: number) => v.toLocaleString()} />
      </PieChart>
    </ResponsiveContainer>
  );
}
```

---

## 2. Chart Types Quick Reference

| Use case | Recharts component | Key props |
|---|---|---|
| Single metric trend | `LineChart` + `Line` | `type="monotone"`, `dot={false}` for dense data |
| Multi-series trend | `LineChart` + multiple `Line` | Different `stroke` per series |
| Grouped bars | `BarChart` + multiple `Bar` | Default side-by-side |
| Stacked bars | `BarChart` + `Bar stackId="a"` | Same `stackId` for stacking |
| Share of total | `PieChart` + `Pie` | `outerRadius`, `Cell` for colors |
| KPI gauge | `RadialBarChart` + `RadialBar` | `startAngle={180}`, `endAngle={0}` |
| Volume + line | `ComposedChart` + `Area` + `Line` | Mix types freely |

---

## 3. Dark Mode Chart Colors

Recharts doesn't read CSS variables — pass colors directly using the dark mode state:

```tsx
function useChartColors() {
  const { isDark } = useDarkMode();
  return {
    grid:    isDark ? '#374151' : '#e5e7eb',
    text:    isDark ? '#9ca3af' : '#6b7280',
    primary: '#6366f1',
    secondary: '#8b5cf6',
    tooltip: {
      bg:     isDark ? '#1f2937' : '#ffffff',
      border: isDark ? '#374151' : '#e5e7eb',
      text:   isDark ? '#f9fafb' : '#111827',
    },
  };
}

// Usage in chart
const colors = useChartColors();
<CartesianGrid stroke={colors.grid} />
<XAxis tick={{ fill: colors.text }} />
<Tooltip contentStyle={{ background: colors.tooltip.bg, borderColor: colors.tooltip.border, color: colors.tooltip.text }} />
```

---

## 4. Chart.js Alternative

Use when already in a Chart.js project or when animation control is important.

```bash
npm install chart.js react-chartjs-2
```

```tsx
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

function LineChartJS({ labels, values }: { labels: string[]; values: number[] }) {
  const data = {
    labels,
    datasets: [{
      label: 'Revenue',
      data: values,
      borderColor: '#6366f1',
      backgroundColor: 'rgba(99,102,241,0.1)',
      tension: 0.4,
      pointRadius: 0,
    }],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: { x: { grid: { display: false } } },
  };

  return <div style={{ height: 300 }}><Line data={data} options={options} /></div>;
}
```

---

## 5. Responsive Container Rules

- **Always** wrap Recharts charts in `<ResponsiveContainer width="100%" height={N}>` — never set a fixed pixel width
- The parent container must have a defined width (flex or grid child, not `width: auto` on a block)
- Set `height` as a number (px), not a percentage — percentage height requires a defined parent height
- On mobile, reduce chart height: `height={isMobile ? 200 : 300}` where `isMobile = useMediaQuery('(max-width: 768px)')`
