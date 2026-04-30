---
name: motion-interaction-designer
description: Design smooth UI animations and interactions using Framer Motion for React/Next.js. Use when users request animations, transitions, hover effects, scroll animations, gesture interactions, or need help implementing Framer Motion. Follow modern motion UX principles with purposeful, performant animations that enhance usability.
---

# Motion & Interaction Designer

Design purposeful, smooth UI animations using Framer Motion following modern motion UX principles.

## Core Philosophy

**Motion UX Principles**:
- **Purposeful**: Every animation serves a function (feedback, guidance, delight)
- **Subtle**: Motion enhances, never distracts (200-500ms sweet spot)
- **Responsive**: Respect user preferences (reduced motion)
- **Performant**: 60fps on all devices, GPU-accelerated properties
- **Consistent**: Unified timing and easing across the app

**When to Animate**:
- ✅ State changes (hover, active, disabled)
- ✅ Page/component transitions (route changes, modals)
- ✅ User feedback (button clicks, form submissions)
- ✅ Content reveals (scroll, load, stagger)
- ✅ Contextual hints (first-time user guidance)

**When NOT to Animate**:
- ❌ Critical actions (payment buttons - instant only)
- ❌ Reading content (body text, paragraphs)
- ❌ Rapid repetition (typing, scrolling lists)
- ❌ User requested reduced motion

## Technology Stack

**Required Dependency**:
```json
{
  "framer-motion": "^11.0.0"
}
```

**Optional (Scroll Animations)**:
```json
{
  "react-intersection-observer": "^9.5.0"
}
```

## Motion Workflow

When a user requests animation design, follow this approach:

### Step 1: Identify Animation Type

Categorize the interaction into one of these patterns:

**1. State Transitions** (hover, focus, active, disabled)
- Buttons, links, cards
- Duration: 150-300ms
- Easing: ease-out

**2. Enter/Exit Animations** (mount, unmount, visibility)
- Modals, dropdowns, tooltips
- Duration: 200-400ms
- Easing: ease-in-out

**3. Layout Animations** (position, size changes)
- Expanding cards, reordering lists
- Duration: 300-500ms
- Easing: spring or ease-out

**4. Scroll Animations** (scroll-triggered reveals)
- Parallax, fade-ins, stagger effects
- Duration: 400-600ms
- Easing: ease-out

**5. Gesture Interactions** (drag, tap, swipe)
- Custom controls, sliders, carousels
- Duration: Immediate feedback + 200-400ms settle
- Easing: spring (feels natural)

### Step 2: Define Motion Properties

For each animation, specify:

1. **Properties to Animate**:
   - **GPU-accelerated** (best performance): `transform`, `opacity`
   - **Avoid**: `width`, `height`, `top`, `left`, `margin`

2. **Duration**: Target time in milliseconds
3. **Easing**: Curve type (see timing guide below)
4. **Delay**: Stagger or sequence timing
5. **Spring vs Tween**: Natural feel vs precise control

### Step 3: Provide Implementation Code

Structure code with:
- Import statements
- Component structure
- Motion variants (reusable animation configs)
- Responsive behavior
- Accessibility (reduced motion)

## Implementation Patterns

### Pattern 1: Basic Hover Animation (Button)

**Use Case**: Call-to-action buttons, interactive elements

**Implementation**:
```tsx
import { motion } from 'framer-motion'

export function AnimatedButton({ children, onClick }) {
  return (
    <motion.button
      onClick={onClick}
      whileHover={{
        scale: 1.05,
        boxShadow: '0 10px 20px rgba(0, 0, 0, 0.15)'
      }}
      whileTap={{ scale: 0.95 }}
      transition={{
        type: 'spring',
        stiffness: 400,
        damping: 17
      }}
      style={{
        padding: '12px 24px',
        backgroundColor: '#6366F1',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        cursor: 'pointer'
      }}
    >
      {children}
    </motion.button>
  )
}
```

**Motion Properties**:
- **Hover**: Scale 1.05 (5% larger), shadow grows
- **Tap**: Scale 0.95 (5% smaller) - tactile feedback
- **Transition**: Spring (natural bounce)
- **Performance**: GPU-accelerated (scale, boxShadow)

