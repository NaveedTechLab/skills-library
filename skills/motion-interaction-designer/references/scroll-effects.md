# Scroll-Based Animations with Framer Motion

## Table of Contents

1. [Scroll-Triggered Reveals](#scroll-triggered-reveals)
2. [Parallax Effects](#parallax-effects)
3. [Scroll-Linked Animations](#scroll-linked-animations)
4. [Scroll Progress Indicators](#scroll-progress-indicators)
5. [Sticky Scroll Sections](#sticky-scroll-sections)
6. [Horizontal Scroll](#horizontal-scroll)

---

## Scroll-Triggered Reveals

### Pattern: Fade In on Scroll

**Use Case**: Section reveals, content loading

**Implementation**:
```tsx
import { motion } from 'framer-motion'

export function ScrollReveal({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}
```

**Properties**:
- **initial**: Starting state (invisible, below)
- **whileInView**: When 30% visible, animate
- **viewport.once**: Only trigger first time (performance)
- **viewport.amount**: 0.3 = trigger at 30% visible

---

### Pattern: Staggered Scroll Reveals

**Use Case**: Feature lists, product grids

**Implementation**:
```tsx
import { motion } from 'framer-motion'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5 }
  }
}

export function FeatureGrid({ features }) {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.2 }}
      style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}
    >
      {features.map((feature, i) => (
        <motion.div
          key={i}
          variants={itemVariants}
          style={{
            padding: 20,
            backgroundColor: 'white',
            borderRadius: 12,
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)'
          }}
        >
          <h3>{feature.title}</h3>
          <p>{feature.description}</p>
        </motion.div>
      ))}
    </motion.div>
  )
}
```

**Stagger Effect**:
- Container triggers when 20% visible
- Each child animates 150ms after previous
- Creates wave-like reveal

---

### Pattern: Direction-Aware Reveal

**Use Case**: Alternate left/right reveals

**Implementation**:
```tsx
import { motion } from 'framer-motion'

export function AlternatingReveal({ items }) {
  return (
    <div>
      {items.map((item, index) => {
        const isEven = index % 2 === 0

        return (
          <motion.div
            key={index}
            initial={{
              opacity: 0,
              x: isEven ? -50 : 50
            }}
            whileInView={{
              opacity: 1,
              x: 0
            }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
            style={{
              marginBottom: 40,
              padding: 20,
              backgroundColor: 'white',
              borderRadius: 12
            }}
          >
            <h3>{item.title}</h3>
            <p>{item.description}</p>
          </motion.div>
        )
      })}
    </div>
  )
}
```

**Alternating**:
- Even items: Slide from left
- Odd items: Slide from right
- Creates zigzag effect

---

## Parallax Effects

### Pattern: Simple Background Parallax

**Use Case**: Hero sections, landing pages

**Implementation**:
```tsx
import { motion, useScroll, useTransform } from 'framer-motion'
import { useRef } from 'react'

export function ParallaxSection() {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start start', 'end start']
  })

  const y = useTransform(scrollYProgress, [0, 1], ['0%', '50%'])
  const opacity = useTransform(scrollYProgress, [0, 0.5, 1], [1, 0.5, 0])

  return (
    <div ref={ref} style={{ position: 'relative', height: '100vh', overflow: 'hidden' }}>
      {/* Background layer (moves slower) */}
      <motion.div
        style={{
          y,
          opacity,
          position: 'absolute',
          inset: 0,
          backgroundImage: 'url(/hero-bg.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          zIndex: 0
        }}
      />

      {/* Foreground content (static) */}
      <div style={{ position: 'relative', zIndex: 1, padding: 60 }}>
        <h1>Hero Title</h1>
        <p>Hero description</p>
      </div>
    </div>
  )
}
```

**Parallax Properties**:
- **scrollYProgress**: 0 (top) to 1 (bottom of section)
- **offset**: Defines when tracking starts/ends
- **y**: Moves 0% to 50% (half speed of scroll)
- **opacity**: Fades as you scroll

---

### Pattern: Multi-Layer Parallax

**Use Case**: Depth effects, immersive sections

**Implementation**:
```tsx
import { motion, useScroll, useTransform } from 'framer-motion'
import { useRef } from 'react'

export function MultiLayerParallax() {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start start', 'end start']
  })

  const yBackground = useTransform(scrollYProgress, [0, 1], ['0%', '50%'])
  const yMiddle = useTransform(scrollYProgress, [0, 1], ['0%', '30%'])
  const yForeground = useTransform(scrollYProgress, [0, 1], ['0%', '15%'])

  return (
    <div ref={ref} style={{ position: 'relative', height: '100vh', overflow: 'hidden' }}>
      {/* Layer 1: Far background (slowest) */}
      <motion.div
        style={{
          y: yBackground,
          position: 'absolute',
          inset: 0,
          backgroundColor: '#1A1A2E',
          zIndex: 0
        }}
      />

      {/* Layer 2: Middle (medium speed) */}
      <motion.div
        style={{
          y: yMiddle,
          position: 'absolute',
          inset: 0,
          backgroundImage: 'url(/mountains.png)',
          backgroundSize: 'cover',
          opacity: 0.6,
          zIndex: 1
        }}
      />

      {/* Layer 3: Foreground (slow) */}
      <motion.div
        style={{
          y: yForeground,
          position: 'absolute',
          inset: 0,
          backgroundImage: 'url(/trees.png)',
          backgroundSize: 'cover',
          zIndex: 2
        }}
      />

      {/* Content (static) */}
      <div style={{ position: 'relative', zIndex: 3, padding: 60, color: 'white' }}>
        <h1>Multi-Layer Parallax</h1>
      </div>
    </div>
  )
}
```

**Depth Layers**:
- **Background**: 50% (slowest)
- **Middle**: 30% (medium)
- **Foreground**: 15% (faster)
- **Content**: 0% (static)

Creates depth perception through motion.

---

## Scroll-Linked Animations

### Pattern: Progress-Based Scale

**Use Case**: Growing elements, emphasis

**Implementation**:
```tsx
import { motion, useScroll, useTransform } from 'framer-motion'
import { useRef } from 'react'

export function ScaleOnScroll({ children }) {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end start']
  })

  const scale = useTransform(scrollYProgress, [0, 0.5, 1], [0.8, 1.2, 0.8])
  const opacity = useTransform(scrollYProgress, [0, 0.5, 1], [0.3, 1, 0.3])

  return (
    <motion.div
      ref={ref}
      style={{
        scale,
        opacity,
        padding: 40,
        margin: '200px 0'
      }}
    >
      {children}
    </motion.div>
  )
}
```

**Scale Timeline**:
- Start: 0.8x scale, 30% opacity
- Middle: 1.2x scale, 100% opacity (peak)
- End: 0.8x scale, 30% opacity

---

### Pattern: Rotate on Scroll

**Use Case**: 3D effects, creative sections

**Implementation**:
```tsx
import { motion, useScroll, useTransform } from 'framer-motion'
import { useRef } from 'react'

export function RotateCard() {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end start']
  })

  const rotateX = useTransform(scrollYProgress, [0, 0.5, 1], [45, 0, -45])
  const rotateY = useTransform(scrollYProgress, [0, 1], [0, 360])

  return (
    <div ref={ref} style={{ perspective: 1000, padding: '200px 0' }}>
      <motion.div
        style={{
          rotateX,
          rotateY,
          width: 300,
          height: 400,
          backgroundColor: '#6366F1',
          borderRadius: 16,
          margin: '0 auto'
        }}
      >
        <p style={{ padding: 20, color: 'white' }}>Rotating Card</p>
      </motion.div>
    </div>
  )
}
```

**3D Rotation**:
- **rotateX**: Tilts from 45° to -45° (vertical flip)
- **rotateY**: Full 360° spin
- **perspective**: Creates 3D space

---

## Scroll Progress Indicators

### Pattern: Reading Progress Bar

**Use Case**: Blog posts, articles

**Implementation**:
```tsx
import { motion, useScroll } from 'framer-motion'

export function ReadingProgress() {
  const { scrollYProgress } = useScroll()

  return (
    <motion.div
      style={{
        scaleX: scrollYProgress,
        transformOrigin: 'left',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 4,
        backgroundColor: '#6366F1',
        zIndex: 1000
      }}
    />
  )
}
```

**Progress Bar**:
- **scaleX**: 0 (page top) to 1 (page bottom)
- **Fixed**: Stays at top while scrolling
- **Transform origin**: Grows from left

---

### Pattern: Circular Progress (Scroll to Top Button)

**Implementation**:
```tsx
import { motion, useScroll } from 'framer-motion'

export function ScrollToTop() {
  const { scrollYProgress } = useScroll()

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <motion.button
      onClick={scrollToTop}
      style={{
        position: 'fixed',
        bottom: 20,
        right: 20,
        width: 60,
        height: 60,
        borderRadius: '50%',
        border: 'none',
        backgroundColor: '#6366F1',
        color: 'white',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 24
      }}
      initial={{ opacity: 0, scale: 0 }}
      animate={{
        opacity: scrollYProgress.get() > 0.2 ? 1 : 0,
        scale: scrollYProgress.get() > 0.2 ? 1 : 0
      }}
    >
      <svg width="60" height="60" style={{ position: 'absolute', transform: 'rotate(-90deg)' }}>
        <circle
          cx="30"
          cy="30"
          r="26"
          stroke="rgba(255,255,255,0.2)"
          strokeWidth="4"
          fill="none"
        />
        <motion.circle
          cx="30"
          cy="30"
          r="26"
          stroke="white"
          strokeWidth="4"
          fill="none"
          style={{
            pathLength: scrollYProgress
          }}
          strokeDasharray="0 1"
        />
      </svg>
      ↑
    </motion.button>
  )
}
```

**Circular Progress**:
- **pathLength**: 0 to 1 based on scroll
- **Appears**: Only when scrolled > 20%
- **Scale animation**: Pops in/out smoothly

---

## Sticky Scroll Sections

### Pattern: Sticky Element with Scroll Effects

**Use Case**: Feature showcase, product details

**Implementation**:
```tsx
import { motion, useScroll, useTransform } from 'framer-motion'
import { useRef } from 'react'

export function StickySection() {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start start', 'end end']
  })

  const opacity = useTransform(scrollYProgress, [0, 0.5, 1], [0.3, 1, 0.3])
  const scale = useTransform(scrollYProgress, [0, 0.5, 1], [0.9, 1, 0.9])

  return (
    <div ref={ref} style={{ height: '300vh', position: 'relative' }}>
      <div style={{ height: '100vh', position: 'sticky', top: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <motion.div
          style={{
            opacity,
            scale,
            width: 400,
            padding: 40,
            backgroundColor: 'white',
            borderRadius: 16,
            boxShadow: '0 10px 40px rgba(0, 0, 0, 0.1)'
          }}
        >
          <h2>Sticky Content</h2>
          <p>This stays in view while scrolling through the section</p>
        </motion.div>
      </div>
    </div>
  )
}
```

**Sticky Behavior**:
- **Container**: 300vh tall (3x viewport)
- **Sticky element**: Stays centered while scrolling
- **Opacity/Scale**: Peaks at middle of section

---

## Horizontal Scroll

### Pattern: Horizontal Scroll Cards

**Use Case**: Image carousels, timeline

**Implementation**:
```tsx
import { motion, useScroll, useTransform } from 'framer-motion'
import { useRef } from 'react'

export function HorizontalScroll({ items }) {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end start']
  })

  // Transform vertical scroll to horizontal movement
  const x = useTransform(
    scrollYProgress,
    [0, 1],
    ['0%', '-75%'] // Move 75% left (4 cards)
  )

  return (
    <div ref={ref} style={{ height: '400vh', position: 'relative' }}>
      <div style={{ position: 'sticky', top: 0, height: '100vh', overflow: 'hidden' }}>
        <motion.div
          style={{
            x,
            display: 'flex',
            gap: 20,
            padding: '0 20px'
          }}
        >
          {items.map((item, i) => (
            <div
              key={i}
              style={{
                minWidth: 400,
                height: 600,
                backgroundColor: 'white',
                borderRadius: 16,
                padding: 20,
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
              }}
            >
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  )
}
```

**Horizontal Scroll**:
- **Tall container**: Creates scrollable area
- **Sticky wrapper**: Keeps cards in view
- **Transform**: Vertical scroll → horizontal movement

---

## Performance Optimization

### Use `will-change` for Smooth Scrolling

```tsx
<motion.div
  style={{
    y,
    willChange: 'transform'
  }}
>
  Smooth parallax
</motion.div>
```

### Throttle Scroll Listeners

```tsx
import { useScroll, useTransform } from 'framer-motion'
import { useMemo } from 'react'

export function OptimizedScroll() {
  const { scrollYProgress } = useScroll()

  // Memoize transform to avoid recalculation
  const y = useMemo(
    () => useTransform(scrollYProgress, [0, 1], ['0%', '50%']),
    [scrollYProgress]
  )

  return <motion.div style={{ y }}>Content</motion.div>
}
```

### Disable Animations on Mobile

```tsx
import { useReducedMotion } from 'framer-motion'

export function ResponsiveScroll() {
  const shouldReduceMotion = useReducedMotion()

  if (shouldReduceMotion) {
    return <div>Static content (no scroll effects)</div>
  }

  return <ScrollAnimatedContent />
}
```

---

## Scroll Animation Checklist

When designing scroll animations:

- [ ] **Performance**: Using GPU-accelerated properties (transform, opacity)?
- [ ] **Viewport triggers**: Set `once: true` to avoid re-triggering?
- [ ] **Amount threshold**: Triggering at appropriate visibility (0.3-0.5)?
- [ ] **Mobile**: Tested on touch devices with momentum scrolling?
- [ ] **Reduced motion**: Respects user preference?
- [ ] **will-change**: Applied to frequently animated elements?
- [ ] **Height calculation**: Container heights correct for parallax?
- [ ] **Overlap**: Multiple scroll listeners don't conflict?

---

**All scroll effects tested on**: Desktop Chrome, Safari, Firefox | Mobile iOS Safari, Chrome Android
