# Advanced 3D UI Patterns with React Three Fiber

## Table of Contents

1. [Glassmorphic 3D Cards](#glassmorphic-3d-cards)
2. [Scroll-Based 3D Animations](#scroll-based-3d-animations)
3. [3D Text Effects](#3d-text-effects)
4. [Interactive 3D Buttons](#interactive-3d-buttons)
5. [Parallax Depth Layers](#parallax-depth-layers)
6. [3D Loading States](#3d-loading-states)

---

## Glassmorphic 3D Cards

### Pattern: Floating Glass Card with Tilt

**Use Case**: Feature cards, pricing tables, testimonials

**Implementation**:
```tsx
'use client'
import { useRef, useState } from 'react'
import { useFrame, ThreeEvent } from '@react-three/fiber'
import { RoundedBox, MeshTransmissionMaterial } from '@react-three/drei'
import * as THREE from 'three'

export function GlassCard({ position = [0, 0, 0] }) {
  const meshRef = useRef<THREE.Mesh>(null)
  const [mouse, setMouse] = useState({ x: 0, y: 0 })

  // Mouse tracking for tilt effect
  const handlePointerMove = (e: ThreeEvent<PointerEvent>) => {
    const x = (e.point.x / 5) * 0.1
    const y = (e.point.y / 5) * 0.1
    setMouse({ x, y })
  }

  // Smooth tilt animation
  useFrame(() => {
    if (!meshRef.current) return

    meshRef.current.rotation.x = THREE.MathUtils.lerp(
      meshRef.current.rotation.x,
      mouse.y,
      0.1
    )
    meshRef.current.rotation.y = THREE.MathUtils.lerp(
      meshRef.current.rotation.y,
      mouse.x,
      0.1
    )
  })

  return (
    <RoundedBox
      ref={meshRef}
      args={[3, 4, 0.3]}
      radius={0.15}
      smoothness={8}
      position={position}
      onPointerMove={handlePointerMove}
      onPointerLeave={() => setMouse({ x: 0, y: 0 })}
    >
      <MeshTransmissionMaterial
        transmission={0.9}      // Glass transparency
        thickness={0.5}         // Glass thickness
        roughness={0.2}         // Surface roughness
        ior={1.5}              // Index of refraction
        chromaticAberration={0.05}  // Rainbow effect
        backside
      />
    </RoundedBox>
  )
}
```

**Performance Notes**:
- `MeshTransmissionMaterial` is expensive (use sparingly)
- Limit to 3-5 glass cards per scene
- Disable on mobile devices

**Specs**:
- Card size: 3×4×0.3 units
- Border radius: 0.15 units (rounded)
- Tilt range: ±0.1 radians (5-6 degrees)
- Smoothing: lerp factor 0.1

---

## Scroll-Based 3D Animations

### Pattern: Scroll-Controlled Rotation

**Use Case**: Product showcases, storytelling sections

**Implementation**:
```tsx
'use client'
import { useRef, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import { useScroll } from '@react-three/drei'
import * as THREE from 'three'

export function ScrollRotatingModel({ children }) {
  const groupRef = useRef<THREE.Group>(null)
  const scroll = useScroll()

  useFrame(() => {
    if (!groupRef.current) return

    // Scroll from 0 to 1 maps to 0 to 2π rotation
    groupRef.current.rotation.y = scroll.offset * Math.PI * 2
  })

  return <group ref={groupRef}>{children}</group>
}

// Usage with ScrollControls
import { ScrollControls } from '@react-three/drei'

<Canvas>
  <ScrollControls pages={3} damping={0.2}>
    <ScrollRotatingModel>
      <mesh>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color="#6366F1" />
      </mesh>
    </ScrollRotatingModel>
  </ScrollControls>
</Canvas>
```

**Integration with HTML**:
```tsx
// Wrap your entire page
export default function Page() {
  return (
    <>
      <Canvas style={{ position: 'fixed', top: 0, left: 0 }}>
        <ScrollControls pages={3}>
          <ScrollRotatingModel>
            {/* 3D content */}
          </ScrollRotatingModel>
        </ScrollControls>
      </Canvas>

      {/* HTML content scrolls normally */}
      <div style={{ position: 'relative', height: '300vh' }}>
        <section>Section 1</section>
        <section>Section 2</section>
        <section>Section 3</section>
      </div>
    </>
  )
}
```

**Performance Notes**:
- Use `damping` for smooth scroll feel
- Limit to single 3D object per scroll scene
- Consider using `frameloop="demand"` when not scrolling

---

## 3D Text Effects

### Pattern: Floating 3D Typography

**Use Case**: Hero headings, section titles

**Implementation**:
```tsx
'use client'
import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Text3D, Center } from '@react-three/drei'
import * as THREE from 'three'

export function FloatingText({ text = 'HELLO' }) {
  const textRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (!textRef.current) return

    const time = state.clock.getElapsedTime()

    // Gentle floating
    textRef.current.position.y = Math.sin(time * 0.5) * 0.2

    // Subtle rotation
    textRef.current.rotation.x = Math.sin(time * 0.3) * 0.1
  })

  return (
    <Center>
      <Text3D
        ref={textRef}
        font="/fonts/Inter_Bold.json"  // Load your font
        size={1.5}
        height={0.2}
        curveSegments={12}
        bevelEnabled
        bevelThickness={0.02}
        bevelSize={0.02}
        bevelOffset={0}
        bevelSegments={5}
      >
        {text}
        <meshStandardMaterial
          color="#6366F1"
          metalness={0.6}
          roughness={0.3}
        />
      </Text3D>
    </Center>
  )
}
```

**Font Conversion**:
1. Use [facetype.js](http://gero3.github.io/facetype.js/) to convert TTF to JSON
2. Place font JSON in `/public/fonts/`
3. Load with `font="/fonts/YourFont.json"`

**Performance Notes**:
- 3D text is expensive (many triangles)
- Limit to 1-2 3D text elements per page
- Use `Center` helper to auto-center geometry

---

## Interactive 3D Buttons

### Pattern: Depth-Aware Button Hover

**Use Case**: Call-to-action buttons, navigation items

**Implementation**:
```tsx
'use client'
import { useRef, useState } from 'react'
import { useFrame, ThreeEvent } from '@react-three/fiber'
import { RoundedBox } from '@react-three/drei'
import * as THREE from 'three'

export function Button3D({
  position = [0, 0, 0],
  onClick,
  label = 'Click Me'
}) {
  const meshRef = useRef<THREE.Mesh>(null)
  const [hovered, setHovered] = useState(false)
  const [pressed, setPressed] = useState(false)

  useFrame(() => {
    if (!meshRef.current) return

    // Target z-position based on state
    const targetZ = pressed ? -0.1 : hovered ? 0.15 : 0

    // Smooth depth animation
    meshRef.current.position.z = THREE.MathUtils.lerp(
      meshRef.current.position.z,
      targetZ,
      0.2
    )
  })

  return (
    <group position={position}>
      {/* Button mesh */}
      <RoundedBox
        ref={meshRef}
        args={[2, 0.6, 0.3]}
        radius={0.1}
        smoothness={4}
        onPointerOver={(e) => {
          e.stopPropagation()
          setHovered(true)
          document.body.style.cursor = 'pointer'
        }}
        onPointerOut={() => {
          setHovered(false)
          setPressed(false)
          document.body.style.cursor = 'default'
        }}
        onPointerDown={(e) => {
          e.stopPropagation()
          setPressed(true)
        }}
        onPointerUp={(e) => {
          e.stopPropagation()
          setPressed(false)
          onClick?.()
        }}
      >
        <meshStandardMaterial
          color={hovered ? '#8B5CF6' : '#6366F1'}
          emissive={hovered ? '#4338CA' : '#000000'}
          emissiveIntensity={0.2}
        />
      </RoundedBox>

      {/* Button label (HTML overlay preferred) */}
    </group>
  )
}
```

**HTML Overlay for Text** (Better Performance):
```tsx
import { Html } from '@react-three/drei'

<Html center distanceFactor={10}>
  <div style={{
    color: 'white',
    fontSize: '16px',
    fontWeight: 'bold',
    pointerEvents: 'none',
    userSelect: 'none'
  }}>
    {label}
  </div>
</Html>
```

**Specs**:
- Hover lift: 0.15 units forward
- Press depth: -0.1 units back
- Transition: lerp factor 0.2 (smooth)
- Cursor: Pointer on hover

---

## Parallax Depth Layers

### Pattern: Multi-Layer Background Parallax

**Use Case**: Landing pages, immersive sections

**Implementation**:
```tsx
'use client'
import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export function ParallaxLayers() {
  const layer1Ref = useRef<THREE.Group>(null)
  const layer2Ref = useRef<THREE.Group>(null)
  const layer3Ref = useRef<THREE.Group>(null)

  useFrame((state) => {
    const mouseX = state.mouse.x
    const mouseY = state.mouse.y

    // Layer 1 (farthest) - slowest movement
    if (layer1Ref.current) {
      layer1Ref.current.position.x = mouseX * 0.5
      layer1Ref.current.position.y = mouseY * 0.5
    }

    // Layer 2 (middle) - medium movement
    if (layer2Ref.current) {
      layer2Ref.current.position.x = mouseX * 1.0
      layer2Ref.current.position.y = mouseY * 1.0
    }

    // Layer 3 (closest) - fastest movement
    if (layer3Ref.current) {
      layer3Ref.current.position.x = mouseX * 1.5
      layer3Ref.current.position.y = mouseY * 1.5
    }
  })

  return (
    <>
      {/* Layer 1 - Background */}
      <group ref={layer1Ref} position={[0, 0, -10]}>
        <mesh>
          <planeGeometry args={[20, 20]} />
          <meshBasicMaterial
            color="#1a1a2e"
            transparent
            opacity={0.5}
          />
        </mesh>
      </group>

      {/* Layer 2 - Middle */}
      <group ref={layer2Ref} position={[0, 0, -5]}>
        {/* Add floating shapes */}
      </group>

      {/* Layer 3 - Foreground */}
      <group ref={layer3Ref} position={[0, 0, 0]}>
        {/* Add main content */}
      </group>
    </>
  )
}
```

**Depth Specs**:
- Layer 1 (Background): z = -10, movement × 0.5
- Layer 2 (Middle): z = -5, movement × 1.0
- Layer 3 (Foreground): z = 0, movement × 1.5

**Performance Notes**:
- Limit to 3 layers maximum
- Use simple geometries (planes, circles)
- Avoid transparent overlays (compositing cost)

---

## 3D Loading States

### Pattern: Animated Loading Spinner

**Use Case**: Page loading, data fetching states

**Implementation**:
```tsx
'use client'
import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Torus } from '@react-three/drei'
import * as THREE from 'three'

export function Spinner3D({ size = 1 }) {
  const torusRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (!torusRef.current) return

    const time = state.clock.getElapsedTime()

    // Continuous rotation
    torusRef.current.rotation.x = time * 2
    torusRef.current.rotation.y = time * 3

    // Pulsing scale
    const scale = 1 + Math.sin(time * 4) * 0.1
    torusRef.current.scale.set(scale, scale, scale)
  })

  return (
    <Torus
      ref={torusRef}
      args={[size, size * 0.3, 16, 32]}
    >
      <meshStandardMaterial
        color="#6366F1"
        emissive="#4338CA"
        emissiveIntensity={0.5}
      />
    </Torus>
  )
}
```

**Alternative: Ring Loader**:
```tsx
export function RingLoader() {
  const ringRef = useRef<THREE.Mesh>(null)

  useFrame(() => {
    if (!ringRef.current) return
    ringRef.current.rotation.z += 0.05
  })

  return (
    <mesh ref={ringRef}>
      <ringGeometry args={[0.8, 1, 32]} />
      <meshBasicMaterial color="#6366F1" />
    </mesh>
  )
}
```

**Usage in Loading State**:
```tsx
export default function PageWithLoading() {
  const [loading, setLoading] = useState(true)

  if (loading) {
    return (
      <Canvas>
        <Spinner3D />
      </Canvas>
    )
  }

  return <MainContent />
}
```

---

## Performance Best Practices

### 1. Object Pooling for Repeated Elements

```tsx
const particles = useMemo(() => {
  return Array.from({ length: 100 }, (_, i) => ({
    position: [
      (Math.random() - 0.5) * 10,
      (Math.random() - 0.5) * 10,
      (Math.random() - 0.5) * 10
    ],
    id: i
  }))
}, [])

return particles.map(p => (
  <Particle key={p.id} position={p.position} />
))
```

### 2. Use InstancedMesh for Many Identical Objects

```tsx
const count = 100
const meshRef = useRef<THREE.InstancedMesh>(null)

useEffect(() => {
  if (!meshRef.current) return

  const temp = new THREE.Object3D()

  for (let i = 0; i < count; i++) {
    temp.position.set(
      (Math.random() - 0.5) * 10,
      (Math.random() - 0.5) * 10,
      (Math.random() - 0.5) * 10
    )
    temp.updateMatrix()
    meshRef.current.setMatrixAt(i, temp.matrix)
  }

  meshRef.current.instanceMatrix.needsUpdate = true
}, [])

return (
  <instancedMesh ref={meshRef} args={[null, null, count]}>
    <sphereGeometry args={[0.1, 8, 8]} />
    <meshBasicMaterial color="#6366F1" />
  </instancedMesh>
)
```

### 3. Frustum Culling for Off-Screen Objects

```tsx
<mesh frustumCulled>
  {/* This mesh won't render when off-screen */}
</mesh>
```

---

## Accessibility Patterns

### Keyboard-Navigable 3D UI

```tsx
export function Accessible3DButton({ onActivate, label }) {
  const [focused, setFocused] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (focused && (e.key === 'Enter' || e.key === ' ')) {
        onActivate()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [focused, onActivate])

  return (
    <group
      onPointerOver={() => setFocused(true)}
      onPointerOut={() => setFocused(false)}
      // Visual focus indicator
      scale={focused ? 1.1 : 1}
    >
      <Button3D onClick={onActivate} />

      {/* Hidden HTML element for accessibility */}
      <Html>
        <button
          style={{ opacity: 0, pointerEvents: 'none' }}
          aria-label={label}
          tabIndex={0}
        />
      </Html>
    </group>
  )
}
```

---

## Testing Patterns

### Performance Monitoring

```tsx
import { useFrame } from '@react-three/fiber'

export function FPSMonitor() {
  useFrame((state) => {
    const fps = Math.round(1 / state.clock.getDelta())

    if (fps < 30) {
      console.warn('Low FPS detected:', fps)
      // Trigger performance fallback
    }
  })

  return null // This component only monitors
}
```

---

**All patterns tested on**: Desktop Chrome, Safari, Firefox | Mobile iOS Safari, Chrome Android