---

### Pattern 2: Fade In on Mount (Modal, Dropdown)

**Use Case**: Overlays, popups, tooltips

**Implementation**:
```tsx
import { motion, AnimatePresence } from 'framer-motion'

export function Modal({ isOpen, onClose, children }) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              zIndex: 40
            }}
          />

          {/* Modal Content */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{
              duration: 0.3,
              ease: [0.4, 0, 0.2, 1] // Custom ease-out
            }}
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              backgroundColor: 'white',
              padding: '32px',
              borderRadius: '12px',
              zIndex: 50
            }}
          >
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
```

**Motion Properties**:
- **Enter**: Fade + scale up + slide down
- **Exit**: Fade + scale down + slide down
- **Duration**: 300ms (perceivable but not slow)
- **Easing**: Custom ease-out (smooth deceleration)
- **AnimatePresence**: Handles unmount animations

---

### Pattern 3: Stagger Children (List Items)

**Use Case**: Todo lists, navigation items, feature grids

**Implementation**:
```tsx
import { motion } from 'framer-motion'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1, // 100ms delay between children
      delayChildren: 0.2    // Wait 200ms before starting
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.4,
      ease: 'easeOut'
    }
  }
}

export function TodoList({ todos }) {
  return (
    <motion.ul
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      style={{ listStyle: 'none', padding: 0 }}
    >
      {todos.map((todo) => (
        <motion.li
          key={todo.id}
          variants={itemVariants}
          style={{ padding: '12px', marginBottom: '8px' }}
        >
          {todo.title}
        </motion.li>
      ))}
    </motion.ul>
  )
}
```

**Motion Properties**:
- **Stagger**: 100ms between each child
- **Delay**: 200ms before first child
- **Item animation**: Fade + slide from left
- **Variants**: Reusable animation configs

---

### Pattern 4: Scroll-Triggered Animation

**Use Case**: Section reveals, parallax effects

**Implementation**:
```tsx
import { motion, useScroll, useTransform } from 'framer-motion'
import { useRef } from 'react'

export function ScrollReveal({ children }) {
  const ref = useRef(null)

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }} // Trigger at 30% visible
      transition={{ duration: 0.6, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}

// Advanced: Parallax scroll
export function ParallaxSection() {
  const { scrollYProgress } = useScroll()
  const y = useTransform(scrollYProgress, [0, 1], ['0%', '50%'])

  return (
    <motion.div
      style={{ y }}
      className="background-layer"
    >
      {/* Background content */}
    </motion.div>
  )
}
```

**Motion Properties**:
- **whileInView**: Animates when 30% visible
- **viewport.once**: Only animate first time (performance)
- **Parallax**: Transform Y based on scroll progress
- **Use case**: Hero sections, feature reveals

---

### Pattern 5: Layout Animation (Reordering, Expanding)

**Use Case**: Animated lists, accordions, grid layouts

**Implementation**:
```tsx
import { motion, LayoutGroup } from 'framer-motion'
import { useState } from 'react'

export function AnimatedList({ items }) {
  const [sortedItems, setSortedItems] = useState(items)

  return (
    <LayoutGroup>
      <motion.ul layout>
        {sortedItems.map((item) => (
          <motion.li
            key={item.id}
            layout
            transition={{
              type: 'spring',
              stiffness: 500,
              damping: 30
            }}
          >
            {item.title}
          </motion.li>
        ))}
      </motion.ul>
    </LayoutGroup>
  )
}

// Accordion example
export function Accordion({ title, children }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <motion.div layout>
      <motion.button
        layout
        onClick={() => setIsOpen(!isOpen)}
      >
        {title}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
```

**Motion Properties**:
- **layout prop**: Auto-animates position/size changes
- **LayoutGroup**: Shared layout context for smooth transitions
- **Spring**: Natural feel for reordering
- **Auto height**: Smooth accordion expand/collapse

---

### Pattern 6: Drag Interaction

**Use Case**: Sliders, reorderable lists, custom controls

