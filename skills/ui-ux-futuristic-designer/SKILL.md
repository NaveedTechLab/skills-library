---
name: ui-ux-futuristic-designer
description: Design futuristic 2026-style UI with 3D depth, glassmorphism, soft shadows, and modern aesthetics. Use when users request UI/UX design guidance, dashboard layouts, SaaS interfaces, design systems, color palettes, typography recommendations, or need help creating modern, polished visual designs. Provides step-by-step design guidance without implementation code.
---

# UI/UX Futuristic Designer (2026 Style)

Design cutting-edge user interfaces optimized for modern SaaS dashboards with futuristic aesthetics.

## Core Design Philosophy

**2026 Design Principles:**
- **Depth over Flat**: Embrace 3D depth, layering, and spatial relationships
- **Glass & Blur**: Glassmorphism with frosted glass effects and soft transparency
- **Soft Shadows**: Multi-layered shadows for realistic depth perception
- **Micro-interactions**: Subtle animations that guide user attention
- **Breathing Space**: Generous padding and clear visual hierarchy

## Design Workflow

When a user requests UI/UX design, follow this structured approach:

### Step 1: Understand Context

Ask clarifying questions (max 3-4):
- What is the primary user action? (e.g., view data, create item, manage settings)
- What is the user's emotional state? (e.g., focused work, quick glance, relaxed browsing)
- What device/screen size? (desktop dashboard, mobile app, tablet)
- What brand personality? (professional, playful, minimal, bold)

### Step 2: Define Layout Structure

Provide a clear layout using spatial zones:

```
[EXAMPLE OUTPUT FORMAT]
┌─────────────────────────────────────────┐
│  [Header: 72px]                         │
├──────┬──────────────────────────────────┤
│ Nav  │  Main Content Area               │
│ 280px│  - Primary Section (60% width)   │
│      │  - Secondary Panel (40% width)   │
└──────┴──────────────────────────────────┘

Key spacing:
- Container padding: 24px-32px
- Section gaps: 20px-24px
- Card padding: 20px-24px
- Element spacing: 12px-16px
```

### Step 3: Visual Design System

#### Color System

Recommend a modern color palette:

**Background Layers:**
- Primary BG: `#0A0E1A` (deep navy-black)
- Surface 1: `rgba(255, 255, 255, 0.05)` (subtle glass)
- Surface 2: `rgba(255, 255, 255, 0.08)` (elevated glass)
- Surface 3: `rgba(255, 255, 255, 0.12)` (highest elevation)

**Accent Colors:**
- Primary: `#6366F1` (indigo) or `#8B5CF6` (purple) or `#06B6D4` (cyan)
- Success: `#10B981` (emerald)
- Warning: `#F59E0B` (amber)
- Error: `#EF4444` (red)

**Text Hierarchy:**
- Heading: `#FFFFFF` (100% opacity)
- Body: `rgba(255, 255, 255, 0.87)` (87% opacity)
- Secondary: `rgba(255, 255, 255, 0.60)` (60% opacity)
- Disabled: `rgba(255, 255, 255, 0.38)` (38% opacity)

#### Typography Scale

**Recommended Font Stacks:**
- **Headings**: Inter, SF Pro Display, Segoe UI, system-ui
- **Body**: Inter, SF Pro Text, Segoe UI, system-ui
- **Monospace**: JetBrains Mono, Fira Code, Consolas

**Type Scale (Major Third - 1.250 ratio):**
```
H1: 48px / 60px line-height (font-weight: 700)
H2: 40px / 52px (font-weight: 600)
H3: 32px / 44px (font-weight: 600)
H4: 24px / 32px (font-weight: 600)
Body Large: 18px / 28px (font-weight: 400)
Body: 16px / 24px (font-weight: 400)
Body Small: 14px / 20px (font-weight: 400)
Caption: 12px / 16px (font-weight: 500)
```

#### Glassmorphism Effects

Provide CSS-style specs for glass cards:

```
Card Style:
- Background: rgba(255, 255, 255, 0.08)
- Backdrop-filter: blur(12px) saturate(180%)
- Border: 1px solid rgba(255, 255, 255, 0.12)
- Border-radius: 16px-24px
- Box-shadow:
    0px 2px 4px rgba(0, 0, 0, 0.1),
    0px 8px 16px rgba(0, 0, 0, 0.15),
    inset 0px 1px 0px rgba(255, 255, 255, 0.1)
```

#### Shadow System

Define multi-layered shadows for depth:

**Elevation Levels:**
```
Level 1 (Cards):
  0px 2px 4px rgba(0, 0, 0, 0.1),
  0px 4px 8px rgba(0, 0, 0, 0.12)

Level 2 (Modals):
  0px 4px 8px rgba(0, 0, 0, 0.12),
  0px 12px 24px rgba(0, 0, 0, 0.16)

Level 3 (Dropdowns):
  0px 8px 16px rgba(0, 0, 0, 0.15),
  0px 16px 32px rgba(0, 0, 0, 0.20)

Level 4 (Floating):
  0px 12px 24px rgba(0, 0, 0, 0.18),
  0px 24px 48px rgba(0, 0, 0, 0.24)
```

