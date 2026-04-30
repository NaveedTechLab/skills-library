# WebGL Performance Optimizer

---
name: webgl-performance-optimizer
description: Optimize Three.js UI performance, reduce GPU load, suggest fallback UI strategies, and maintain 60fps experience
version: 1.0.0
author: Claude Code Skills
created: 2026-01-03
---

## Core Philosophy

WebGL performance optimization is about **intelligent resource management** - knowing when to render, what to render, and how to render efficiently. Every frame has a budget of ~16.67ms to maintain 60fps. Your job is to ensure the GPU never exceeds this budget through smart geometry, texture, and draw call management.

**Key Principles:**
- 🎯 **Profile First**: Measure before optimizing - identify actual bottlenecks
- 🔄 **Progressive Degradation**: Gracefully reduce quality when performance drops
- 📊 **Frame Budget**: Target 60fps desktop (16.67ms/frame), 30fps mobile (33.33ms/frame)
- 🎨 **Visual Fidelity Trade-offs**: Balance beauty with performance
- 🛡️ **Fallback Strategies**: Always have non-WebGL alternatives ready

## Technology Stack

- **Three.js**: Core 3D rendering library
- **React Three Fiber** (@react-three/fiber): React renderer for Three.js
- **React Three Drei** (@react-three/drei): Useful helpers and abstractions
- **Stats.js**: Real-time performance monitoring
- **Chrome DevTools**: GPU profiling and frame analysis
- **Spector.js**: WebGL debugging and call inspection

## When to Use This Skill

Use webgl-performance-optimizer when:
- Three.js scenes drop below 60fps on desktop or 30fps on mobile
- GPU usage is high (>80%) during normal operation
- Complex 3D UI elements cause jank or stuttering
- Users on lower-end devices report performance issues
- Draw calls exceed 500-1000 per frame
- Memory usage grows unbounded over time
- You need to balance visual quality with performance

## Optimization Workflow

### 1. Identify Bottlenecks

```tsx
// Add Stats.js for real-time monitoring
import Stats from 'three/examples/jsm/libs/stats.module'

const StatsMonitor = () => {
  const statsRef = useRef<Stats>()

  useEffect(() => {
    const stats = new Stats()
    stats.showPanel(0) // 0: fps, 1: ms, 2: mb
    stats.dom.style.position = 'absolute'
    stats.dom.style.top = '0'
    stats.dom.style.left = '0'
    document.body.appendChild(stats.dom)
    statsRef.current = stats

    return () => document.body.removeChild(stats.dom)
  }, [])

  useFrame(() => {
    statsRef.current?.update()
  })

  return null
}

// Usage in Canvas
<Canvas>
  <StatsMonitor />
  {/* Your scene */}
</Canvas>
```

**Chrome DevTools GPU Profiling:**
- Open DevTools → Performance → Enable "Screenshots" and "Memory"
- Record a session while interacting with 3D UI
- Check for long frames (>16.67ms) in the flame chart
- Identify draw calls, shader compilation, texture uploads

### 2. Reduce Draw Calls

**Problem**: Each mesh = 1 draw call. Too many objects = GPU bottleneck.

**Solution 1: Instanced Rendering**

```tsx
// Bad: 1000 draw calls for 1000 spheres
{particles.map((pos, i) => (
  <mesh key={i} position={pos}>
    <sphereGeometry args={[0.1, 16, 16]} />
    <meshStandardMaterial color="cyan" />
  </mesh>
))}

// Good: 1 draw call for 1000 spheres using instancing
import { Instances, Instance } from '@react-three/drei'

<Instances limit={1000}>
  <sphereGeometry args={[0.1, 16, 16]} />
  <meshStandardMaterial color="cyan" />

  {particles.map((pos, i) => (
    <Instance key={i} position={pos} />
  ))}
</Instances>
```

**Solution 2: Geometry Merging**

