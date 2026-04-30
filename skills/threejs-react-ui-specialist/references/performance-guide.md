# Performance Optimization Guide for React Three Fiber

## Table of Contents

1. [Performance Budget](#performance-budget)
2. [Rendering Optimizations](#rendering-optimizations)
3. [Memory Management](#memory-management)
4. [Bundle Size Optimization](#bundle-size-optimization)
5. [Mobile Optimization](#mobile-optimization)
6. [Profiling & Debugging](#profiling--debugging)

---

## Performance Budget

### Target Metrics

**Desktop (Required)**:
- 60 FPS (16.67ms/frame) minimum
- Initial 3D load: < 500ms
- Bundle size: < 200KB (gzipped)
- Memory: < 100MB heap growth

**Mobile (Required)**:
- 30 FPS (33.33ms/frame) minimum
- Initial 3D load: < 1000ms
- Bundle size: < 150KB (gzipped)
- Memory: < 50MB heap growth

**Graceful Degradation**:
- Drop to 30 FPS on low-end devices
- Disable 3D entirely if < 20 FPS sustained
- Show static fallback if WebGL unavailable

---

## Rendering Optimizations

### 1. Frame Budget Management

**Skip Expensive Frames**:
```tsx
import { useFrame } from '@react-three/fiber'

export function OptimizedComponent() {
  const [skipFrames, setSkipFrames] = useState(0)

  useFrame((state, delta) => {
    // If frame took > 33ms (below 30fps), skip next frame
    if (delta > 0.033) {
      setSkipFrames(2) // Skip 2 frames to recover
      return
    }

    if (skipFrames > 0) {
      setSkipFrames(prev => prev - 1)
      return
    }

    // Your animation code here
  })

  return null
}
```

### 2. Demand-Based Rendering

**Only render when necessary**:
```tsx
import { Canvas } from '@react-three/fiber'

// Option 1: Never render unless state changes
<Canvas frameloop="demand">
  {/* Static scene */}
</Canvas>

// Option 2: Start/stop rendering conditionally
export function ConditionalRender() {
  const [active, setActive] = useState(false)

  return (
    <Canvas frameloop={active ? 'always' : 'demand'}>
      {/* Scene */}
    </Canvas>
  )
}
```

### 3. Level of Detail (LOD)

**Reduce complexity based on distance**:
```tsx
import { Lod } from '@react-three/drei'

export function LODModel() {
  return (
    <Lod distances={[0, 10, 20]}>
      {/* Close: High detail (1000 tris) */}
      <mesh>
        <icosahedronGeometry args={[1, 3]} />
        <meshStandardMaterial />
      </mesh>

      {/* Medium: Medium detail (500 tris) */}
      <mesh>
        <icosahedronGeometry args={[1, 2]} />
        <meshStandardMaterial />
      </mesh>

      {/* Far: Low detail (100 tris) */}
      <mesh>
        <icosahedronGeometry args={[1, 1]} />
        <meshStandardMaterial />
      </mesh>
    </Lod>
  )
}
```

### 4. Frustum Culling

**Don't render off-screen objects**:
```tsx
// Enabled by default, but can be explicit
<mesh frustumCulled>
  <boxGeometry />
  <meshBasicMaterial />
</mesh>

// For dynamic scenes with camera movement
<mesh frustumCulled onAfterRender={(renderer, scene, camera) => {
  // Object was rendered (visible in frustum)
}} />
```

### 5. Instanced Rendering

**Render many identical objects efficiently**:
```tsx
import { useRef, useMemo } from 'react'
import * as THREE from 'three'

export function InstancedParticles({ count = 1000 }) {
  const meshRef = useRef<THREE.InstancedMesh>(null)

  // Pre-calculate positions once
  const positions = useMemo(() => {
    return Array.from({ length: count }, () => ({
      x: (Math.random() - 0.5) * 20,
      y: (Math.random() - 0.5) * 20,
      z: (Math.random() - 0.5) * 20,
    }))
  }, [count])

  useEffect(() => {
    if (!meshRef.current) return

    const temp = new THREE.Object3D()

    positions.forEach((pos, i) => {
      temp.position.set(pos.x, pos.y, pos.z)
      temp.updateMatrix()
      meshRef.current!.setMatrixAt(i, temp.matrix)
    })

    meshRef.current.instanceMatrix.needsUpdate = true
  }, [positions])

  return (
    <instancedMesh ref={meshRef} args={[null, null, count]}>
      <sphereGeometry args={[0.1, 8, 8]} />
      <meshBasicMaterial color="#6366F1" />
    </instancedMesh>
  )
}
```

**Performance Gain**: 100 individual meshes vs 1 instanced mesh = **10-50x faster**

---

## Memory Management

### 1. Dispose Geometries and Materials

**Always clean up on unmount**:
```tsx
import { useEffect, useRef } from 'react'
import * as THREE from 'three'

export function DisposableComponent() {
  const meshRef = useRef<THREE.Mesh>(null)

  useEffect(() => {
    return () => {
      if (meshRef.current) {
        // Dispose geometry
        meshRef.current.geometry.dispose()

        // Dispose material(s)
        if (Array.isArray(meshRef.current.material)) {
          meshRef.current.material.forEach(m => m.dispose())
        } else {
          meshRef.current.material.dispose()
        }

        // Dispose textures if any
        const material = meshRef.current.material
        if (material.map) material.map.dispose()
        if (material.normalMap) material.normalMap.dispose()
        if (material.roughnessMap) material.roughnessMap.dispose()
      }
    }
  }, [])

  return <mesh ref={meshRef}>{/* ... */}</mesh>
}
```

### 2. Reuse Geometries and Materials

**Share resources across components**:
```tsx
import { useMemo } from 'react'

export function SharedResources() {
  // Create geometry once
  const sharedGeometry = useMemo(
    () => new THREE.BoxGeometry(1, 1, 1),
    []
  )

  // Create material once
  const sharedMaterial = useMemo(
    () => new THREE.MeshStandardMaterial({ color: '#6366F1' }),
    []
  )

  // Cleanup when component unmounts
  useEffect(() => {
    return () => {
      sharedGeometry.dispose()
      sharedMaterial.dispose()
    }
  }, [])

  // Use same resources for multiple meshes
  return (
    <>
      <mesh geometry={sharedGeometry} material={sharedMaterial} position={[-2, 0, 0]} />
      <mesh geometry={sharedGeometry} material={sharedMaterial} position={[0, 0, 0]} />
      <mesh geometry={sharedGeometry} material={sharedMaterial} position={[2, 0, 0]} />
    </>
  )
}
```

### 3. Texture Optimization

**Compress and resize textures**:
```tsx
import { useTexture } from '@react-three/drei'

export function OptimizedTexture() {
  // Load texture
  const texture = useTexture('/texture.jpg')

  // Optimize texture settings
  useEffect(() => {
    // Use mipmaps for better quality at distance
    texture.generateMipmaps = true
    texture.minFilter = THREE.LinearMipmapLinearFilter

    // Anisotropic filtering (improves quality at angles)
    texture.anisotropy = 4 // Max is usually 16, but 4 is enough

    // Set proper encoding
    texture.encoding = THREE.sRGBEncoding

    texture.needsUpdate = true
  }, [texture])

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <meshStandardMaterial map={texture} />
    </mesh>
  )
}
```

**Texture Size Guidelines**:
- UI icons/buttons: 128×128 to 256×256
- Cards/panels: 512×512 to 1024×1024
- Backgrounds: 1024×1024 max (or use gradients)
- Use power-of-2 dimensions (256, 512, 1024, 2048)

---

## Bundle Size Optimization

### 1. Tree-Shake Drei Imports

**Import specific components**:
```tsx
// ❌ Bad: Imports entire library (~200KB)
import { Box, Sphere, Text } from '@react-three/drei'

// ✅ Good: Tree-shakeable imports
import { Box } from '@react-three/drei/core/Box'
import { Sphere } from '@react-three/drei/core/Sphere'
import { Text } from '@react-three/drei/core/Text'
```

### 2. Code Splitting

**Lazy load 3D components**:
```tsx
import { lazy, Suspense } from 'react'

// Split heavy 3D scene into separate chunk
const HeavyScene = lazy(() => import('./components/HeavyScene'))

export default function Page() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <HeavyScene />
    </Suspense>
  )
}
```

### 3. Dynamic Imports for Conditionals

**Only load 3D on desktop**:
```tsx
import { useState, useEffect } from 'react'

export function ConditionalScene() {
  const [SceneComponent, setSceneComponent] = useState<any>(null)

  useEffect(() => {
    const isDesktop = window.innerWidth >= 1024

    if (isDesktop) {
      import('./Scene').then(module => {
        setSceneComponent(() => module.default)
      })
    }
  }, [])

  if (!SceneComponent) {
    return <StaticFallback />
  }

  return <SceneComponent />
}
```

### 4. Externalize Large Dependencies

**Use CDN for Three.js (optional)**:
```js
// next.config.js
module.exports = {
  webpack: (config) => {
    config.externals = {
      three: 'THREE'
    }
    return config
  }
}
```

```html
<!-- In _document.tsx -->
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
```

---

## Mobile Optimization

### 1. Device Detection

**Disable 3D on low-end devices**:
```tsx
import { useState, useEffect } from 'react'

export function useDeviceCapability() {
  const [capability, setCapability] = useState<'high' | 'medium' | 'low'>('high')

  useEffect(() => {
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
    const memory = (navigator as any).deviceMemory || 4
    const cores = navigator.hardwareConcurrency || 2

    if (isMobile) {
      if (memory < 4 || cores < 4) {
        setCapability('low') // No 3D
      } else {
        setCapability('medium') // Simplified 3D
      }
    } else {
      setCapability('high') // Full 3D
    }
  }, [])

  return capability
}

// Usage
export function AdaptiveScene() {
  const capability = useDeviceCapability()

  if (capability === 'low') {
    return <StaticFallback />
  }

  if (capability === 'medium') {
    return <SimplifiedScene />
  }

  return <FullScene />
}
```

### 2. Reduce Polygon Count on Mobile

```tsx
import { useState, useEffect } from 'react'

export function ResponsiveGeometry() {
  const [segments, setSegments] = useState(32)

  useEffect(() => {
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
    setSegments(isMobile ? 16 : 32) // Half the detail on mobile
  }, [])

  return (
    <mesh>
      <sphereGeometry args={[1, segments, segments]} />
      <meshStandardMaterial />
    </mesh>
  )
}
```

### 3. Disable Expensive Features on Mobile

```tsx
const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)

<Canvas
  gl={{
    antialias: !isMobile,        // Disable AA on mobile
    powerPreference: 'high-performance'
  }}
  dpr={isMobile ? [1, 1] : [1, 2]}  // No retina on mobile
  shadows={!isMobile}            // Disable shadows on mobile
>
  {/* Scene */}
</Canvas>
```

---

## Profiling & Debugging

### 1. FPS Monitor

```tsx
import { useFrame } from '@react-three/fiber'
import { useState } from 'react'

export function FPSMonitor() {
  const [fps, setFps] = useState(60)

  useFrame((state) => {
    const currentFps = Math.round(1 / state.clock.getDelta())
    setFps(currentFps)

    // Log warnings
    if (currentFps < 30) {
      console.warn('⚠️ Low FPS:', currentFps)
    }
  })

  return (
    <div style={{ position: 'fixed', top: 10, left: 10, zIndex: 1000 }}>
      FPS: {fps}
    </div>
  )
}
```

### 2. Memory Monitor

```tsx
export function MemoryMonitor() {
  const [memory, setMemory] = useState({ used: 0, limit: 0 })

  useEffect(() => {
    const interval = setInterval(() => {
      const perf = (performance as any).memory
      if (perf) {
        setMemory({
          used: Math.round(perf.usedJSHeapSize / 1048576), // MB
          limit: Math.round(perf.jsHeapSizeLimit / 1048576)
        })
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{ position: 'fixed', top: 30, left: 10, zIndex: 1000 }}>
      Memory: {memory.used}MB / {memory.limit}MB
    </div>
  )
}
```

### 3. Three.js Stats

**Install r3f-perf**:
```bash
npm install r3f-perf
```

**Usage**:
```tsx
import { Perf } from 'r3f-perf'

<Canvas>
  <Perf position="top-left" />
  {/* Scene */}
</Canvas>
```

**Shows**:
- FPS (realtime)
- GPU milliseconds
- Memory usage
- Draw calls
- Triangles rendered

### 4. Chrome DevTools

**Enable 3D rendering stats**:
1. Open Chrome DevTools (F12)
2. Press `Cmd/Ctrl + Shift + P`
3. Type "Show Rendering"
4. Enable "FPS Meter"
5. Enable "Paint Flashing"

**WebGL Info**:
```tsx
import { useThree } from '@react-three/fiber'

export function WebGLInfo() {
  const { gl } = useThree()

  useEffect(() => {
    console.log('WebGL Renderer:', gl.info)
    console.log('Draw Calls:', gl.info.render.calls)
    console.log('Triangles:', gl.info.render.triangles)
    console.log('Geometries:', gl.info.memory.geometries)
    console.log('Textures:', gl.info.memory.textures)
  }, [gl])

  return null
}
```

---

## Performance Checklist

### Before Launch

- [ ] Target 60fps on desktop, 30fps on mobile
- [ ] Test on low-end devices (< 4GB RAM)
- [ ] Bundle size < 200KB gzipped
- [ ] No memory leaks (heap stable after 5min)
- [ ] Dispose all geometries/materials on unmount
- [ ] Use instancing for repeated objects (> 10)
- [ ] Lazy load 3D components
- [ ] Provide static fallback for no-WebGL
- [ ] Test with reduced motion preference
- [ ] Profile with r3f-perf in dev mode
- [ ] Check draw calls (< 100 ideal)
- [ ] Optimize textures (power-of-2, compressed)
- [ ] Disable shadows on mobile
- [ ] Use `frameloop="demand"` for static scenes
- [ ] Test on Safari iOS (strictest WebGL limits)

---

## Common Performance Pitfalls

### ❌ Avoid:
- Creating new objects in `useFrame` (use refs)
- Not disposing resources on unmount
- Using default antialias (expensive)
- Rendering 100+ individual meshes (use instancing)
- Large textures (> 2048×2048 for UI)
- Complex shaders for simple effects
- `shadowMap.enabled` on mobile
- Ignoring `frameloop` optimization
- Loading entire Drei library
- Re-creating geometries on every render

### ✅ Do:
- Reuse geometries and materials
- Use `useMemo` for static data
- Implement LOD for distant objects
- Use instancing for repetition
- Lazy load heavy components
- Monitor FPS in development
- Test on real devices
- Profile with Chrome DevTools
- Use `frameloop="demand"` when possible
- Optimize textures (compress, resize)

---

**Target**: < 200KB bundle, 60fps desktop, 30fps mobile, < 100MB memory
