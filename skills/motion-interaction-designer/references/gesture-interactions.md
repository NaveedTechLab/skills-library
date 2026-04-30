# Gesture Interactions with Framer Motion

## Table of Contents

1. [Drag Fundamentals](#drag-fundamentals)
2. [Swipe Gestures](#swipe-gestures)
3. [Pan Gestures](#pan-gestures)
4. [Tap & Press](#tap--press)
5. [Multi-Touch (Pinch/Rotate)](#multi-touch-pinchrotate)
6. [Custom Gesture Handlers](#custom-gesture-handlers)

---

## Drag Fundamentals

### Pattern: Basic Draggable Element

**Use Case**: Movable UI elements, custom controls

**Implementation**:
```tsx
import { motion } from 'framer-motion'

export function DraggableBox() {
  return (
    <motion.div
      drag
      dragConstraints={{ left: -200, right: 200, top: -200, bottom: 200 }}
      dragElastic={0.2}
      dragTransition={{ bounceStiffness: 600, bounceDamping: 20 }}
      whileDrag={{ scale: 1.1, cursor: 'grabbing' }}
      style={{
        width: 100,
        height: 100,
        backgroundColor: '#6366F1',
        borderRadius: 12,
        cursor: 'grab'
      }}
    >
      Drag me
    </motion.div>
  )
}
```

**Drag Properties**:
- **drag**: Enable dragging (`true`, `"x"`, `"y"`)
- **dragConstraints**: Boundary limits (pixels or ref)
- **dragElastic**: Bounce at boundaries (0-1)
- **dragTransition**: Spring physics for bounce
- **whileDrag**: Style while dragging

---

### Pattern: Drag with Snap Points

**Use Case**: Slider controls, card positioning

**Implementation**:
```tsx
import { motion, useMotionValue, useTransform, animate } from 'framer-motion'
import { useEffect } from 'react'

export function SnapSlider({ snapPoints = [0, 100, 200, 300] }) {
  const x = useMotionValue(0)

  const handleDragEnd = () => {
    const currentX = x.get()

    // Find closest snap point
    const closest = snapPoints.reduce((prev, curr) =>
      Math.abs(curr - currentX) < Math.abs(prev - currentX) ? curr : prev
    )

    // Animate to snap point
    animate(x, closest, {
      type: 'spring',
      stiffness: 300,
      damping: 30
    })
  }

  return (
    <div style={{ position: 'relative', width: 400, height: 100 }}>
      {/* Snap point indicators */}
      {snapPoints.map((point) => (
        <div
          key={point}
          style={{
            position: 'absolute',
            left: point,
            width: 4,
            height: 40,
            backgroundColor: '#E5E7EB',
            borderRadius: 2
          }}
        />
      ))}

      {/* Draggable handle */}
      <motion.div
        drag="x"
        dragConstraints={{ left: 0, right: 300 }}
        dragElastic={0}
        onDragEnd={handleDragEnd}
        style={{
          x,
          width: 60,
          height: 60,
          backgroundColor: '#6366F1',
          borderRadius: '50%',
          position: 'absolute',
          top: 20,
          cursor: 'grab'
        }}
      />
    </div>
  )
}
```

**Snap Behavior**:
- Drags freely along X-axis
- On release, snaps to nearest point
- Uses spring animation for smooth snap

---

### Pattern: Drag to Reorder List

**Use Case**: Todo lists, priority queues, playlists

**Implementation**:
```tsx
import { motion, Reorder } from 'framer-motion'
import { useState } from 'react'

export function ReorderableList({ initialItems }) {
  const [items, setItems] = useState(initialItems)

  return (
    <Reorder.Group axis="y" values={items} onReorder={setItems}>
      {items.map((item) => (
        <Reorder.Item
          key={item.id}
          value={item}
          style={{
            padding: 16,
            marginBottom: 8,
            backgroundColor: 'white',
            borderRadius: 8,
            listStyle: 'none',
            cursor: 'grab'
          }}
          whileDrag={{
            scale: 1.05,
            boxShadow: '0 10px 20px rgba(0, 0, 0, 0.15)',
            cursor: 'grabbing'
          }}
        >
          {item.title}
        </Reorder.Item>
      ))}
    </Reorder.Group>
  )
}
```

**Reorder Features**:
- **Reorder.Group**: Container managing order
- **Reorder.Item**: Individual draggable items
- **Auto-layout**: Items shift automatically
- **Touch support**: Works on mobile

---

## Swipe Gestures

### Pattern: Swipe to Dismiss

**Use Case**: Notifications, messages, cards

**Implementation**:
```tsx
import { motion, useMotionValue, useTransform, PanInfo } from 'framer-motion'
import { useState } from 'react'

export function SwipeCard({ onDismiss, children }) {
  const x = useMotionValue(0)
  const [isDismissed, setIsDismissed] = useState(false)

  // Background color based on swipe direction
  const background = useTransform(
    x,
    [-200, 0, 200],
    ['#EF4444', '#FFFFFF', '#10B981']
  )

  const handleDragEnd = (event: any, info: PanInfo) => {
    const threshold = 150
    const velocity = info.velocity.x
    const offset = info.offset.x

    // Fast swipe OR far swipe = dismiss
    if (Math.abs(velocity) > 500 || Math.abs(offset) > threshold) {
      setIsDismissed(true)
      onDismiss()
    }
  }

  if (isDismissed) return null

  return (
    <motion.div
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.7}
      onDragEnd={handleDragEnd}
      style={{
        x,
        background,
        padding: 20,
        borderRadius: 12,
        cursor: 'grab'
      }}
      whileDrag={{ cursor: 'grabbing' }}
    >
      {children}
    </motion.div>
  )
}
```

**Swipe Detection**:
- **Velocity**: Fast swipe (> 500px/s) = dismiss
- **Offset**: Far swipe (> 150px) = dismiss
- **Background color**: Red (left), green (right)
- **Elastic**: Bounces back if not dismissed

---

### Pattern: Swipe Navigation (Tinder-style)

**Implementation**:
```tsx
import { motion, useMotionValue, useTransform, PanInfo } from 'framer-motion'
import { useState } from 'react'

export function SwipeCards({ cards }) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const x = useMotionValue(0)
  const rotate = useTransform(x, [-200, 200], [-25, 25])
  const opacity = useTransform(x, [-200, -100, 0, 100, 200], [0, 1, 1, 1, 0])

  const handleDragEnd = (event: any, info: PanInfo) => {
    if (Math.abs(info.offset.x) > 100) {
      // Swiped left or right
      setCurrentIndex(prev => prev + 1)
    }
  }

  if (currentIndex >= cards.length) {
    return <div>No more cards</div>
  }

  return (
    <div style={{ position: 'relative', width: 300, height: 400 }}>
      {/* Next card (underneath) */}
      {currentIndex + 1 < cards.length && (
        <div
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            backgroundColor: '#F3F4F6',
            borderRadius: 16,
            transform: 'scale(0.95)',
            zIndex: 1
          }}
        />
      )}

      {/* Current card */}
      <motion.div
        drag="x"
        dragConstraints={{ left: 0, right: 0 }}
        onDragEnd={handleDragEnd}
        style={{
          x,
          rotate,
          opacity,
          position: 'absolute',
          width: '100%',
          height: '100%',
          backgroundColor: 'white',
          borderRadius: 16,
          padding: 20,
          cursor: 'grab',
          zIndex: 2,
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
        }}
        whileDrag={{ cursor: 'grabbing' }}
      >
        <h2>{cards[currentIndex].title}</h2>
        <p>{cards[currentIndex].description}</p>
      </motion.div>
    </div>
  )
}
```

**Tinder-Style Motion**:
- **Rotate**: Card tilts as you swipe
- **Opacity**: Fades as it gets farther
- **Stack**: Next card visible underneath
- **Dismiss**: Swipe > 100px to next card

---

## Pan Gestures

### Pattern: Image Pan & Zoom

**Use Case**: Image viewers, maps, diagrams

**Implementation**:
```tsx
import { motion, useMotionValue, useTransform } from 'framer-motion'
import { useState } from 'react'

export function PanZoomImage({ src }) {
  const [scale, setScale] = useState(1)
  const x = useMotionValue(0)
  const y = useMotionValue(0)

  const handleWheel = (e: WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY * -0.01
    const newScale = Math.min(Math.max(scale + delta, 0.5), 3)
    setScale(newScale)
  }

  return (
    <div
      style={{
        width: 600,
        height: 400,
        overflow: 'hidden',
        position: 'relative',
        cursor: scale > 1 ? 'grab' : 'default'
      }}
      onWheel={handleWheel}
    >
      <motion.img
        src={src}
        drag={scale > 1}
        dragConstraints={{
          left: -(scale - 1) * 300,
          right: (scale - 1) * 300,
          top: -(scale - 1) * 200,
          bottom: (scale - 1) * 200
        }}
        dragElastic={0}
        style={{
          x,
          y,
          scale,
          width: '100%',
          height: '100%',
          objectFit: 'contain'
        }}
        whileDrag={{ cursor: 'grabbing' }}
      />
    </div>
  )
}
```

**Pan & Zoom**:
- **Wheel**: Zoom in/out (0.5x to 3x)
- **Drag**: Only enabled when zoomed
- **Constraints**: Dynamic based on zoom level
- **Elastic**: No bounce (feels like native viewer)

---

## Tap & Press

### Pattern: Long Press Action

**Use Case**: Context menus, delete confirmations

**Implementation**:
```tsx
import { motion } from 'framer-motion'
import { useState, useRef } from 'react'

export function LongPressButton({ onLongPress, children }) {
  const [isPressed, setIsPressed] = useState(false)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const handlePressStart = () => {
    setIsPressed(true)

    timerRef.current = setTimeout(() => {
      onLongPress()
      setIsPressed(false)
    }, 800) // 800ms long press
  }

  const handlePressEnd = () => {
    setIsPressed(false)
    if (timerRef.current) {
      clearTimeout(timerRef.current)
    }
  }

  return (
    <motion.button
      onTapStart={handlePressStart}
      onTap={handlePressEnd}
      onTapCancel={handlePressEnd}
      animate={{
        scale: isPressed ? 0.9 : 1,
        backgroundColor: isPressed ? '#8B5CF6' : '#6366F1'
      }}
      transition={{ duration: 0.2 }}
      style={{
        padding: '12px 24px',
        color: 'white',
        border: 'none',
        borderRadius: 8,
        cursor: 'pointer',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {/* Progress indicator */}
      {isPressed && (
        <motion.div
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 0.8, ease: 'linear' }}
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: 3,
            backgroundColor: 'rgba(255, 255, 255, 0.5)',
            transformOrigin: 'left'
          }}
        />
      )}

      {children}
    </motion.button>
  )
}
```

**Long Press**:
- **Duration**: 800ms hold required
- **Feedback**: Button scales down, color changes
- **Progress bar**: Shows how long to hold
- **Cancel**: Release early cancels action

---

### Pattern: Double Tap to Like

**Use Case**: Social media, favorites

**Implementation**:
```tsx
import { motion } from 'framer-motion'
import { useState, useRef } from 'react'

export function DoubleTapImage({ src, onLike }) {
  const [showHeart, setShowHeart] = useState(false)
  const lastTapRef = useRef(0)

  const handleTap = () => {
    const now = Date.now()
    const timeSinceLastTap = now - lastTapRef.current

    if (timeSinceLastTap < 300) {
      // Double tap detected
      onLike()
      setShowHeart(true)

      setTimeout(() => setShowHeart(false), 1000)
    }

    lastTapRef.current = now
  }

  return (
    <div style={{ position: 'relative' }}>
      <motion.img
        src={src}
        onTap={handleTap}
        whileTap={{ scale: 0.98 }}
        style={{
          width: '100%',
          borderRadius: 12,
          cursor: 'pointer'
        }}
      />

      {/* Heart animation */}
      {showHeart && (
        <motion.div
          initial={{ scale: 0, opacity: 1 }}
          animate={{ scale: 1.5, opacity: 0 }}
          transition={{ duration: 0.8 }}
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            fontSize: 80,
            pointerEvents: 'none'
          }}
        >
          ❤️
        </motion.div>
      )}
    </div>
  )
}
```

**Double Tap**:
- **Detection**: < 300ms between taps
- **Feedback**: Heart appears and scales up
- **Fade out**: Heart fades after 1 second

---

## Multi-Touch (Pinch/Rotate)

### Pattern: Pinch to Zoom (Touch Devices)

**Note**: Framer Motion doesn't have built-in pinch gestures. Use native touch events.

**Implementation**:
```tsx
import { motion, useMotionValue } from 'framer-motion'
import { useRef, useEffect } from 'react'

export function PinchZoomImage({ src }) {
  const scale = useMotionValue(1)
  const lastDistanceRef = useRef(0)

  useEffect(() => {
    const element = document.getElementById('pinch-image')
    if (!element) return

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault()

        const touch1 = e.touches[0]
        const touch2 = e.touches[1]

        const distance = Math.hypot(
          touch2.pageX - touch1.pageX,
          touch2.pageY - touch1.pageY
        )

        if (lastDistanceRef.current > 0) {
          const delta = distance - lastDistanceRef.current
          const newScale = Math.min(Math.max(scale.get() + delta * 0.01, 0.5), 3)
          scale.set(newScale)
        }

        lastDistanceRef.current = distance
      }
    }

    const handleTouchEnd = () => {
      lastDistanceRef.current = 0
    }

    element.addEventListener('touchmove', handleTouchMove, { passive: false })
    element.addEventListener('touchend', handleTouchEnd)

    return () => {
      element.removeEventListener('touchmove', handleTouchMove)
      element.removeEventListener('touchend', handleTouchEnd)
    }
  }, [scale])

  return (
    <motion.img
      id="pinch-image"
      src={src}
      style={{
        scale,
        width: '100%',
        touchAction: 'none'
      }}
    />
  )
}
```

**Pinch Zoom**:
- **Two-finger detection**: Calculates distance between touches
- **Scale calculation**: Delta distance → scale change
- **Limits**: 0.5x to 3x zoom
- **Touch action**: Prevents default pinch-to-zoom

---

## Custom Gesture Handlers

### Pattern: Custom Velocity-Based Throw

**Use Case**: Physics-based interactions

**Implementation**:
```tsx
import { motion, useMotionValue, useVelocity, useSpring } from 'framer-motion'

export function ThrowableObject() {
  const x = useMotionValue(0)
  const y = useMotionValue(0)

  const velocityX = useVelocity(x)
  const velocityY = useVelocity(y)

  const springX = useSpring(x, { stiffness: 200, damping: 20 })
  const springY = useSpring(y, { stiffness: 200, damping: 20 })

  const handleDragEnd = () => {
    const vx = velocityX.get()
    const vy = velocityY.get()

    // Apply momentum
    x.set(x.get() + vx * 0.1)
    y.set(y.get() + vy * 0.1)

    // Bounce back to center
    setTimeout(() => {
      x.set(0)
      y.set(0)
    }, 500)
  }

  return (
    <motion.div
      drag
      dragElastic={1}
      onDragEnd={handleDragEnd}
      style={{
        x: springX,
        y: springY,
        width: 100,
        height: 100,
        backgroundColor: '#6366F1',
        borderRadius: '50%',
        cursor: 'grab'
      }}
      whileDrag={{ cursor: 'grabbing', scale: 1.2 }}
    />
  )
}
```

**Physics Simulation**:
- **Velocity tracking**: Monitors drag speed
- **Momentum**: Continues moving after release
- **Spring**: Smooth return to origin
- **Timing**: 500ms before snapping back

---

## Gesture Accessibility

### Keyboard Alternatives

```tsx
import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'

export function AccessibleDraggable() {
  const [position, setPosition] = useState({ x: 0, y: 0 })

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const step = 10

      if (e.key === 'ArrowLeft') setPosition(p => ({ ...p, x: p.x - step }))
      if (e.key === 'ArrowRight') setPosition(p => ({ ...p, x: p.x + step }))
      if (e.key === 'ArrowUp') setPosition(p => ({ ...p, y: p.y - step }))
      if (e.key === 'ArrowDown') setPosition(p => ({ ...p, y: p.y + step }))
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <motion.div
      drag
      animate={position}
      style={{
        width: 100,
        height: 100,
        backgroundColor: '#6366F1',
        borderRadius: 12,
        cursor: 'grab'
      }}
      tabIndex={0}
      role="button"
      aria-label="Draggable element (use arrow keys)"
    />
  )
}
```

**Accessibility**:
- **Keyboard**: Arrow keys for movement
- **Focus**: Tab-able element
- **ARIA**: Screen reader labels
- **Both**: Works with mouse AND keyboard

---

**All gestures tested on**: Desktop (mouse), Tablet (touch), Mobile (touch + multi-touch)