```tsx
import { mergeBufferGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils'

// Merge static geometries into single mesh
const MergedStaticObjects = () => {
  const mergedGeometry = useMemo(() => {
    const geometries = staticObjects.map(obj => {
      const geo = new BoxGeometry(obj.size, obj.size, obj.size)
      geo.translate(obj.position.x, obj.position.y, obj.position.z)
      return geo
    })
    return mergeBufferGeometries(geometries)
  }, [staticObjects])

  return (
    <mesh geometry={mergedGeometry}>
      <meshStandardMaterial />
    </mesh>
  )
}
```

### 3. Optimize Geometry

**Reduce Polygon Count:**

```tsx
// Bad: High poly sphere (2400 triangles)
<sphereGeometry args={[1, 64, 64]} />

// Good: Low poly sphere (300 triangles) - visually similar with proper lighting
<sphereGeometry args={[1, 16, 16]} />

// Better: Adaptive detail based on screen size
const DetailedSphere = ({ radius, screenSize }) => {
  const segments = screenSize > 1920 ? 32 : screenSize > 1280 ? 24 : 16

  return <sphereGeometry args={[radius, segments, segments]} />
}
```

**Use LOD (Level of Detail):**

```tsx
import { LOD } from 'three'

const AdaptiveMesh = ({ position }) => {
  const lodRef = useRef<LOD>()

  useEffect(() => {
    const lod = new LOD()

    // High detail (close)
    const highGeo = new SphereGeometry(1, 32, 32)
    const highMesh = new Mesh(highGeo, material)
    lod.addLevel(highMesh, 0)

    // Medium detail
    const medGeo = new SphereGeometry(1, 16, 16)
    const medMesh = new Mesh(medGeo, material)
    lod.addLevel(medMesh, 10)

    // Low detail (far)
    const lowGeo = new SphereGeometry(1, 8, 8)
    const lowMesh = new Mesh(lowGeo, material)
    lod.addLevel(lowMesh, 20)

    lodRef.current = lod
  }, [])

  return <primitive object={lodRef.current} position={position} />
}
```

### 4. Optimize Textures

**Texture Compression and Sizing:**

```tsx
import { useTexture } from '@react-three/drei'

// Bad: 4K uncompressed texture (64MB memory)
const texture = useTexture('/texture-4k.png')

// Good: Compressed, appropriately sized texture (4MB memory)
const OptimizedTexture = () => {
  const texture = useTexture('/texture-1k-compressed.jpg')

  // Enable mipmaps for better performance at distance
  texture.generateMipmaps = true
  texture.minFilter = THREE.LinearMipmapLinearFilter
  texture.magFilter = THREE.LinearFilter

  // Anisotropic filtering (2-4 is usually enough)
  texture.anisotropy = 2

  return <meshStandardMaterial map={texture} />
}
```

**Texture Atlasing:**

```tsx
// Bad: 10 separate textures = 10 texture binds per frame
materials.map(mat => <meshBasicMaterial map={mat.texture} />)

// Good: 1 texture atlas = 1 texture bind
// Combine multiple textures into single atlas, use UV offsets
const AtlasMaterial = ({ uvOffset, uvScale }) => {
  const atlas = useTexture('/texture-atlas.jpg')

  return (
    <meshBasicMaterial
      map={atlas}
      map-offset={uvOffset}
      map-repeat={uvScale}
    />
  )
}
```

### 5. Optimize Shaders

**Avoid Expensive Operations:**

```glsl
// Bad: Expensive operations in fragment shader
varying vec3 vNormal;
varying vec3 vPosition;

void main() {
  // Normalize in fragment shader (runs per-pixel)
  vec3 normal = normalize(vNormal);

  // Expensive calculations per pixel
  float pattern = sin(vPosition.x * 100.0) * cos(vPosition.y * 100.0);

  gl_FragColor = vec4(normal * pattern, 1.0);
}

// Good: Move calculations to vertex shader (runs per-vertex)
// Vertex Shader
attribute vec3 position;
attribute vec3 normal;
varying vec3 vNormal;
varying float vPattern;

void main() {
  vNormal = normalize(normalMatrix * normal); // Normalize once per vertex
  vPattern = sin(position.x * 100.0) * cos(position.y * 100.0);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}

// Fragment Shader
varying vec3 vNormal;
varying float vPattern;

void main() {
  gl_FragColor = vec4(vNormal * vPattern, 1.0);
}
```