**Implementation**:
```tsx
import { motion } from 'framer-motion'

export function DraggableCard() {
  return (
    <motion.div
      drag
      dragConstraints={{
        top: -100,
        left: -100,
        right: 100,
        bottom: 100
      }}
      dragElastic={0.1}
      dragTransition={{
        bounceStiffness: 600,
        bounceDamping: 20
      }}
      whileDrag={{ scale: 1.05, cursor: 'grabbing' }}
      style={{
        width: 200,
        height: 200,
        backgroundColor: '#6366F1',
        borderRadius: 12,
        cursor: 'grab'
      }}
    >
      Drag me!
    </motion.div>
  )
}

// Swipe to dismiss
export function SwipeCard({ onDismiss }) {
  return (
    <motion.div
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      onDragEnd={(e, { offset, velocity }) => {
        const swipe = Math.abs(offset.x) * velocity.x

        if (swipe < -10000 || swipe > 10000) {
          onDismiss()
        }
      }}
    >
      Swipe to dismiss
    </motion.div>
  )
}
```

**Motion Properties**:
- **drag**: Enable dragging (x, y, or both)
- **dragConstraints**: Limit drag area
- **dragElastic**: Bounce at boundaries
- **whileDrag**: Scale up while dragging
- **Swipe detection**: velocity × offset

---

## Timing & Easing Guide

### Duration Guidelines

**Instant** (0-100ms):
- Immediate feedback (button clicks, checkbox toggles)
- No animation needed

**Quick** (100-200ms):
- State changes (hover, focus)
- Small movements (icon rotations)
- Use: `transition={{ duration: 0.15 }}`

**Standard** (200-400ms):
- Modals, dropdowns, tooltips
- Card reveals, fades
- Use: `transition={{ duration: 0.3 }}`

**Slow** (400-600ms):
- Page transitions
- Large layout shifts
- Scroll-triggered reveals
- Use: `transition={{ duration: 0.5 }}`

**Very Slow** (600ms+):
- Only for intentional dramatic effect
- Onboarding tours, hero animations
- Use sparingly: `transition={{ duration: 0.8 }}`

### Easing Functions

**Ease Out** (Most Common):
```tsx
transition={{ ease: 'easeOut' }}
// or custom: ease: [0.4, 0, 0.2, 1]
```
- **Use**: Enter animations, reveals, fades
- **Feel**: Starts fast, slows down (natural deceleration)

**Ease In**:
```tsx
transition={{ ease: 'easeIn' }}
```
- **Use**: Exit animations, dismissals
- **Feel**: Starts slow, speeds up (falling away)

**Ease In-Out**:
```tsx
transition={{ ease: 'easeInOut' }}
```
- **Use**: Mid-journey animations (A → B → A)
- **Feel**: Smooth start and end

**Spring** (Most Natural):
```tsx
transition={{
  type: 'spring',
  stiffness: 500,  // Higher = faster
  damping: 30      // Higher = less bounce
}}
```
- **Use**: Interactive elements (buttons, drag)
- **Feel**: Physical, bouncy, responsive
- **Stiffness**: 300-700 range (500 is good default)
- **Damping**: 20-40 range (30 is good default)

**Linear**:
```tsx
transition={{ ease: 'linear' }}
```
- **Use**: Looping animations, loading spinners
- **Feel**: Mechanical, constant speed

---

## Accessibility & Reduced Motion

### Respect User Preferences

**Always include reduced motion support**:
```tsx
import { useReducedMotion } from 'framer-motion'

export function AccessibleAnimation({ children }) {
  const shouldReduceMotion = useReducedMotion()

  const variants = {
    hidden: { opacity: 0, y: shouldReduceMotion ? 0 : 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: shouldReduceMotion ? 0.01 : 0.4
      }
    }
  }

  return (
    <motion.div
      variants={variants}
      initial="hidden"
      animate="visible"
    >
      {children}
    </motion.div>
  )
}
```