### Step 4: Component Design Guidance

For each component requested, provide:

1. **Purpose**: What user need does this solve?
2. **Visual Specs**:
   - Dimensions (width × height)
   - Padding/margins
   - Colors (background, text, border)
   - Border-radius
   - Shadow elevation
3. **States**: Default, Hover, Active, Disabled, Loading
4. **Accessibility**: Color contrast ratios (WCAG AA minimum)

**Example Component Spec:**

```
Primary Button (Call-to-Action)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Purpose: Main user action (e.g., "Create", "Save", "Submit")

Dimensions:
- Height: 44px (touch-friendly)
- Padding: 12px 24px
- Min-width: 120px
- Border-radius: 12px

Colors:
- Background: Linear gradient(135deg, #6366F1, #8B5CF6)
- Text: #FFFFFF (font-weight: 600)
- Shadow: 0px 4px 12px rgba(99, 102, 241, 0.4)

States:
- Hover: Lift 2px, shadow grows to 0px 6px 16px
- Active: Slight scale(0.98)
- Disabled: opacity 0.5, no shadow, cursor not-allowed
- Loading: Spinner animation, text fades to 60%

Accessibility:
- Contrast ratio: 4.5:1 (WCAG AA)
- Focus outline: 2px solid #6366F1 with 4px offset
```

### Step 5: Advanced Features

#### 3D Depth & Parallax

When designing hero sections or feature showcases:

```
3D Card Effect:
- Transform: perspective(1000px) rotateX(2deg)
- Transition: transform 0.3s ease
- On hover: rotateX(0deg) translateY(-8px)
- Shadow expands on elevation
```

#### Micro-interactions

Suggest subtle animations:
- **Page transitions**: 0.3s ease-out fade + slide
- **Card hovers**: 0.2s ease scale(1.02) + shadow growth
- **Button clicks**: 0.1s ease scale(0.98) → scale(1)
- **Loading states**: Skeleton screens with shimmer (2s loop)

#### Data Visualization

For dashboards with charts:
- Use accent colors for data series
- Soft glows on hover (`box-shadow: 0 0 20px rgba(99, 102, 241, 0.6)`)
- Rounded corners on bars (8px border-radius)
- Glass background for chart containers

### Step 6: Responsive Breakpoints

Provide mobile-first breakpoints:

```
Mobile: 320px - 767px
  - Stack all columns
  - Reduce padding to 16px
  - Font scale down 10-15%
  - Collapse navigation to hamburger

Tablet: 768px - 1023px
  - 2-column layouts
  - Padding: 20px-24px
  - Show condensed navigation

Desktop: 1024px+
  - Full multi-column layouts
  - Padding: 24px-32px
  - Persistent side navigation
```

## Output Format

Always structure design guidance as:

```
## Design: [Component/Page Name]

### Layout
[ASCII diagram or description]

### Visual Specs
- Background: [color/gradient]
- Typography: [sizes and weights]
- Spacing: [padding/margins]
- Effects: [glassmorphism/shadows]

### Components
1. [Component Name]
   - Specs: [detailed specs]
   - States: [interaction states]

### Responsive Behavior
- Mobile: [adaptations]
- Tablet: [adaptations]
- Desktop: [full experience]

### Accessibility Notes
- [Color contrast checks]
- [Keyboard navigation]
- [Screen reader labels]
```

## Constraints

**Never provide:**
- ❌ Implementation code (React, HTML, CSS)
- ❌ Backend logic or API design
- ❌ Database schemas
- ❌ Framework-specific instructions

**Always provide:**
- ✅ Visual specifications with exact values
- ✅ Color codes (hex/rgba)
- ✅ Spacing in pixels
- ✅ Component states and transitions
- ✅ Accessibility guidelines
- ✅ Clear, actionable design guidance

## Advanced Patterns

For complex dashboard requests, see:
- **references/design-patterns.md** - Common SaaS dashboard patterns
- **references/color-systems.md** - Extended color palette systems

## Quick Examples

**User Request**: "Design a dashboard card to show revenue metrics"

**Response Structure**:
1. Clarify: "Daily, weekly, or monthly revenue? Compare to previous period?"
2. Layout: Card with metric + trend + sparkline
3. Visual Specs: Glass card, 280×180px, indigo accent
4. Component details: Metric (48px bold), trend (+12% green), mini chart
5. States: Hover reveals detailed tooltip

---

**Remember**: Design is about solving user problems elegantly. Every pixel, color, and animation should have a purpose. Guide with precision, inspire with aesthetics.