**Shader Precision:**

```glsl
// Use appropriate precision for mobile
precision mediump float; // Good for mobile (saves GPU power)
precision highp float;   // Use only when necessary

// Mix precisions for optimal performance
varying lowp vec4 vColor;      // Color doesn't need high precision
varying mediump vec2 vUv;       // UVs need medium precision
varying highp vec3 vPosition;   // Positions may need high precision
```

### 6. Frustum Culling & Occlusion

```tsx
import { useThree } from '@react-three/fiber'

const FrustumCulledObject = ({ position, children }) => {
  const { camera } = useThree()
  const meshRef = useRef()
  const [visible, setVisible] = useState(true)

  useFrame(() => {
    if (!meshRef.current) return

    // Check if object is in camera frustum
    const frustum = new THREE.Frustum()
    const matrix = new THREE.Matrix4().multiplyMatrices(
      camera.projectionMatrix,
      camera.matrixWorldInverse
    )
    frustum.setFromProjectionMatrix(matrix)

    const isVisible = frustum.intersectsObject(meshRef.current)
    setVisible(isVisible)
  })

  return visible ? (
    <group ref={meshRef} position={position}>
      {children}
    </group>
  ) : null
}
```

### 7. Conditional Rendering

```tsx
const PerformanceAdaptiveScene = () => {
  const [quality, setQuality] = useState<'high' | 'medium' | 'low'>('high')
  const fpsRef = useRef(60)

  useFrame((state, delta) => {
    // Monitor FPS
    const currentFps = 1 / delta
    fpsRef.current = fpsRef.current * 0.9 + currentFps * 0.1 // Smooth average

    // Adaptive quality
    if (fpsRef.current < 30 && quality !== 'low') {
      setQuality('low')
    } else if (fpsRef.current < 50 && quality === 'high') {
      setQuality('medium')
    } else if (fpsRef.current > 55 && quality !== 'high') {
      setQuality('high')
    }
  })

  return (
    <>
      {quality === 'high' && <HighQualityEffects />}
      {quality === 'medium' && <MediumQualityEffects />}
      {quality === 'low' && <MinimalEffects />}

      <Instances limit={quality === 'high' ? 1000 : quality === 'medium' ? 500 : 200}>
        {/* Adaptive particle count */}
      </Instances>
    </>
  )
}
```

### 8. Memory Management

```tsx
// Dispose of geometries and materials when unmounting
const ManagedMesh = () => {
  const meshRef = useRef<THREE.Mesh>()

  useEffect(() => {
    return () => {
      // Clean up on unmount
      if (meshRef.current) {
        meshRef.current.geometry.dispose()
        if (Array.isArray(meshRef.current.material)) {
          meshRef.current.material.forEach(mat => mat.dispose())
        } else {
          meshRef.current.material.dispose()
        }
      }
    }
  }, [])

  return <mesh ref={meshRef}>{/* ... */}</mesh>
}

// Dispose textures
const textureRef = useRef<THREE.Texture>()
useEffect(() => {
  return () => {
    textureRef.current?.dispose()
  }
}, [])
```

## Fallback Strategies

### 1. WebGL Detection & Fallback

```tsx
const WebGLDetector = () => {
  const [webglAvailable, setWebglAvailable] = useState(true)

  useEffect(() => {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
    setWebglAvailable(!!gl)
  }, [])

  if (!webglAvailable) {
    return (
      <div className="fallback-ui">
        <h2>3D View Unavailable</h2>
        <p>Your browser doesn't support WebGL. Here's a 2D alternative:</p>
        <StaticImageFallback />
      </div>
    )
  }

  return <Canvas>{/* 3D Scene */}</Canvas>
}
```

### 2. Progressive Enhancement

