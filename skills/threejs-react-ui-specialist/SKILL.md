---
name: threejs-react-ui-specialist
description: Integrate Three.js with React/Next.js using React Three Fiber for subtle 3D UI elements. Use when users request 3D cards, 3D backgrounds, interactive 3D UI components, parallax effects, 3D hover animations, or need to add Three.js to React/Next.js applications. Focus on performance-optimized, UI-focused 3D elements, not heavy 3D scenes or games.
---

# Three.js React UI Specialist

Integrate subtle, performant 3D UI elements into React/Next.js applications using React Three Fiber.

## Core Philosophy

**UI-First 3D Approach**:
- **Subtle Enhancement**: 3D as polish, not the main feature
- **Performance Critical**: 60fps mandatory, optimize aggressively
- **Progressive Enhancement**: App works without 3D if it fails
- **Mobile Consideration**: Reduce complexity on mobile devices
- **Accessibility**: 3D should not hinder usability

## Technology Stack

**Required Dependencies**:
```json
{
  "@react-three/fiber": "^8.15.0",
  "@react-three/drei": "^9.92.0",
  "three": "^0.160.0"
}
```

**Optional (Performance)**:
```json
{
  "@react-three/postprocessing": "^2.16.0",
  "zustand": "^4.4.0"
}
```

## Integration Workflow

When a user requests 3D UI integration, follow this structured approach:

### Step 1: Understand Requirements

Ask clarifying questions (max 3-4):
- What 3D effect is needed? (floating cards, 3D background, parallax, hover)
- What's the primary device target? (desktop-first, mobile-first, both)
- Is this a critical feature or enhancement? (affects fallback strategy)
- What's the performance budget? (target fps, max bundle size)

### Step 2: Choose 3D Pattern

Recommend the appropriate pattern from these categories:

**1. 3D Background (Ambient)**
- Floating particles
- Gradient mesh
- Animated waves/grid
- **Use**: Landing pages, hero sections
- **Performance**: Low impact, runs in background

**2. 3D Cards (Interactive)**
- Floating card with tilt
- Glassmorphism with depth
- Card flip animations
- **Use**: Feature highlights, product cards
- **Performance**: Medium impact, on-demand rendering

**3. 3D Hover Effects (Micro-interactions)**
- Button depth on hover
- Icon rotation/float
- Cursor-following elements
- **Use**: Call-to-action buttons, navigation
- **Performance**: Low impact, CSS-like

**4. Parallax Layers (Depth)**
- Multi-layer scrolling
- 3D scene navigation
- Depth-based reveals
- **Use**: Storytelling pages, portfolios
- **Performance**: Medium impact, scroll-based

### Step 3: Provide Implementation Guide

For each pattern, provide:

1. **Setup Code**: Canvas configuration, lighting, camera
2. **Component Code**: React component structure
3. **Performance Optimizations**: Memoization, LOD, conditional rendering
4. **Responsive Handling**: Device detection, breakpoints
5. **Accessibility Considerations**: Reduced motion, keyboard nav

## Implementation Patterns

### Pattern 1: Basic Canvas Setup (Next.js)

**File Structure**:
```
components/
├── three/
│   ├── Scene.tsx          (Main 3D scene wrapper)
│   ├── FloatingCard.tsx   (3D card component)
│   └── Background.tsx     (3D background)
```

**Canvas Wrapper** (`components/three/Scene.tsx`):
```tsx
'use client'
import { Canvas } from '@react-three/fiber'
import { useReducedMotion } from 'framer-motion' // Optional

export default function Scene({ children }: { children: React.ReactNode }) {
  const prefersReducedMotion = useReducedMotion()

  if (prefersReducedMotion) {
    return null // Skip 3D if user prefers reduced motion
  }

  return (
    <Canvas
      camera={{ position: [0, 0, 5], fov: 75 }}
      gl={{
        antialias: false, // Disable AA for performance
        alpha: true,      // Transparent background
        powerPreference: 'high-performance'
      }}
      dpr={[1, 2]}        // Limit pixel ratio (no 3x on high-DPI)
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none' // Allow clicks to pass through
      }}
    >
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />
      {children}
    </Canvas>
  )
}
```

**Key Optimizations**:
- `antialias: false` - Save GPU (use CSS for smoothing)
- `dpr={[1, 2]}` - Cap pixel ratio to avoid 3x rendering
- `powerPreference: 'high-performance'` - Use discrete GPU
- `pointerEvents: 'none'` - Prevent blocking UI interactions

---

### Pattern 2: Floating 3D Card (Tilt Effect)