**What to Reduce**:
- Disable decorative animations
- Reduce duration to 0.01s (instant but still works)
- Keep essential feedback (button press, loading states)
- Maintain layout shifts (don't disable `layout` prop)

---

## Performance Optimization

### GPU-Accelerated Properties

**Animate These** (60fps guaranteed):
```tsx
// ✅ Fast (uses transform)
<motion.div
  animate={{
    x: 100,           // translateX
    y: 100,           // translateY
    scale: 1.5,       // scale
    rotate: 45,       // rotate
    opacity: 0.5      // opacity
  }}
/>
```

**Avoid Animating** (causes reflow/repaint):
```tsx
// ❌ Slow (triggers layout recalculation)
<motion.div
  animate={{
    width: 300,
    height: 200,
    top: 100,
    left: 100,
    margin: 20
  }}
/>
```

### Will-Change Optimization

For complex animations:
```tsx
<motion.div
  style={{ willChange: 'transform' }}
  animate={{ x: 100, rotate: 45 }}
/>
```

**Warning**: Only use for actively animating elements. Remove after animation completes.

### Lazy Loading Animations

```tsx
import { motion, LazyMotion, domAnimation } from 'framer-motion'

// Reduces bundle size by 30KB
export function OptimizedApp() {
  return (
    <LazyMotion features={domAnimation}>
      <motion.div>Optimized animations</motion.div>
    </LazyMotion>
  )
}
```

---

## Common Animation Patterns

### Page Transitions (Next.js)

```tsx
// app/layout.tsx
import { motion, AnimatePresence } from 'framer-motion'
import { usePathname } from 'next/navigation'

export default function Layout({ children }) {
  const pathname = usePathname()

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        transition={{ duration: 0.3 }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}
```

### Loading States

```tsx
export function LoadingSpinner() {
  return (
    <motion.div
      animate={{ rotate: 360 }}
      transition={{
        duration: 1,
        repeat: Infinity,
        ease: 'linear'
      }}
      style={{
        width: 40,
        height: 40,
        border: '3px solid #E5E7EB',
        borderTopColor: '#6366F1',
        borderRadius: '50%'
      }}
    />
  )
}
```

### Success Checkmark

```tsx
import { motion } from 'framer-motion'

const checkmarkVariants = {
  hidden: { pathLength: 0, opacity: 0 },
  visible: {
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: { duration: 0.5, ease: 'easeOut' },
      opacity: { duration: 0.01 }
    }
  }
}

export function SuccessCheckmark() {
  return (
    <svg width="60" height="60" viewBox="0 0 60 60">
      <motion.path
        d="M15,30 L25,40 L45,20"
        fill="none"
        stroke="#10B981"
        strokeWidth="4"
        strokeLinecap="round"
        variants={checkmarkVariants}
        initial="hidden"
        animate="visible"
      />
    </svg>
  )
}
```

---

## Motion Design Checklist

When designing animations, verify:

- [ ] **Purpose**: Does this animation serve a clear UX purpose?
- [ ] **Duration**: Is it 200-500ms (or justified if longer)?
- [ ] **Easing**: Using appropriate curve (ease-out for most cases)?
- [ ] **Performance**: Animating only `transform` and `opacity`?
- [ ] **Reduced Motion**: Respects `prefers-reduced-motion`?
- [ ] **Consistency**: Matches timing/style of other animations?
- [ ] **Mobile**: Tested on low-end devices?
- [ ] **Accessibility**: Keyboard users can skip/disable?
- [ ] **Bundle Size**: Using `LazyMotion` if many animations?

---

## Advanced Patterns

For complex scenarios, see:
- **references/motion-patterns.md** - Advanced animation patterns (shared transitions, orchestration)
- **references/gesture-interactions.md** - Drag, swipe, pan, pinch gestures
- **references/scroll-effects.md** - Parallax, scroll-linked animations, viewport triggers

---

## Output Format

When providing motion design guidance, structure as:

```
## Animation: [Component Name]

### Purpose
[Why this animation exists - user benefit]

### Motion Specs
- **Trigger**: [Hover, click, scroll, mount]
- **Properties**: [x, y, scale, opacity, etc.]
- **Duration**: [200ms, 400ms, etc.]
- **Easing**: [ease-out, spring, etc.]
- **Delay**: [If staggered or sequenced]

### Implementation
[Framer Motion code]

### Reduced Motion Fallback
[Simplified version for accessibility]

### Performance Notes
[GPU acceleration, potential issues]
```

---

**Remember**: Less is more. Purposeful motion enhances usability. Excessive animation annoys users.