```tsx
const AdaptiveVisualization = () => {
  const [mode, setMode] = useState<'3d' | '2d' | 'minimal'>('3d')
  const performanceRef = useRef({ fps: 60, memory: 0 })

  // Monitor performance and switch modes
  useEffect(() => {
    const checkPerformance = () => {
      const { fps, memory } = performanceRef.current

      if (fps < 20 || memory > 500) {
        setMode('minimal')
      } else if (fps < 40 || memory > 300) {
        setMode('2d')
      }
    }

    const interval = setInterval(checkPerformance, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <>
      {mode === '3d' && <Full3DScene />}
      {mode === '2d' && <Simplified2DView />}
      {mode === 'minimal' && <StaticFallback />}
    </>
  )
}
```

### 3. User-Controlled Quality

```tsx
const QualitySettings = () => {
  const [userQuality, setUserQuality] = useState<'auto' | 'high' | 'low'>('auto')

  return (
    <div className="quality-controls">
      <select value={userQuality} onChange={e => setUserQuality(e.target.value)}>
        <option value="auto">Auto</option>
        <option value="high">High Quality</option>
        <option value="low">Performance Mode</option>
      </select>

      <Canvas dpr={userQuality === 'low' ? [1, 1] : [1, 2]}>
        <PerformanceOptimizedScene quality={userQuality} />
      </Canvas>
    </div>
  )
}
```

## Performance Targets

### Desktop (60fps = 16.67ms/frame)
- **Draw Calls**: < 500 per frame
- **Triangles**: < 500k per frame
- **Texture Memory**: < 500MB total
- **Shader Complexity**: < 100 instructions per shader
- **Particles**: < 10k active particles

### Mobile (30fps = 33.33ms/frame)
- **Draw Calls**: < 200 per frame
- **Triangles**: < 100k per frame
- **Texture Memory**: < 200MB total
- **Shader Complexity**: < 50 instructions per shader
- **Particles**: < 2k active particles

## Canvas Setup for Performance

```tsx
<Canvas
  // Limit pixel ratio for performance
  dpr={[1, 2]} // Max 2x pixel ratio

  // Performance-focused GL settings
  gl={{
    antialias: false,              // Disable AA for performance (use FXAA in post if needed)
    alpha: false,                  // Disable transparency if not needed
    stencil: false,                // Disable stencil buffer if not needed
    depth: true,                   // Keep depth buffer for proper rendering
    powerPreference: 'high-performance', // Request discrete GPU
    failIfMajorPerformanceCaveat: true,  // Fail on software rendering
  }}

  // Frame loop control
  frameloop="demand" // Only render when needed (for static scenes)
  // frameloop="always" // Use for animated scenes

  // Camera settings
  camera={{
    fov: 50, // Narrower FOV = less to render
    near: 0.1,
    far: 100, // Tighter far plane = less depth buffer precision needed
  }}
>
  {/* Your scene */}
</Canvas>
```

## Quick Wins Checklist

- [ ] Enable frustum culling (enabled by default in Three.js)
- [ ] Use instancing for repeated objects
- [ ] Reduce geometry segments (16 instead of 64 for spheres)
- [ ] Compress textures and use appropriate sizes (1k-2k max for UI elements)
- [ ] Set `dpr={[1, 2]}` to limit pixel ratio
- [ ] Disable antialiasing in Canvas GL settings
- [ ] Use `frameloop="demand"` for static scenes
- [ ] Implement LOD for complex objects
- [ ] Dispose geometries/materials on unmount
- [ ] Add Stats.js to monitor FPS in development
- [ ] Test on mid-range mobile devices
- [ ] Provide fallback UI for WebGL unsupported browsers

## Resources

See `/references` directory for:
- `optimization-techniques.md` - Advanced optimization methods
- `fallback-strategies.md` - Progressive enhancement approaches
- `performance-monitoring.md` - Profiling and debugging tools

## Remember

> "Premature optimization is the root of all evil, but so is premature de-optimization." - Profile first, optimize based on data, not assumptions. Always maintain 60fps on desktop and 30fps on mobile as your baseline targets.
