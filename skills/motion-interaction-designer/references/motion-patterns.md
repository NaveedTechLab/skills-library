# Advanced Motion Patterns with Framer Motion

## Table of Contents

1. [Shared Layout Transitions](#shared-layout-transitions)
2. [Orchestrated Sequences](#orchestrated-sequences)
3. [Morphing Shapes](#morphing-shapes)
4. [Card Flip Animations](#card-flip-animations)
5. [Notification Systems](#notification-systems)
6. [Skeleton Loading States](#skeleton-loading-states)

---

## Shared Layout Transitions

### Pattern: Expanding Card to Full Page

**Use Case**: Image galleries, product details, article expansion

**Implementation**:
```tsx
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion'
import { useState } from 'react'

export function ExpandableCard({ item }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <LayoutGroup>
      <motion.div
        layout
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          borderRadius: 16,
          overflow: 'hidden',
          cursor: 'pointer'
        }}
      >
        <motion.img
          layout
          src={item.image}
          alt={item.title}
          style={{
            width: '100%',
            height: isExpanded ? 400 : 200,
            objectFit: 'cover'
          }}
        />

        <motion.div layout style={{ padding: 20 }}>
          <motion.h2 layout style={{ margin: 0 }}>
            {item.title}
          </motion.h2>

          <AnimatePresence>
            {isExpanded && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2, delay: 0.1 }}
              >
                {item.description}
              </motion.p>
            )}
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </LayoutGroup>
  )
}
```

**Motion Properties**:
- **layout prop**: Smoothly animates size/position changes
- **LayoutGroup**: Ensures coordinated animations
- **Delay**: Content fades in after layout settles
- **Spring**: Feels natural (can customize with `transition`)

---

### Pattern: Gallery to Lightbox Transition

**Implementation**:
```tsx
import { motion, AnimateSharedLayout } from 'framer-motion'
import { useState } from 'react'

export function ImageGallery({ images }) {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  return (
    <>
      {/* Gallery Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {images.map((image) => (
          <motion.div
            key={image.id}
            layoutId={`image-${image.id}`}
            onClick={() => setSelectedId(image.id)}
            style={{ cursor: 'pointer', borderRadius: 8, overflow: 'hidden' }}
          >
            <img src={image.thumbnail} alt={image.alt} style={{ width: '100%' }} />
          </motion.div>
        ))}
      </div>

      {/* Lightbox */}
      <AnimatePresence>
        {selectedId && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedId(null)}
              style={{
                position: 'fixed',
                inset: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.9)',
                zIndex: 50
              }}
            />

            <motion.div
              layoutId={`image-${selectedId}`}
              style={{
                position: 'fixed',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                zIndex: 51,
                borderRadius: 8,
                overflow: 'hidden',
                maxWidth: '90vw',
                maxHeight: '90vh'
              }}
            >
              <img
                src={images.find(img => img.id === selectedId)?.full}
                alt=""
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
```

**Motion Properties**:
- **layoutId**: Shared element identifier for morphing
- **Automatic**: Framer Motion handles the complex transition
- **Result**: Image smoothly expands from grid to fullscreen

---

## Orchestrated Sequences

### Pattern: Sequential Reveal (Hero Section)

**Use Case**: Landing pages, onboarding flows

**Implementation**:
```tsx
import { motion } from 'framer-motion'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      when: 'beforeChildren',
      staggerChildren: 0.2
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
}

export function HeroSection() {
  return (
    <motion.section
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      style={{ textAlign: 'center', padding: 60 }}
    >
      <motion.h1
        variants={itemVariants}
        transition={{ duration: 0.6 }}
      >
        Welcome to Our Product
      </motion.h1>

      <motion.p
        variants={itemVariants}
        transition={{ duration: 0.6 }}
      >
        The best way to manage your tasks
      </motion.p>

      <motion.button
        variants={itemVariants}
        transition={{ duration: 0.6 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        Get Started
      </motion.button>
    </motion.section>
  )
}
```

**Orchestration**:
1. Container fades in
2. Then children appear one-by-one (200ms apart)
3. Each child: fade + slide up
4. Total time: ~1 second

---

### Pattern: Multi-Step Form Transitions

**Implementation**:
```tsx
import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0
  }),
  center: {
    x: 0,
    opacity: 1
  },
  exit: (direction: number) => ({
    x: direction < 0 ? 300 : -300,
    opacity: 0
  })
}

export function MultiStepForm() {
  const [step, setStep] = useState(0)
  const [direction, setDirection] = useState(0)

  const nextStep = () => {
    setDirection(1)
    setStep(prev => prev + 1)
  }

  const prevStep = () => {
    setDirection(-1)
    setStep(prev => prev - 1)
  }

  const steps = [
    <Step1 key="step1" />,
    <Step2 key="step2" />,
    <Step3 key="step3" />
  ]

  return (
    <div style={{ position: 'relative', overflow: 'hidden', height: 400 }}>
      <AnimatePresence initial={false} custom={direction}>
        <motion.div
          key={step}
          custom={direction}
          variants={slideVariants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{
            x: { type: 'spring', stiffness: 300, damping: 30 },
            opacity: { duration: 0.2 }
          }}
          style={{ position: 'absolute', width: '100%' }}
        >
          {steps[step]}
        </motion.div>
      </AnimatePresence>

      <div style={{ marginTop: 320, display: 'flex', gap: 12 }}>
        {step > 0 && <button onClick={prevStep}>Back</button>}
        {step < steps.length - 1 && <button onClick={nextStep}>Next</button>}
      </div>
    </div>
  )
}
```

**Direction-Aware**:
- Next: Slides in from right, exits to left
- Back: Slides in from left, exits to right
- Uses `custom` prop to pass direction to variants

---

## Morphing Shapes

### Pattern: Icon Transitions (Menu ↔ Close)

**Implementation**:
```tsx
import { motion } from 'framer-motion'

export function MenuIcon({ isOpen, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        padding: 8
      }}
    >
      <svg width="24" height="24" viewBox="0 0 24 24">
        <motion.path
          d={isOpen ? 'M6 18L18 6' : 'M4 6h16'}
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          animate={{ d: isOpen ? 'M6 18L18 6' : 'M4 6h16' }}
          transition={{ duration: 0.3 }}
        />

        <motion.path
          d="M4 12h16"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          animate={{ opacity: isOpen ? 0 : 1 }}
          transition={{ duration: 0.2 }}
        />

        <motion.path
          d={isOpen ? 'M18 18L6 6' : 'M4 18h16'}
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          animate={{ d: isOpen ? 'M18 18L6 6' : 'M4 18h16' }}
          transition={{ duration: 0.3 }}
        />
      </svg>
    </button>
  )
}
```

**Morphing**:
- Top line → Left diagonal (X)
- Middle line → Fades out
- Bottom line → Right diagonal (X)

---

## Card Flip Animations

### Pattern: 3D Card Flip (Front/Back)

**Use Case**: Flashcards, product specs, profile cards

**Implementation**:
```tsx
import { motion } from 'framer-motion'
import { useState } from 'react'

export function FlipCard({ front, back }) {
  const [isFlipped, setIsFlipped] = useState(false)

  return (
    <div
      onClick={() => setIsFlipped(!isFlipped)}
      style={{
        perspective: 1000,
        width: 300,
        height: 200,
        cursor: 'pointer'
      }}
    >
      <motion.div
        animate={{ rotateY: isFlipped ? 180 : 0 }}
        transition={{
          duration: 0.6,
          ease: 'easeInOut'
        }}
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          transformStyle: 'preserve-3d'
        }}
      >
        {/* Front */}
        <div
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            backfaceVisibility: 'hidden',
            backgroundColor: '#6366F1',
            borderRadius: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white'
          }}
        >
          {front}
        </div>

        {/* Back */}
        <div
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            backfaceVisibility: 'hidden',
            transform: 'rotateY(180deg)',
            backgroundColor: '#8B5CF6',
            borderRadius: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white'
          }}
        >
          {back}
        </div>
      </motion.div>
    </div>
  )
}
```

**3D Transform**:
- **perspective**: Creates 3D space
- **rotateY**: Flips along Y-axis
- **backfaceVisibility**: Hides back of card
- **preserve-3d**: Maintains 3D positioning

---

## Notification Systems

### Pattern: Toast Notifications (Stack)

**Implementation**:
```tsx
import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'

type Toast = {
  id: string
  message: string
  type: 'success' | 'error' | 'info'
}

const toastVariants = {
  initial: { opacity: 0, y: -50, scale: 0.3 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, x: 300, scale: 0.8 }
}

export function ToastContainer({ toasts, onDismiss }) {
  return (
    <div
      style={{
        position: 'fixed',
        top: 20,
        right: 20,
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: 12
      }}
    >
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            variants={toastVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            layout
            transition={{
              type: 'spring',
              stiffness: 500,
              damping: 40
            }}
            style={{
              padding: '12px 20px',
              backgroundColor: toast.type === 'success' ? '#10B981' : '#EF4444',
              color: 'white',
              borderRadius: 8,
              minWidth: 300,
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{toast.message}</span>
              <button
                onClick={() => onDismiss(toast.id)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'white',
                  cursor: 'pointer',
                  fontSize: 20
                }}
              >
                ×
              </button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

// Usage
export function App() {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = (message: string, type: Toast['type']) => {
    const id = Date.now().toString()
    setToasts(prev => [...prev, { id, message, type }])

    // Auto-dismiss after 3 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 3000)
  }

  return (
    <>
      <button onClick={() => addToast('Success!', 'success')}>
        Show Toast
      </button>

      <ToastContainer
        toasts={toasts}
        onDismiss={(id) => setToasts(prev => prev.filter(t => t.id !== id))}
      />
    </>
  )
}
```

**Notification Motion**:
- **Enter**: Slide down + scale up
- **Exit**: Slide right + scale down
- **layout prop**: Stack adjusts smoothly when dismissed

---

## Skeleton Loading States

### Pattern: Shimmer Skeleton

**Implementation**:
```tsx
import { motion } from 'framer-motion'

export function SkeletonCard() {
  return (
    <div
      style={{
        padding: 20,
        backgroundColor: '#f3f4f6',
        borderRadius: 12
      }}
    >
      {/* Animated shimmer effect */}
      <div style={{ position: 'relative', overflow: 'hidden' }}>
        <motion.div
          animate={{
            x: ['-100%', '100%']
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'linear'
          }}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)',
            pointerEvents: 'none'
          }}
        />

        {/* Skeleton shapes */}
        <div style={{ width: '60%', height: 20, backgroundColor: '#e5e7eb', borderRadius: 4, marginBottom: 12 }} />
        <div style={{ width: '100%', height: 16, backgroundColor: '#e5e7eb', borderRadius: 4, marginBottom: 8 }} />
        <div style={{ width: '80%', height: 16, backgroundColor: '#e5e7eb', borderRadius: 4 }} />
      </div>
    </div>
  )
}
```

**Shimmer Animation**:
- Linear gradient moves left to right
- Infinite loop
- Creates "loading" effect

---

### Pattern: Pulsing Skeleton

**Implementation**:
```tsx
import { motion } from 'framer-motion'

export function PulsingSkeleton() {
  return (
    <motion.div
      animate={{ opacity: [0.5, 1, 0.5] }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: 'easeInOut'
      }}
      style={{
        width: '100%',
        height: 200,
        backgroundColor: '#e5e7eb',
        borderRadius: 12
      }}
    />
  )
}
```

---

## Performance Best Practices

### Avoid Layout Thrashing

**Bad** (causes reflow):
```tsx
// ❌ Animating width/height directly
<motion.div animate={{ width: 300, height: 200 }} />
```

**Good** (GPU-accelerated):
```tsx
// ✅ Use scale instead
<motion.div
  style={{ width: 200, height: 100 }}
  animate={{ scale: 1.5 }}
/>
```

### Use `layout` Prop Sparingly

**When to use**:
- Reordering lists
- Expanding/collapsing sections
- Shared element transitions

**When NOT to use**:
- Simple fade-ins
- Position changes you can animate with `x` and `y`
- High-frequency updates (scrolling)

### Optimize Variants

**Reuse variant objects**:
```tsx
// ✅ Define once, reuse
const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 }
}

<motion.div variants={fadeIn} />
<motion.div variants={fadeIn} />
```

**vs**

```tsx
// ❌ Creates new object each render
<motion.div
  variants={{ hidden: { opacity: 0 }, visible: { opacity: 1 } }}
/>
```

---

## Testing Animations

### Visual Regression Testing

```tsx
import { render } from '@testing-library/react'
import { MotionConfig } from 'framer-motion'

// Disable animations in tests
test('component renders correctly', () => {
  render(
    <MotionConfig reducedMotion="always">
      <AnimatedComponent />
    </MotionConfig>
  )

  // Test static state
})
```

### Performance Testing

```tsx
// Monitor animation FPS
import { useAnimationFrame } from 'framer-motion'

let frameCount = 0
let lastTime = performance.now()

useAnimationFrame(() => {
  frameCount++
  const now = performance.now()

  if (now - lastTime >= 1000) {
    console.log(`FPS: ${frameCount}`)
    frameCount = 0
    lastTime = now
  }
})
```

---

**All patterns tested on**: Desktop Chrome, Safari, Firefox | Mobile iOS Safari, Chrome Android
