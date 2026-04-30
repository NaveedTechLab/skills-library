# Common SaaS Dashboard Design Patterns (2026)

## Table of Contents

1. [Dashboard Layouts](#dashboard-layouts)
2. [Data Visualization Cards](#data-visualization-cards)
3. [Navigation Patterns](#navigation-patterns)
4. [Table Designs](#table-designs)
5. [Form Patterns](#form-patterns)

---

## Dashboard Layouts

### Pattern 1: Metric Grid Dashboard

**Use Case**: Executive dashboards, analytics overviews

**Structure**:
```
┌─────────────────────────────────────────────────────────┐
│  Header (Logo, Search, Profile)                         │
├───────┬─────────────────────────────────────────────────┤
│ Nav   │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐              │
│ 240px │  │KPI 1│ │KPI 2│ │KPI 3│ │KPI 4│  (4 columns)│
│       │  └─────┘ └─────┘ └─────┘ └─────┘              │
│       │  ┌───────────────┐ ┌───────────────┐          │
│       │  │ Chart Area 1  │ │ Chart Area 2  │          │
│       │  │  (Line chart) │ │  (Bar chart)  │          │
│       │  └───────────────┘ └───────────────┘          │
│       │  ┌─────────────────────────────────┐          │
│       │  │  Data Table (Recent Activity)   │          │
│       │  └─────────────────────────────────┘          │
└───────┴─────────────────────────────────────────────────┘
```

**Visual Specs**:
- KPI cards: 24px padding, 16px border-radius, glassmorphism
- Chart areas: 32px padding, minimal grid lines, accent color highlights
- Grid gap: 20px between cards
- Responsive: 4 → 2 → 1 column on smaller screens

---

### Pattern 2: Sidebar Focus Layout

**Use Case**: Settings pages, detailed forms, admin panels

**Structure**:
```
┌──────────────────────────────────────────────┐
│  Top Nav (Breadcrumbs, Actions)             │
├────────┬─────────────────────────────────────┤
│ Side   │  ┌───────────────────────────────┐ │
│ Menu   │  │  Main Content Panel           │ │
│        │  │  (Form or Detail View)        │ │
│ 200px  │  │                               │ │
│        │  └───────────────────────────────┘ │
│        │  [Action Buttons: Cancel, Save]   │
└────────┴─────────────────────────────────────┘
```

**Visual Specs**:
- Sidebar: Subtle background, 16px item padding, active state with accent border-left
- Main panel: White/glass card with 40px padding
- Sticky header with breadcrumbs

---

## Data Visualization Cards

### KPI Metric Card

```
┌─────────────────────────────┐
│ Total Revenue        [Icon] │  ← Title (14px, 60% opacity)
│                             │
│ $127,563            ↗ +12% │  ← Value (32px bold) + Trend
│                             │
│ ▁▂▃▄▅▆▇█ ▄▅▆      (sparkline)│  ← Mini chart
│                             │
│ vs last month: $113,895     │  ← Context (12px, 60% opacity)
└─────────────────────────────┘
```

**Specs**:
- Card: 280×200px, glassmorphism, level 1 shadow
- Trend positive: `#10B981` (green), negative: `#EF4444` (red)
- Sparkline: 2px stroke, accent color with 20% opacity fill
- Hover: Lift 4px, show detailed tooltip

---

### Chart Card (Line/Bar/Donut)

```
┌──────────────────────────────────────┐
│ Sales by Region          [⋮ Menu]   │
│ ────────────────────────────────────│
│                                      │
│     Chart Area                       │
│     - Clean axes                     │
│     - Soft grid lines                │
│     - Accent color highlights        │
│     - Tooltips on hover              │
│                                      │
│ [Legend: ● North ● South ● East]    │
└──────────────────────────────────────┘
```

**Specs**:
- Chart card: 560×400px, 32px padding
- Axes: 1px solid `rgba(255, 255, 255, 0.1)`
- Grid lines: Dashed, 0.5px, 5% opacity
- Data points: 8px radius circles with glow on hover
- Legend: Horizontal, 12px font, inline with icons

---

## Navigation Patterns

### Vertical Sidebar Navigation

```
┌────────────────┐
│ [Logo]         │  ← Brand (48px height)
│                │
│ ━━━━━━━━━━━━━ │  ← Divider
│                │
│ 🏠 Dashboard   │  ← Active (accent bg, bold)
│ 📊 Analytics   │
│ 👥 Customers   │
│ ⚙️ Settings    │
│                │
│ ━━━━━━━━━━━━━ │
│                │
│ [User Profile] │  ← Bottom (avatar + name)
└────────────────┘
```

**Specs**:
- Width: 240px-280px
- Item height: 44px, 12px padding, 8px border-radius
- Active state: Accent background (10% opacity), accent border-left (3px)
- Hover: Background 5% opacity
- Icons: 20px, left-aligned with 12px gap

---

### Top Horizontal Navigation

```
┌─────────────────────────────────────────────────────┐
│ [Logo]  Dashboard  Analytics  Reports  [Search] 👤 │
└─────────────────────────────────────────────────────┘
```

**Specs**:
- Height: 64px-72px
- Items: 16px padding, 8px gap
- Active: Border-bottom (3px accent color)
- Glass background with backdrop-blur

---

## Table Designs

### Modern Data Table

```
┌────────────────────────────────────────────────────────┐
│ Customers (1,247)           [Search] [Filter] [Export]│
├────────┬──────────┬──────────┬──────────┬─────────────┤
│ Name   │ Email    │ Status   │ Revenue  │ Actions     │  ← Header (bold, 60% opacity)
├────────┼──────────┼──────────┼──────────┼─────────────┤
│ John D │ john@... │ ● Active │ $12,340  │ [⋮]         │
│ Sarah M│ sarah@...│ ● Active │ $8,920   │ [⋮]         │
│ Mike R │ mike@... │ ○ Idle   │ $3,450   │ [⋮]         │
└────────┴──────────┴──────────┴──────────┴─────────────┘
```

**Specs**:
- Row height: 56px
- Header: 48px, sticky on scroll, glass background
- Cell padding: 16px horizontal, 12px vertical
- Row hover: Background 3% opacity
- Borders: 1px solid `rgba(255, 255, 255, 0.08)` between rows
- Status badges: 8px dot + 12px text, colored by status
- Pagination: Bottom-right, 36px button height

---

## Form Patterns

### Modern Input Field

```
┌─────────────────────────────────────┐
│ Email Address                       │  ← Label (12px, 87% opacity)
│ ┌─────────────────────────────────┐ │
│ │ john@example.com            [✓] │ │  ← Input (44px height)
│ └─────────────────────────────────┘ │
│ Must be a valid email address       │  ← Helper (11px, 60% opacity)
└─────────────────────────────────────┘
```

**Specs**:
- Input height: 44px-48px
- Padding: 12px 16px
- Border-radius: 12px
- Border: 1px solid `rgba(255, 255, 255, 0.12)`
- Focus: Accent color border (2px), glow shadow
- Error state: Red border, red helper text
- Success: Green checkmark icon, green border

---

### Form Layout (Multi-field)

```
┌──────────────────────────────────────────┐
│ Create New Project                       │
│ ──────────────────────────────────────── │
│                                          │
│ [Project Name ─────────────────────────] │
│                                          │
│ [Description (textarea) ───────────────] │
│ [                                      ] │
│                                          │
│ ┌──────────────┐  ┌──────────────────┐  │
│ │ Start Date   │  │ End Date         │  │
│ └──────────────┘  └──────────────────┘  │
│                                          │
│ [Tags: #design #frontend] [+ Add]       │
│                                          │
│           [Cancel]  [Create Project]    │
└──────────────────────────────────────────┘
```

**Specs**:
- Field vertical gap: 20px
- Multi-column: Use CSS Grid with 20px gap
- Buttons: Right-aligned, 12px gap
- Card padding: 32px-40px

---

## Accessibility Guidelines

**For All Patterns**:
- Color contrast: Minimum 4.5:1 for text, 3:1 for UI components
- Focus states: 2px outline with 4px offset
- Keyboard navigation: Tab order follows visual flow
- ARIA labels: All interactive elements labeled
- Screen reader: Announce state changes (loading, error, success)