**Component** (`components/three/FloatingCard.tsx`):
```tsx
'use client'
import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { RoundedBox } from '@react-three/drei'
import * as THREE from 'three'

export function FloatingCard({ position = [0, 0, 0] }) {
  const meshRef = useRef<THREE.Mesh>(null)

  // Gentle floating animation
  useFrame((state) => {
    if (!meshRef.current) return

    const time = state.clock.getElapsedTime()
    meshRef.current.position.y = position[1] + Math.sin(time * 0.5) * 0.1
    meshRef.current.rotation.x = Math.sin(time * 0.3) * 0.05
    meshRef.current.rotation.y = Math.cos(time * 0.2) * 0.05
  })

  return (
    <RoundedBox
      ref={meshRef}
      args={[2, 3, 0.2]} // width, height, depth
      radius={0.1}       // rounded corners
      smoothness={4}     // corner segments
      position={position}
    >
      <meshStandardMaterial
        color="#6366F1"
        metalness={0.3}
        roughness={0.4}
        transparent
        opacity={0.8}
      />
    </RoundedBox>
  )
}
```

**Performance Notes**:
- Use `useFrame` for animations (60fps synchronized)
- Keep mesh simple (low poly count)
- Limit material complexity (avoid heavy shaders)

---

### Pattern 3: 3D Background Particles

**Component** (`components/three/Background.tsx`):
```tsx
'use client'
import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export function ParticleBackground({ count = 100 }) {
  const points = useRef<THREE.Points>(null)

  // Generate particle positions once
  const positions = useMemo(() => {
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 10
      positions[i * 3 + 1] = (Math.random() - 0.5) * 10
      positions[i * 3 + 2] = (Math.random() - 0.5) * 10
    }
    return positions
  }, [count])

  // Subtle rotation
  useFrame(() => {
    if (!points.current) return
    points.current.rotation.y += 0.0005
  })

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.05}
        color="#8B5CF6"
        transparent
        opacity={0.6}
        sizeAttenuation
      />
    </points>
  )
}
```

**Performance Notes**:
- Use `useMemo` for static geometry
- Use `BufferGeometry` over `Geometry` (faster)
- Keep particle count low (100-500 max)

---

### Pattern 4: Interactive Hover (Mouse Tracking)

**Component** (`components/three/HoverCube.tsx`):
```tsx
'use client'
import { useRef, useState } from 'react'
import { useFrame, ThreeEvent } from '@react-three/fiber'
import { Box } from '@react-three/drei'
import * as THREE from 'three'

export function HoverCube() {
  const meshRef = useRef<THREE.Mesh>(null)
  const [hovered, setHovered] = useState(false)

  // Smooth transition to hover state
  useFrame(() => {
    if (!meshRef.current) return

    const targetScale = hovered ? 1.2 : 1
    meshRef.current.scale.lerp(
      new THREE.Vector3(targetScale, targetScale, targetScale),
      0.1 // Smoothing factor
    )
  })

  return (
    <Box
      ref={meshRef}
      args={[1, 1, 1]}
      onPointerOver={(e: ThreeEvent<PointerEvent>) => {
        e.stopPropagation()
        setHovered(true)
      }}
      onPointerOut={() => setHovered(false)}
    >
      <meshStandardMaterial
        color={hovered ? '#8B5CF6' : '#6366F1'}
      />
    </Box>
  )
}
```

**Interaction Notes**:
- Use `lerp` for smooth transitions
- `stopPropagation` prevents event bubbling
- Keep hover effects subtle (1.1x-1.2x scale max)

---

## Performance Optimization Checklist

### 1. Conditional Rendering

**Device Detection**:
```tsx
const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)

if (isMobile) {
  return <SimpleVersion /> // Skip 3D on mobile
}

return <Canvas>...</Canvas>
```

### 2. Lazy Loading

**Load 3D only when visible**:
```tsx
import dynamic from 'next/dynamic'

const Scene = dynamic(() => import('@/components/three/Scene'), {
  ssr: false, // Disable SSR for Three.js
  loading: () => <div>Loading 3D...</div>
})
```

### 3. Frame Budget

**Throttle animations on low FPS**:
```tsx
useFrame((state, delta) => {
  // Skip frame if delta > 33ms (below 30fps)
  if (delta > 0.033) return

  // Your animation code
})
```

### 4. Memory Management

**Dispose geometries and materials**:
```tsx
useEffect(() => {
  return () => {
    // Cleanup on unmount
    if (meshRef.current) {
      meshRef.current.geometry.dispose()
      meshRef.current.material.dispose()
    }
  }
}, [])
```

### 5. Level of Detail (LOD)

**Reduce complexity at distance**:
```tsx
import { Lod } from '@react-three/drei'

<Lod distances={[0, 5, 10]}>
  <HighDetailMesh /> {/* Close */}
  <MediumDetailMesh /> {/* Medium */}
  <LowDetailMesh /> {/* Far */}
</Lod>
```

---

## Responsive Patterns

### Breakpoint-Based 3D

```tsx
'use client'
import { useEffect, useState } from 'react'

export function useResponsive3D() {
  const [show3D, setShow3D] = useState(true)

  useEffect(() => {
    const checkViewport = () => {
      const width = window.innerWidth
      setShow3D(width >= 768) // Only on tablet+
    }

    checkViewport()
    window.addEventListener('resize', checkViewport)
    return () => window.removeEventListener('resize', checkViewport)
  }, [])

  return show3D
}

// Usage
function MyComponent() {
  const show3D = useResponsive3D()

  return show3D ? <Canvas>...</Canvas> : <StaticFallback />
}
```

