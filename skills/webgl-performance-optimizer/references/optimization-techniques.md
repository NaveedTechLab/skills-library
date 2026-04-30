# Advanced WebGL Optimization Techniques

This guide covers advanced optimization strategies for Three.js and React Three Fiber applications.

## Table of Contents

1. [Batching and Instancing](#batching-and-instancing)
2. [Geometry Optimization](#geometry-optimization)
3. [Texture Optimization](#texture-optimization)
4. [Shader Optimization](#shader-optimization)
5. [Memory Management](#memory-management)
6. [Render Loop Optimization](#render-loop-optimization)
7. [Post-Processing Optimization](#post-processing-optimization)

---

## Batching and Instancing

### Instanced Mesh for Massive Object Counts

Use `InstancedMesh` for rendering thousands of identical objects with different transforms.

```tsx
import { useRef, useEffect } from 'react'
import { InstancedMesh, Object3D, Matrix4 } from 'three'

const ParticleField = ({ count = 10000 }) => {
  const meshRef = useRef<InstancedMesh>(null)
  const tempObject = new Object3D()

  useEffect(() => {
    if (!meshRef.current) return

    // Set initial positions
    for (let i = 0; i < count; i++) {
      tempObject.position.set(
        Math.random() * 100 - 50,
        Math.random() * 100 - 50,
        Math.random() * 100 - 50
      )
      tempObject.rotation.set(
        Math.random() * Math.PI,
        Math.random() * Math.PI,
        0
      )
      tempObject.scale.setScalar(Math.random() * 0.5 + 0.5)
      tempObject.updateMatrix()
      meshRef.current.setMatrixAt(i, tempObject.matrix)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
  }, [count])

  useFrame(() => {
    if (!meshRef.current) return

    // Animate instances
    for (let i = 0; i < count; i++) {
      meshRef.current.getMatrixAt(i, tempObject.matrix)
      tempObject.matrix.decompose(tempObject.position, tempObject.quaternion, tempObject.scale)

      tempObject.rotation.y += 0.01
      tempObject.updateMatrix()

      meshRef.current.setMatrixAt(i, tempObject.matrix)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
  })

  return (
    <instancedMesh ref={meshRef} args={[null, null, count]}>
      <boxGeometry args={[0.1, 0.1, 0.1]} />
      <meshStandardMaterial color="cyan" />
    </instancedMesh>
  )
}
```

### Geometry Merging for Static Objects

Merge multiple static geometries into a single mesh to reduce draw calls.

```tsx
import { useMemo } from 'react'
import { BufferGeometry, BoxGeometry, Vector3 } from 'three'
import { mergeBufferGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils'

const MergedCityBuildings = ({ buildingData }) => {
  const mergedGeometry = useMemo(() => {
    const geometries: BufferGeometry[] = []

    buildingData.forEach(building => {
      const geo = new BoxGeometry(
        building.width,
        building.height,
        building.depth
      )
      geo.translate(building.x, building.y, building.z)
      geometries.push(geo)
    })

    const merged = mergeBufferGeometries(geometries)
    // Dispose individual geometries to free memory
    geometries.forEach(geo => geo.dispose())

    return merged
  }, [buildingData])

  useEffect(() => {
    return () => mergedGeometry.dispose()
  }, [mergedGeometry])

  return (
    <mesh geometry={mergedGeometry}>
      <meshLambertMaterial color="#cccccc" />
    </mesh>
  )
}
```

### Texture Atlasing

Combine multiple textures into a single atlas to reduce texture binds.

```tsx
// Create texture atlas (do this in your build process)
// Combine multiple 512x512 textures into 2048x2048 atlas

const AtlasSprite = ({ atlasTexture, spriteIndex, totalSprites = 16 }) => {
  const spritesPerRow = Math.sqrt(totalSprites)
  const uvScale = 1 / spritesPerRow

  const row = Math.floor(spriteIndex / spritesPerRow)
  const col = spriteIndex % spritesPerRow

  const uvOffset = [col * uvScale, row * uvScale]
  const uvRepeat = [uvScale, uvScale]

  return (
    <mesh>
      <planeGeometry args={[1, 1]} />
      <meshBasicMaterial
        map={atlasTexture}
        map-offset={uvOffset}
        map-repeat={uvRepeat}
      />
    </mesh>
  )
}
```

---

## Geometry Optimization

### Level of Detail (LOD) System

Automatically switch between high and low poly models based on camera distance.

```tsx
import { useRef, useEffect } from 'react'
import { LOD, Mesh, SphereGeometry, MeshStandardMaterial } from 'three'
import { useFrame } from '@react-three/fiber'

const LODObject = ({ position }) => {
  const lodRef = useRef<LOD>()
  const material = new MeshStandardMaterial({ color: 'orange' })

  useEffect(() => {
    const lod = new LOD()

    // Level 0: High detail (0-15 units from camera)
    const highGeo = new SphereGeometry(1, 32, 32)
    const highMesh = new Mesh(highGeo, material)
    lod.addLevel(highMesh, 0)

    // Level 1: Medium detail (15-30 units)
    const medGeo = new SphereGeometry(1, 16, 16)
    const medMesh = new Mesh(medGeo, material)
    lod.addLevel(medMesh, 15)

    // Level 2: Low detail (30-50 units)
    const lowGeo = new SphereGeometry(1, 8, 8)
    const lowMesh = new Mesh(lowGeo, material)
    lod.addLevel(lowMesh, 30)

    // Level 3: Billboard (50+ units) - just a sprite
    const billboardGeo = new PlaneGeometry(2, 2)
    const billboardMesh = new Mesh(billboardGeo, material)
    lod.addLevel(billboardMesh, 50)

    lodRef.current = lod

    return () => {
      highGeo.dispose()
      medGeo.dispose()
      lowGeo.dispose()
      billboardGeo.dispose()
      material.dispose()
    }
  }, [])

  useFrame(({ camera }) => {
    lodRef.current?.update(camera)
  })

  return <primitive object={lodRef.current} position={position} />
}
```

### BufferGeometry Optimization

Remove unnecessary vertex attributes to reduce memory and bandwidth.

```tsx
import { BufferGeometry, BufferAttribute } from 'three'

const OptimizedGeometry = () => {
  const geometry = useMemo(() => {
    const geo = new BufferGeometry()

    // Only include necessary attributes
    const vertices = new Float32Array([
      -1, -1, 0,
       1, -1, 0,
       1,  1, 0,
      -1,  1, 0,
    ])

    const indices = new Uint16Array([
      0, 1, 2,
      0, 2, 3,
    ])

    // Use Uint16Array for indices instead of Uint32Array when possible
    geo.setAttribute('position', new BufferAttribute(vertices, 3))
    geo.setIndex(new BufferAttribute(indices, 1))

    // Don't compute normals/UVs if you don't need them
    // geo.computeVertexNormals() // Skip if using flat shading

    return geo
  }, [])

  return (
    <mesh geometry={geometry}>
      <meshBasicMaterial color="blue" />
    </mesh>
  )
}
```

### Indexed Geometry

Use indexed geometry to reuse vertices and reduce memory.

```tsx
// Non-indexed: 6 vertices per quad, 36 vertices per cube
const nonIndexedCube = new BoxGeometry(1, 1, 1)
console.log(nonIndexedCube.attributes.position.count) // 36 vertices

// Indexed: 8 vertices per cube
const indexedCube = new BoxGeometry(1, 1, 1)
indexedCube.setIndex([...]) // Explicitly set indices
console.log(indexedCube.attributes.position.count) // 8 vertices
```

---

## Texture Optimization

### Texture Compression

Use compressed texture formats (KTX2, Basis Universal) for massive size reduction.

```tsx
import { KTX2Loader } from 'three/examples/jsm/loaders/KTX2Loader'
import { useLoader } from '@react-three/fiber'

const CompressedTextureMaterial = () => {
  const texture = useLoader(KTX2Loader, '/textures/diffuse.ktx2')

  return <meshStandardMaterial map={texture} />
}

// Setup KTX2 Loader (in your app setup)
const ktx2Loader = new KTX2Loader()
ktx2Loader.setTranscoderPath('/basis/')
ktx2Loader.detectSupport(renderer)
```

### Texture Mipmaps

Generate and use mipmaps for better performance when textures are viewed at distance.

```tsx
import { useTexture } from '@react-three/drei'

const MipmappedTexture = () => {
  const texture = useTexture('/texture.jpg')

  // Enable mipmaps
  texture.generateMipmaps = true
  texture.minFilter = THREE.LinearMipmapLinearFilter
  texture.magFilter = THREE.LinearFilter

  // Limit anisotropic filtering
  texture.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy())

  return <meshStandardMaterial map={texture} />
}
```

### Lazy Texture Loading

Load textures on demand rather than upfront.

```tsx
const LazyTextureLoader = ({ texturePath, shouldLoad }) => {
  const [texture, setTexture] = useState(null)

  useEffect(() => {
    if (!shouldLoad) return

    const loader = new THREE.TextureLoader()
    loader.load(texturePath, (loadedTexture) => {
      setTexture(loadedTexture)
    })

    return () => {
      texture?.dispose()
    }
  }, [shouldLoad, texturePath])

  return texture ? (
    <meshBasicMaterial map={texture} />
  ) : (
    <meshBasicMaterial color="#cccccc" />
  )
}
```

### Texture Resizing Based on Screen Size

Dynamically load appropriate texture resolution.

```tsx
const ResponsiveTexture = () => {
  const textureSize = useMemo(() => {
    const width = window.innerWidth
    if (width > 2560) return '4k'
    if (width > 1920) return '2k'
    if (width > 1280) return '1k'
    return '512'
  }, [])

  const texture = useTexture(`/textures/diffuse-${textureSize}.jpg`)

  return <meshStandardMaterial map={texture} />
}
```

---

## Shader Optimization

### Vertex Shader Calculations

Move calculations from fragment to vertex shader when possible.

```glsl
// BAD: Expensive calculation in fragment shader (runs per pixel)
// Fragment Shader
varying vec2 vUv;

void main() {
  // This runs for EVERY pixel
  float noise = sin(vUv.x * 50.0) * cos(vUv.y * 50.0);
  gl_FragColor = vec4(vec3(noise), 1.0);
}

// GOOD: Calculate in vertex shader (runs per vertex)
// Vertex Shader
attribute vec2 uv;
varying float vNoise;

void main() {
  // This runs once per vertex, then interpolated
  vNoise = sin(uv.x * 50.0) * cos(uv.y * 50.0);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}

// Fragment Shader
varying float vNoise;

void main() {
  gl_FragColor = vec4(vec3(vNoise), 1.0);
}
```

### Shader Precision

Use appropriate precision levels for mobile.

```glsl
// Use lowp for colors
varying lowp vec4 vColor;

// Use mediump for most calculations
varying mediump vec2 vUv;
varying mediump vec3 vNormal;

// Use highp only when absolutely necessary
varying highp vec3 vPosition;

void main() {
  // Mobile GPUs are much faster with mediump
  mediump float value = sin(vUv.x * 3.14159);
  lowp vec3 color = vec3(value);
  gl_FragColor = vec4(color, 1.0);
}
```

### Avoid Branching in Shaders

Minimize conditional statements in shaders.

```glsl
// BAD: Branching in shader
void main() {
  vec3 color;
  if (vUv.x > 0.5) {
    color = vec3(1.0, 0.0, 0.0);
  } else {
    color = vec3(0.0, 0.0, 1.0);
  }
  gl_FragColor = vec4(color, 1.0);
}

// GOOD: Use mix/step instead
void main() {
  vec3 red = vec3(1.0, 0.0, 0.0);
  vec3 blue = vec3(0.0, 0.0, 1.0);
  float mask = step(0.5, vUv.x);
  vec3 color = mix(blue, red, mask);
  gl_FragColor = vec4(color, 1.0);
}
```

### Shader Caching

Reuse shader materials instead of creating new ones.

```tsx
// BAD: Creates new material every render
{objects.map(obj => (
  <mesh key={obj.id}>
    <sphereGeometry />
    <shaderMaterial {...shaderProps} />
  </mesh>
))}

// GOOD: Reuse shared material
const SharedMaterial = () => {
  const sharedMaterial = useMemo(() => new ShaderMaterial({...}), [])

  useEffect(() => {
    return () => sharedMaterial.dispose()
  }, [])

  return objects.map(obj => (
    <mesh key={obj.id}>
      <sphereGeometry />
      <primitive object={sharedMaterial} attach="material" />
    </mesh>
  ))
}
```

---

## Memory Management

### Automatic Disposal

Create a hook to automatically dispose Three.js objects.

```tsx
function useDisposable<T extends { dispose: () => void }>(
  createFn: () => T,
  deps: any[] = []
): T {
  const ref = useRef<T>()

  useEffect(() => {
    ref.current = createFn()

    return () => {
      ref.current?.dispose()
    }
  }, deps)

  return ref.current!
}

// Usage
const MyMesh = () => {
  const geometry = useDisposable(() => new BoxGeometry(1, 1, 1))
  const material = useDisposable(() => new MeshStandardMaterial({ color: 'red' }))

  return (
    <mesh geometry={geometry} material={material} />
  )
}
```

### Texture Pool

Reuse textures across objects.

```tsx
const textureCache = new Map<string, THREE.Texture>()

export function useSharedTexture(path: string) {
  const [texture, setTexture] = useState<THREE.Texture | null>(null)

  useEffect(() => {
    // Check cache first
    if (textureCache.has(path)) {
      setTexture(textureCache.get(path)!)
      return
    }

    // Load and cache
    const loader = new THREE.TextureLoader()
    loader.load(path, (tex) => {
      textureCache.set(path, tex)
      setTexture(tex)
    })

    // Don't dispose cached textures automatically
  }, [path])

  return texture
}

// Clear cache manually when needed
export function clearTextureCache() {
  textureCache.forEach(tex => tex.dispose())
  textureCache.clear()
}
```

### Memory Leak Detection

Monitor memory usage and detect leaks.

```tsx
const MemoryMonitor = () => {
  useEffect(() => {
    const checkMemory = () => {
      if (performance.memory) {
        const { usedJSHeapSize, jsHeapSizeLimit } = performance.memory
        const usagePercent = (usedJSHeapSize / jsHeapSizeLimit) * 100

        console.log(`Memory: ${Math.round(usagePercent)}%`)

        if (usagePercent > 90) {
          console.warn('High memory usage detected!')
        }
      }
    }

    const interval = setInterval(checkMemory, 5000)
    return () => clearInterval(interval)
  }, [])

  return null
}
```

---

## Render Loop Optimization

### Conditional Rendering

Only render when scene changes.

```tsx
const StaticScene = () => {
  const [needsUpdate, setNeedsUpdate] = useState(false)

  return (
    <Canvas frameloop={needsUpdate ? 'always' : 'demand'}>
      <OrbitControls onChange={() => setNeedsUpdate(true)} />
      {/* Static content */}
    </Canvas>
  )
}
```

### Throttled Updates

Limit update frequency for expensive calculations.

```tsx
const ThrottledAnimation = () => {
  const lastUpdate = useRef(0)
  const updateInterval = 100 // ms

  useFrame((state, delta) => {
    const now = state.clock.elapsedTime * 1000

    if (now - lastUpdate.current < updateInterval) {
      return // Skip this frame
    }

    lastUpdate.current = now
    // Expensive update logic here
  })

  return <mesh>{/* ... */}</mesh>
}
```

### Separate Update and Render Loops

Decouple logic updates from render loop.

```tsx
const SeparatedLoops = () => {
  const dataRef = useRef({ positions: [] })

  // Logic update (30 fps)
  useEffect(() => {
    const interval = setInterval(() => {
      // Update game logic
      dataRef.current.positions = calculateNewPositions()
    }, 1000 / 30)

    return () => clearInterval(interval)
  }, [])

  // Render loop (60 fps or demand)
  useFrame(() => {
    // Just render current state
    updateMeshPositions(dataRef.current.positions)
  })

  return <group>{/* meshes */}</group>
}
```

---

## Post-Processing Optimization

### Selective Post-Processing

Only apply effects to specific objects.

```tsx
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing'

const SelectiveEffects = () => {
  return (
    <>
      <EffectComposer>
        {/* Only bloom bright objects */}
        <Bloom
          luminanceThreshold={0.9}
          luminanceSmoothing={0.9}
          intensity={1.5}
        />

        {/* Vignette is cheap, always apply */}
        <Vignette />
      </EffectComposer>
    </>
  )
}
```

### Reduce Effect Resolution

Run post-processing at lower resolution.

```tsx
<EffectComposer
  multisampling={0}           // Disable MSAA
  renderPriority={1}
  resolutionScale={0.5}       // Run at half resolution
>
  <Bloom />
</EffectComposer>
```

### FXAA Instead of MSAA

Use FXAA post-process instead of multi-sample anti-aliasing.

```tsx
import { EffectComposer, FXAA } from '@react-three/postprocessing'

// In Canvas setup
<Canvas gl={{ antialias: false }}> {/* Disable MSAA */}
  <EffectComposer>
    <FXAA />  {/* Cheaper post-process AA */}
  </EffectComposer>
</Canvas>
```

---

## Performance Profiling

### Built-in Stats

```tsx
import { Stats } from '@react-three/drei'

<Canvas>
  <Stats showPanel={0} /> {/* 0: fps, 1: ms, 2: mb */}
</Canvas>
```

### Custom Performance Tracker

```tsx
const PerformanceTracker = () => {
  const metrics = useRef({ fps: 60, drawCalls: 0, triangles: 0 })

  useFrame((state) => {
    const { gl } = state
    const info = gl.info

    metrics.current = {
      fps: Math.round(1 / state.clock.getDelta()),
      drawCalls: info.render.calls,
      triangles: info.render.triangles,
    }
  })

  return (
    <Html position={[0, 5, 0]}>
      <div style={{ background: 'rgba(0,0,0,0.8)', padding: '10px', color: 'white' }}>
        <div>FPS: {metrics.current.fps}</div>
        <div>Draw Calls: {metrics.current.drawCalls}</div>
        <div>Triangles: {metrics.current.triangles}</div>
      </div>
    </Html>
  )
}
```

---

## Summary

Key takeaways for WebGL optimization:

1. **Batching**: Use instancing and geometry merging to reduce draw calls
2. **LOD**: Implement level of detail systems for complex scenes
3. **Textures**: Compress, atlas, and size appropriately
4. **Shaders**: Move calculations to vertex shader, use appropriate precision
5. **Memory**: Always dispose of Three.js objects, reuse when possible
6. **Render Loop**: Use frameloop="demand" for static scenes
7. **Post-Processing**: Apply selectively and at lower resolution

Always profile before optimizing, and maintain your target frame rates (60fps desktop, 30fps mobile).
