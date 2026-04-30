# Performance Monitoring and Profiling for WebGL

Comprehensive guide to measuring, analyzing, and debugging Three.js/WebGL performance issues.

## Table of Contents

1. [Real-Time FPS Monitoring](#real-time-fps-monitoring)
2. [Chrome DevTools Profiling](#chrome-devtools-profiling)
3. [WebGL Call Inspection](#webgl-call-inspection)
4. [Memory Profiling](#memory-profiling)
5. [Custom Performance Metrics](#custom-performance-metrics)
6. [Automated Performance Testing](#automated-performance-testing)

---

## Real-Time FPS Monitoring

### Stats.js Integration

```tsx
import Stats from 'three/examples/jsm/libs/stats.module'
import { useEffect, useRef } from 'react'
import { useFrame } from '@react-three/fiber'

const StatsMonitor = ({ mode = 0 }) => {
  const statsRef = useRef<Stats>()

  useEffect(() => {
    const stats = new Stats()
    stats.showPanel(mode) // 0: fps, 1: ms, 2: mb, 3+: custom
    stats.dom.style.position = 'absolute'
    stats.dom.style.top = '0'
    stats.dom.style.left = '0'
    stats.dom.style.zIndex = '9999'
    document.body.appendChild(stats.dom)
    statsRef.current = stats

    return () => {
      if (stats.dom.parentNode) {
        document.body.removeChild(stats.dom)
      }
    }
  }, [mode])

  useFrame(() => {
    statsRef.current?.update()
  })

  return null
}

// Usage
<Canvas>
  <StatsMonitor mode={0} />
  <Scene />
</Canvas>
```

### Multi-Panel Stats

```tsx
const MultiStats = () => {
  const statsRefs = useRef<Stats[]>([])

  useEffect(() => {
    const panels = [
      { panel: 0, label: 'FPS', x: 0 },
      { panel: 1, label: 'MS', x: 80 },
      { panel: 2, label: 'MB', x: 160 },
    ]

    panels.forEach(({ panel, x }) => {
      const stats = new Stats()
      stats.showPanel(panel)
      stats.dom.style.position = 'absolute'
      stats.dom.style.left = `${x}px`
      stats.dom.style.top = '0'
      document.body.appendChild(stats.dom)
      statsRefs.current.push(stats)
    })

    return () => {
      statsRefs.current.forEach(stats => {
        if (stats.dom.parentNode) {
          document.body.removeChild(stats.dom)
        }
      })
      statsRefs.current = []
    }
  }, [])

  useFrame(() => {
    statsRefs.current.forEach(stats => stats.update())
  })

  return null
}
```

### Custom FPS Display

```tsx
import { Html } from '@react-three/drei'

const CustomFPSDisplay = () => {
  const [fps, setFps] = useState(60)
  const [ms, setMs] = useState(0)
  const frameCount = useRef(0)
  const lastTime = useRef(performance.now())

  useFrame(() => {
    frameCount.current++

    const now = performance.now()
    const delta = now - lastTime.current

    if (delta >= 1000) {
      const currentFps = Math.round((frameCount.current * 1000) / delta)
      const currentMs = Math.round(delta / frameCount.current)

      setFps(currentFps)
      setMs(currentMs)

      frameCount.current = 0
      lastTime.current = now
    }
  })

  const color = fps >= 55 ? '#0f0' : fps >= 30 ? '#ff0' : '#f00'

  return (
    <Html position={[0, 0, 0]} center style={{ pointerEvents: 'none' }}>
      <div
        style={{
          background: 'rgba(0, 0, 0, 0.8)',
          padding: '10px',
          borderRadius: '5px',
          color: 'white',
          fontFamily: 'monospace',
          fontSize: '14px',
        }}
      >
        <div style={{ color }}>
          <strong>FPS:</strong> {fps}
        </div>
        <div>
          <strong>MS:</strong> {ms}
        </div>
      </div>
    </Html>
  )
}
```

---

## Chrome DevTools Profiling

### Performance Panel Recording

**Step-by-step process:**

1. Open Chrome DevTools (F12)
2. Go to Performance tab
3. Enable:
   - Screenshots
   - Memory
   - Web Vitals (if available)
4. Click Record (Ctrl+E)
5. Interact with your 3D scene for 5-10 seconds
6. Stop recording

**What to look for:**

- **Long Tasks** (red bars): Frames taking >50ms
- **GPU Activity**: Check for GPU bottlenecks
- **Main Thread**: JavaScript execution time
- **Raster**: Drawing operations
- **Compositor**: Compositing layers

### Analyzing Frame Drops

```tsx
const FrameDropDetector = () => {
  const frameHistory = useRef<number[]>([])
  const droppedFrames = useRef(0)

  useFrame((state, delta) => {
    const targetFrameTime = 1000 / 60 // 16.67ms for 60fps
    const actualFrameTime = delta * 1000

    frameHistory.current.push(actualFrameTime)

    // Keep last 300 frames (5 seconds at 60fps)
    if (frameHistory.current.length > 300) {
      frameHistory.current.shift()
    }

    // Detect dropped frame
    if (actualFrameTime > targetFrameTime * 1.5) {
      droppedFrames.current++
      console.warn(`Frame drop detected: ${actualFrameTime.toFixed(2)}ms`)
    }

    // Report every 5 seconds
    if (frameHistory.current.length === 300) {
      const avgFrameTime = frameHistory.current.reduce((a, b) => a + b) / 300
      const avgFps = 1000 / avgFrameTime
      const dropRate = (droppedFrames.current / 300) * 100

      console.log(`Performance Report:
        Average FPS: ${avgFps.toFixed(1)}
        Average Frame Time: ${avgFrameTime.toFixed(2)}ms
        Dropped Frames: ${droppedFrames.current} (${dropRate.toFixed(1)}%)
      `)

      frameHistory.current = []
      droppedFrames.current = 0
    }
  })

  return null
}
```

### GPU Memory Tracking

```tsx
const GPUMemoryMonitor = () => {
  const { gl } = useThree()

  useEffect(() => {
    const checkMemory = () => {
      const info = gl.info

      console.log('WebGL Info:', {
        memory: {
          geometries: info.memory.geometries,
          textures: info.memory.textures,
        },
        render: {
          calls: info.render.calls,
          triangles: info.render.triangles,
          points: info.render.points,
          lines: info.render.lines,
        },
        programs: info.programs?.length || 0,
      })
    }

    const interval = setInterval(checkMemory, 5000)
    return () => clearInterval(interval)
  }, [gl])

  return null
}
```

---

## WebGL Call Inspection

### Spector.js Integration

```html
<!-- Add Spector.js for WebGL debugging -->
<script src="https://spectorcdn.babylonjs.com/spector.bundle.js"></script>

<script>
  // Initialize Spector
  const spector = new SPECTOR.Spector()
  spector.displayUI()

  // Capture a frame
  spector.captureCanvas(document.querySelector('canvas'))
</script>
```

### Manual Draw Call Counting

```tsx
const DrawCallCounter = () => {
  const { gl } = useThree()
  const [drawCalls, setDrawCalls] = useState(0)

  useFrame(() => {
    const info = gl.info.render
    setDrawCalls(info.calls)
  })

  return (
    <Html position={[0, 3, 0]} center>
      <div style={{
        background: 'rgba(0,0,0,0.8)',
        color: drawCalls > 500 ? '#f00' : '#0f0',
        padding: '10px',
        fontFamily: 'monospace'
      }}>
        Draw Calls: {drawCalls}
        {drawCalls > 500 && <span> ⚠️ Too many!</span>}
      </div>
    </Html>
  )
}
```

### Texture Memory Analysis

```tsx
const TextureMemoryAnalyzer = () => {
  const { gl, scene } = useThree()
  const [textureMemory, setTextureMemory] = useState(0)

  useEffect(() => {
    const analyzeTextures = () => {
      let totalMemory = 0
      const textures = new Set<THREE.Texture>()

      scene.traverse((object: any) => {
        if (object.material) {
          const materials = Array.isArray(object.material)
            ? object.material
            : [object.material]

          materials.forEach(mat => {
            // Check all texture properties
            ;['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap', 'emissiveMap'].forEach(
              prop => {
                if (mat[prop] && !textures.has(mat[prop])) {
                  const tex = mat[prop]
                  textures.add(tex)

                  // Estimate memory: width × height × 4 bytes (RGBA)
                  const width = tex.image?.width || 1024
                  const height = tex.image?.height || 1024
                  const memory = width * height * 4

                  totalMemory += memory

                  console.log(`Texture: ${width}x${height} = ${(memory / 1024 / 1024).toFixed(2)} MB`)
                }
              }
            )
          })
        }
      })

      setTextureMemory(totalMemory)
      console.log(`Total Texture Memory: ${(totalMemory / 1024 / 1024).toFixed(2)} MB`)
    }

    analyzeTextures()
    const interval = setInterval(analyzeTextures, 10000)

    return () => clearInterval(interval)
  }, [scene])

  return (
    <Html position={[0, 2, 0]} center>
      <div style={{ background: 'rgba(0,0,0,0.8)', color: '#fff', padding: '10px' }}>
        Texture Memory: {(textureMemory / 1024 / 1024).toFixed(2)} MB
      </div>
    </Html>
  )
}
```

---

## Memory Profiling

### JavaScript Heap Monitoring

```tsx
const HeapMonitor = () => {
  const [heapInfo, setHeapInfo] = useState({
    used: 0,
    total: 0,
    limit: 0,
    percentage: 0,
  })

  useEffect(() => {
    const checkHeap = () => {
      if ('memory' in performance) {
        const mem = (performance as any).memory
        const used = mem.usedJSHeapSize
        const total = mem.totalJSHeapSize
        const limit = mem.jsHeapSizeLimit
        const percentage = (used / limit) * 100

        setHeapInfo({
          used: used / 1024 / 1024,
          total: total / 1024 / 1024,
          limit: limit / 1024 / 1024,
          percentage,
        })

        if (percentage > 90) {
          console.warn('⚠️ High memory usage detected!')
        }
      }
    }

    checkHeap()
    const interval = setInterval(checkHeap, 2000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div
      style={{
        position: 'absolute',
        top: '100px',
        left: '10px',
        background: 'rgba(0, 0, 0, 0.8)',
        color: heapInfo.percentage > 80 ? '#f00' : '#0f0',
        padding: '10px',
        fontFamily: 'monospace',
        fontSize: '12px',
        borderRadius: '5px',
      }}
    >
      <div>Used: {heapInfo.used.toFixed(2)} MB</div>
      <div>Total: {heapInfo.total.toFixed(2)} MB</div>
      <div>Limit: {heapInfo.limit.toFixed(2)} MB</div>
      <div>Usage: {heapInfo.percentage.toFixed(1)}%</div>
    </div>
  )
}
```

### Geometry Memory Tracking

```tsx
const GeometryMemoryTracker = () => {
  const { scene } = useThree()
  const [geometryStats, setGeometryStats] = useState({
    count: 0,
    vertices: 0,
    triangles: 0,
    estimatedMemory: 0,
  })

  useEffect(() => {
    const analyzeGeometry = () => {
      let totalVertices = 0
      let totalTriangles = 0
      let geometryCount = 0

      scene.traverse((object: any) => {
        if (object.geometry) {
          geometryCount++
          const geo = object.geometry

          const positions = geo.attributes.position
          if (positions) {
            totalVertices += positions.count

            if (geo.index) {
              totalTriangles += geo.index.count / 3
            } else {
              totalTriangles += positions.count / 3
            }
          }
        }
      })

      // Estimate memory: vertices × (position + normal + uv) × 4 bytes
      const estimatedMemory = totalVertices * (3 + 3 + 2) * 4

      setGeometryStats({
        count: geometryCount,
        vertices: totalVertices,
        triangles: Math.floor(totalTriangles),
        estimatedMemory,
      })
    }

    analyzeGeometry()
    const interval = setInterval(analyzeGeometry, 10000)

    return () => clearInterval(interval)
  }, [scene])

  return (
    <Html position={[0, 1, 0]} center>
      <div style={{ background: 'rgba(0,0,0,0.8)', color: '#fff', padding: '10px' }}>
        <div>Geometries: {geometryStats.count}</div>
        <div>Vertices: {geometryStats.vertices.toLocaleString()}</div>
        <div>Triangles: {geometryStats.triangles.toLocaleString()}</div>
        <div>Est. Memory: {(geometryStats.estimatedMemory / 1024 / 1024).toFixed(2)} MB</div>
      </div>
    </Html>
  )
}
```

---

## Custom Performance Metrics

### Comprehensive Performance Dashboard

```tsx
interface PerformanceMetrics {
  fps: number
  frameTime: number
  drawCalls: number
  triangles: number
  textures: number
  geometries: number
  programs: number
  jsHeapMB: number
  gpuMemoryMB: number
}

const PerformanceDashboard = () => {
  const { gl, scene } = useThree()
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    fps: 60,
    frameTime: 16.67,
    drawCalls: 0,
    triangles: 0,
    textures: 0,
    geometries: 0,
    programs: 0,
    jsHeapMB: 0,
    gpuMemoryMB: 0,
  })

  const lastTime = useRef(performance.now())
  const frameCount = useRef(0)

  useFrame(() => {
    frameCount.current++

    const now = performance.now()
    const delta = now - lastTime.current

    if (delta >= 1000) {
      const fps = Math.round((frameCount.current * 1000) / delta)
      const frameTime = delta / frameCount.current

      const info = gl.info

      let jsHeapMB = 0
      if ('memory' in performance) {
        jsHeapMB = (performance as any).memory.usedJSHeapSize / 1024 / 1024
      }

      setMetrics({
        fps,
        frameTime: Math.round(frameTime * 100) / 100,
        drawCalls: info.render.calls,
        triangles: info.render.triangles,
        textures: info.memory.textures,
        geometries: info.memory.geometries,
        programs: info.programs?.length || 0,
        jsHeapMB: Math.round(jsHeapMB * 100) / 100,
        gpuMemoryMB: 0, // Would need WebGL extension to get accurate GPU memory
      })

      frameCount.current = 0
      lastTime.current = now
    }
  })

  const getColorForFPS = (fps: number) => {
    if (fps >= 55) return '#0f0'
    if (fps >= 30) return '#ff0'
    return '#f00'
  }

  return (
    <div
      style={{
        position: 'absolute',
        top: '10px',
        right: '10px',
        background: 'rgba(0, 0, 0, 0.9)',
        color: '#fff',
        padding: '15px',
        fontFamily: 'monospace',
        fontSize: '12px',
        borderRadius: '8px',
        minWidth: '250px',
        boxShadow: '0 4px 8px rgba(0,0,0,0.3)',
      }}
    >
      <h3 style={{ margin: '0 0 10px 0', fontSize: '14px' }}>Performance Metrics</h3>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        <div>
          <strong style={{ color: getColorForFPS(metrics.fps) }}>FPS:</strong>
        </div>
        <div>{metrics.fps}</div>

        <div>
          <strong>Frame Time:</strong>
        </div>
        <div>{metrics.frameTime} ms</div>

        <div>
          <strong>Draw Calls:</strong>
        </div>
        <div style={{ color: metrics.drawCalls > 500 ? '#f00' : '#fff' }}>
          {metrics.drawCalls}
        </div>

        <div>
          <strong>Triangles:</strong>
        </div>
        <div style={{ color: metrics.triangles > 500000 ? '#f00' : '#fff' }}>
          {metrics.triangles.toLocaleString()}
        </div>

        <div>
          <strong>Textures:</strong>
        </div>
        <div>{metrics.textures}</div>

        <div>
          <strong>Geometries:</strong>
        </div>
        <div>{metrics.geometries}</div>

        <div>
          <strong>Programs:</strong>
        </div>
        <div>{metrics.programs}</div>

        <div>
          <strong>JS Heap:</strong>
        </div>
        <div>{metrics.jsHeapMB} MB</div>
      </div>
    </div>
  )
}
```

### Performance Budget Warnings

```tsx
interface PerformanceBudget {
  maxDrawCalls: number
  maxTriangles: number
  maxTextures: number
  maxMemoryMB: number
  minFPS: number
}

const budget: PerformanceBudget = {
  maxDrawCalls: 500,
  maxTriangles: 500000,
  maxTextures: 50,
  maxMemoryMB: 500,
  minFPS: 30,
}

const PerformanceBudgetMonitor = () => {
  const { gl } = useThree()
  const [violations, setViolations] = useState<string[]>([])

  useFrame(() => {
    const info = gl.info
    const newViolations: string[] = []

    if (info.render.calls > budget.maxDrawCalls) {
      newViolations.push(`⚠️ Draw calls: ${info.render.calls} > ${budget.maxDrawCalls}`)
    }

    if (info.render.triangles > budget.maxTriangles) {
      newViolations.push(
        `⚠️ Triangles: ${info.render.triangles.toLocaleString()} > ${budget.maxTriangles.toLocaleString()}`
      )
    }

    if (info.memory.textures > budget.maxTextures) {
      newViolations.push(`⚠️ Textures: ${info.memory.textures} > ${budget.maxTextures}`)
    }

    if ('memory' in performance) {
      const heapMB = (performance as any).memory.usedJSHeapSize / 1024 / 1024
      if (heapMB > budget.maxMemoryMB) {
        newViolations.push(
          `⚠️ Memory: ${heapMB.toFixed(0)} MB > ${budget.maxMemoryMB} MB`
        )
      }
    }

    setViolations(newViolations)
  })

  if (violations.length === 0) return null

  return (
    <div
      style={{
        position: 'absolute',
        top: '10px',
        left: '10px',
        background: 'rgba(255, 0, 0, 0.9)',
        color: '#fff',
        padding: '15px',
        fontFamily: 'monospace',
        fontSize: '12px',
        borderRadius: '8px',
        maxWidth: '400px',
      }}
    >
      <h3 style={{ margin: '0 0 10px 0' }}>Performance Budget Violations</h3>
      {violations.map((v, i) => (
        <div key={i} style={{ marginBottom: '5px' }}>
          {v}
        </div>
      ))}
    </div>
  )
}
```

---

## Automated Performance Testing

### Benchmark Suite

```tsx
interface BenchmarkResult {
  name: string
  fps: number
  avgFrameTime: number
  maxFrameTime: number
  minFrameTime: number
  droppedFrames: number
}

class PerformanceBenchmark {
  private results: BenchmarkResult[] = []

  async runBenchmark(name: string, duration: number = 5000): Promise<BenchmarkResult> {
    return new Promise(resolve => {
      const frameTimes: number[] = []
      let startTime = performance.now()
      let lastFrameTime = startTime
      let droppedFrames = 0

      const measureFrame = () => {
        const now = performance.now()
        const frameTime = now - lastFrameTime
        frameTimes.push(frameTime)

        if (frameTime > 33.33) {
          droppedFrames++
        }

        lastFrameTime = now

        if (now - startTime < duration) {
          requestAnimationFrame(measureFrame)
        } else {
          const avgFrameTime = frameTimes.reduce((a, b) => a + b) / frameTimes.length
          const result: BenchmarkResult = {
            name,
            fps: Math.round(1000 / avgFrameTime),
            avgFrameTime: Math.round(avgFrameTime * 100) / 100,
            maxFrameTime: Math.max(...frameTimes),
            minFrameTime: Math.min(...frameTimes),
            droppedFrames,
          }

          this.results.push(result)
          resolve(result)
        }
      }

      requestAnimationFrame(measureFrame)
    })
  }

  getResults(): BenchmarkResult[] {
    return this.results
  }

  printResults() {
    console.table(this.results)
  }
}

// Usage
const benchmark = new PerformanceBenchmark()

await benchmark.runBenchmark('Low Poly Scene', 5000)
await benchmark.runBenchmark('High Poly Scene', 5000)
await benchmark.runBenchmark('With Post-Processing', 5000)

benchmark.printResults()
```

### A/B Performance Testing

```tsx
const PerformanceABTest = () => {
  const [variant, setVariant] = useState<'A' | 'B'>('A')
  const [results, setResults] = useState<{ A: number[]; B: number[] }>({ A: [], B: [] })

  const recordFrame = useCallback((fps: number) => {
    setResults(prev => ({
      ...prev,
      [variant]: [...prev[variant], fps].slice(-100), // Keep last 100 frames
    }))
  }, [variant])

  useFrame((state, delta) => {
    const fps = 1 / delta
    recordFrame(fps)
  })

  const getAverage = (arr: number[]) =>
    arr.length > 0 ? arr.reduce((a, b) => a + b) / arr.length : 0

  return (
    <div style={{ position: 'absolute', top: '10px', left: '10px' }}>
      <button onClick={() => setVariant(variant === 'A' ? 'B' : 'A')}>
        Switch to {variant === 'A' ? 'B' : 'A'}
      </button>

      <div style={{ marginTop: '10px', color: '#fff' }}>
        <div>Current: {variant}</div>
        <div>A Average FPS: {getAverage(results.A).toFixed(1)}</div>
        <div>B Average FPS: {getAverage(results.B).toFixed(1)}</div>
      </div>

      {variant === 'A' ? <OptimizationVariantA /> : <OptimizationVariantB />}
    </div>
  )
}
```

---

## Performance Analysis Tools

### Flame Graph Generator

```tsx
interface FrameEvent {
  name: string
  startTime: number
  duration: number
}

class PerformanceProfiler {
  private events: FrameEvent[] = []
  private activeEvents: Map<string, number> = new Map()

  start(name: string) {
    this.activeEvents.set(name, performance.now())
  }

  end(name: string) {
    const startTime = this.activeEvents.get(name)
    if (startTime !== undefined) {
      this.events.push({
        name,
        startTime,
        duration: performance.now() - startTime,
      })
      this.activeEvents.delete(name)
    }
  }

  getEvents(): FrameEvent[] {
    return this.events
  }

  clear() {
    this.events = []
  }

  printSummary() {
    const summary = this.events.reduce((acc, event) => {
      if (!acc[event.name]) {
        acc[event.name] = { count: 0, totalTime: 0 }
      }
      acc[event.name].count++
      acc[event.name].totalTime += event.duration
      return acc
    }, {} as Record<string, { count: number; totalTime: number }>)

    console.table(
      Object.entries(summary).map(([name, data]) => ({
        name,
        count: data.count,
        avgTime: (data.totalTime / data.count).toFixed(2) + 'ms',
        totalTime: data.totalTime.toFixed(2) + 'ms',
      }))
    )
  }
}

// Usage
const profiler = new PerformanceProfiler()

function ExpensiveComponent() {
  useFrame(() => {
    profiler.start('render-loop')

    profiler.start('update-positions')
    // ... expensive position updates
    profiler.end('update-positions')

    profiler.start('update-materials')
    // ... material updates
    profiler.end('update-materials')

    profiler.end('render-loop')
  })

  return <mesh>{/* ... */}</mesh>
}

// Print summary every 5 seconds
setInterval(() => {
  profiler.printSummary()
  profiler.clear()
}, 5000)
```

---

## Summary

Performance monitoring checklist:

- [ ] Add Stats.js for real-time FPS monitoring
- [ ] Profile with Chrome DevTools Performance panel
- [ ] Monitor draw calls and triangle count
- [ ] Track GPU and CPU memory usage
- [ ] Set up performance budgets with warnings
- [ ] Implement automated benchmarking
- [ ] Use Spector.js for WebGL call inspection
- [ ] Monitor texture and geometry memory
- [ ] Create custom performance dashboards
- [ ] Test on target devices (mobile, low-end)

Remember: **Measure, don't guess.** Always profile before optimizing to ensure you're fixing the right bottlenecks.