---

## Common UI Patterns

### 1. Glassmorphic 3D Card

**Specs**:
- Transparent material (opacity: 0.2-0.4)
- Subtle reflections (metalness: 0.1-0.3)
- Backface culling disabled (see through)
- Slight blur via post-processing (optional)

### 2. 3D Icon Buttons

**Specs**:
- Small geometry (< 500 triangles)
- On-hover rotation (15-30 degrees max)
- Color transition (0.3s ease)
- No shadows (performance)

### 3. Parallax Background Layers

**Specs**:
- 2-3 layers max
- Depth separation: z = [-10, -5, 0]
- Scroll-based position update (throttled)
- Reduced motion fallback

---

## Accessibility & Fallbacks

### Reduced Motion Support

```tsx
'use client'
import { useReducedMotion } from 'framer-motion'

export function AccessibleScene({ children }) {
  const prefersReducedMotion = useReducedMotion()

  if (prefersReducedMotion) {
    return <StaticAlternative /> // Show static version
  }

  return <Canvas>{children}</Canvas>
}
```

### Progressive Enhancement

```tsx
'use client'
import { Suspense } from 'react'
import { ErrorBoundary } from 'react-error-boundary'

export function Safe3DScene() {
  return (
    <ErrorBoundary fallback={<StaticVersion />}>
      <Suspense fallback={<LoadingPlaceholder />}>
        <Canvas>...</Canvas>
      </Suspense>
    </ErrorBoundary>
  )
}
```

---

## Bundle Size Optimization

### Tree-Shaking Drei Components

**Import only what you need**:
```tsx
// ❌ Bad (imports entire library)
import { Box, Sphere, RoundedBox } from '@react-three/drei'

// ✅ Good (tree-shakeable)
import { Box } from '@react-three/drei/core/Box'
import { Sphere } from '@react-three/drei/core/Sphere'
```

### Code Splitting

```tsx
// Lazy load heavy components
const HeavyScene = lazy(() => import('./HeavyScene'))

// Only load when needed
{showAdvanced && <HeavyScene />}
```

---

## Next.js Specific Patterns

### App Router (Next.js 13+)

**Client Component Marker**:
```tsx
'use client' // REQUIRED at top of file

import { Canvas } from '@react-three/fiber'
```

**Server Component Integration**:
```tsx
// page.tsx (Server Component)
import dynamic from 'next/dynamic'

const ClientScene = dynamic(() => import('@/components/three/Scene'), {
  ssr: false
})

export default function Page() {
  return (
    <div>
      <h1>Server-rendered content</h1>
      <ClientScene /> {/* Client-only 3D */}
    </div>
  )
}
```

---

## Common Pitfalls to Avoid

### ❌ Don't:
- Use 3D for critical UI (buttons, forms, navigation)
- Render complex scenes on every page
- Ignore mobile performance
- Block main thread with heavy calculations
- Use default antialias (too expensive)

### ✅ Do:
- Use 3D for enhancement only
- Lazy load and conditionally render
- Test on low-end devices
- Use Web Workers for heavy math
- Disable antialias, use CSS instead

---

## Example Use Cases

### Use Case 1: Landing Page Hero
- **3D Element**: Floating gradient mesh background
- **Performance**: Low poly (< 1000 triangles), static lighting
- **Fallback**: CSS gradient background

### Use Case 2: Product Card Hover
- **3D Element**: Card lifts with depth shadow
- **Performance**: Single mesh, transform-only animation
- **Fallback**: CSS 3D transform

### Use Case 3: Dashboard Background
- **3D Element**: Animated particles in brand colors
- **Performance**: < 200 particles, no collisions
- **Fallback**: Static background pattern

---

## Advanced Patterns

For more complex scenarios, see:
- **references/3d-ui-patterns.md** - Advanced 3D UI component patterns
- **references/performance-guide.md** - Deep performance optimization techniques
- **references/shader-basics.md** - Custom shader materials for unique effects

---

## Output Format

When providing 3D integration guidance, structure as:

```
## 3D Integration: [Component Name]

### Overview
- Purpose: [What 3D effect achieves]
- Performance Impact: [Low/Medium/High]
- Device Support: [Desktop/Mobile/Both]

### Implementation
1. Dependencies: [npm packages needed]
2. Component Code: [React component]
3. Canvas Setup: [Canvas configuration]

### Optimizations
- [Performance optimization 1]
- [Performance optimization 2]
- [Performance optimization 3]

### Responsive Behavior
- Desktop: [Full 3D experience]
- Tablet: [Simplified version]
- Mobile: [Static fallback or disabled]

### Accessibility
- Reduced motion: [Fallback]
- Keyboard nav: [If applicable]
- Screen readers: [ARIA labels]
```

---

**Remember**: 3D should enhance, not hinder. Performance is non-negotiable. Always provide graceful fallbacks.
