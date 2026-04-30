# Fallback Strategies for WebGL Applications

Progressive enhancement and graceful degradation strategies for Three.js/WebGL applications to ensure accessibility and performance across all devices.

## Table of Contents

1. [WebGL Detection](#webgl-detection)
2. [Progressive Enhancement](#progressive-enhancement)
3. [Adaptive Quality Levels](#adaptive-quality-levels)
4. [Static Alternatives](#static-alternatives)
5. [Feature Detection](#feature-detection)
6. [User Controls](#user-controls)

---

## WebGL Detection

### Basic WebGL Availability Check

```tsx
export function detectWebGL(): boolean {
  try {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
    return !!gl
  } catch (e) {
    return false
  }
}

export function detectWebGL2(): boolean {
  try {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl2')
    return !!gl
  } catch (e) {
    return false
  }
}
```

### Comprehensive WebGL Support Detection

```tsx
interface WebGLCapabilities {
  webgl: boolean
  webgl2: boolean
  maxTextureSize: number
  maxVertexUniforms: number
  maxFragmentUniforms: number
  maxVertexAttributes: number
  maxVaryingVectors: number
  extensions: string[]
}

export function getWebGLCapabilities(): WebGLCapabilities | null {
  const canvas = document.createElement('canvas')
  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl')

  if (!gl) {
    return null
  }

  const gl2 = canvas.getContext('webgl2')

  return {
    webgl: true,
    webgl2: !!gl2,
    maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
    maxVertexUniforms: gl.getParameter(gl.MAX_VERTEX_UNIFORM_VECTORS),
    maxFragmentUniforms: gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS),
    maxVertexAttributes: gl.getParameter(gl.MAX_VERTEX_ATTRIBS),
    maxVaryingVectors: gl.getParameter(gl.MAX_VARYING_VECTORS),
    extensions: gl.getSupportedExtensions() || [],
  }
}
```

### React Hook for WebGL Detection

```tsx
export function useWebGLSupport() {
  const [support, setSupport] = useState<WebGLCapabilities | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const capabilities = getWebGLCapabilities()
    setSupport(capabilities)
    setLoading(false)
  }, [])

  return { support, loading, isSupported: !!support }
}

// Usage
const MyComponent = () => {
  const { isSupported, loading, support } = useWebGLSupport()

  if (loading) return <LoadingSpinner />
  if (!isSupported) return <WebGLNotSupported />

  return (
    <Canvas>
      {/* 3D content */}
    </Canvas>
  )
}
```

---

## Progressive Enhancement

### Tiered Rendering Modes

```tsx
type RenderMode = 'webgl2' | 'webgl1' | '2d' | 'static'

function detectBestRenderMode(): RenderMode {
  if (detectWebGL2()) return 'webgl2'
  if (detectWebGL()) return 'webgl1'

  // Check if Canvas2D is available
  try {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    if (ctx) return '2d'
  } catch (e) {
    // Canvas2D not supported
  }

  return 'static'
}

const AdaptiveVisualization = ({ data }) => {
  const [mode, setMode] = useState<RenderMode>(() => detectBestRenderMode())

  return (
    <div className="visualization-container">
      {mode === 'webgl2' && <FullQuality3DScene data={data} />}
      {mode === 'webgl1' && <Reduced3DScene data={data} />}
      {mode === '2d' && <Canvas2DVisualization data={data} />}
      {mode === 'static' && <StaticImageFallback data={data} />}

      <QualitySelector currentMode={mode} onModeChange={setMode} />
    </div>
  )
}
```

### Progressive Loading Strategy

```tsx
const ProgressiveScene = () => {
  const [loadLevel, setLoadLevel] = useState(0)

  useEffect(() => {
    // Load in stages
    const timers = [
      setTimeout(() => setLoadLevel(1), 0),     // Basic geometry
      setTimeout(() => setLoadLevel(2), 500),   // Add textures
      setTimeout(() => setLoadLevel(3), 1000),  // Add lighting
      setTimeout(() => setLoadLevel(4), 1500),  // Add effects
    ]

    return () => timers.forEach(clearTimeout)
  }, [])

  return (
    <Canvas>
      {/* Level 0: Loading state */}
      {loadLevel === 0 && <LoadingPlaceholder />}

      {/* Level 1: Basic geometry */}
      {loadLevel >= 1 && <BasicGeometry />}

      {/* Level 2: Add textures */}
      {loadLevel >= 2 && <TexturedMaterials />}

      {/* Level 3: Add lighting */}
      {loadLevel >= 3 && (
        <>
          <ambientLight intensity={0.5} />
          <directionalLight position={[5, 5, 5]} />
        </>
      )}

      {/* Level 4: Add effects */}
      {loadLevel >= 4 && <PostProcessing />}
    </Canvas>
  )
}
```

### Capability-Based Feature Loading

```tsx
const FeatureDetector = () => {
  const capabilities = getWebGLCapabilities()

  const features = {
    shadows: capabilities?.extensions.includes('WEBGL_depth_texture'),
    instancedArrays: capabilities?.extensions.includes('ANGLE_instanced_arrays'),
    floatTextures: capabilities?.extensions.includes('OES_texture_float'),
    highPrecision: capabilities?.maxFragmentUniforms && capabilities.maxFragmentUniforms > 200,
  }

  return (
    <Canvas shadows={features.shadows}>
      {features.instancedArrays ? (
        <InstancedParticles count={10000} />
      ) : (
        <SimpleParticles count={100} />
      )}

      {features.floatTextures && <AdvancedEffects />}
    </Canvas>
  )
}
```

---

## Adaptive Quality Levels

### Performance-Based Auto Quality

```tsx
type QualityLevel = 'ultra' | 'high' | 'medium' | 'low' | 'minimal'

interface QualitySettings {
  dpr: number
  shadows: boolean
  antialias: boolean
  particleCount: number
  textureSize: 'high' | 'medium' | 'low'
  postProcessing: boolean
}

const qualityPresets: Record<QualityLevel, QualitySettings> = {
  ultra: {
    dpr: 2,
    shadows: true,
    antialias: true,
    particleCount: 10000,
    textureSize: 'high',
    postProcessing: true,
  },
  high: {
    dpr: 1.5,
    shadows: true,
    antialias: true,
    particleCount: 5000,
    textureSize: 'high',
    postProcessing: true,
  },
  medium: {
    dpr: 1,
    shadows: true,
    antialias: false,
    particleCount: 2000,
    textureSize: 'medium',
    postProcessing: false,
  },
  low: {
    dpr: 1,
    shadows: false,
    antialias: false,
    particleCount: 500,
    textureSize: 'low',
    postProcessing: false,
  },
  minimal: {
    dpr: 1,
    shadows: false,
    antialias: false,
    particleCount: 100,
    textureSize: 'low',
    postProcessing: false,
  },
}

const AdaptiveQualityScene = () => {
  const [quality, setQuality] = useState<QualityLevel>('high')
  const fpsHistory = useRef<number[]>([])
  const settings = qualityPresets[quality]

  useFrame((state, delta) => {
    const currentFps = 1 / delta

    // Keep rolling average of last 60 frames
    fpsHistory.current.push(currentFps)
    if (fpsHistory.current.length > 60) {
      fpsHistory.current.shift()
    }

    // Check performance every 60 frames
    if (fpsHistory.current.length === 60) {
      const avgFps = fpsHistory.current.reduce((a, b) => a + b) / 60

      // Auto-adjust quality
      if (avgFps < 25 && quality !== 'minimal') {
        console.log('Performance low, reducing quality')
        const levels: QualityLevel[] = ['ultra', 'high', 'medium', 'low', 'minimal']
        const currentIndex = levels.indexOf(quality)
        setQuality(levels[Math.min(currentIndex + 1, levels.length - 1)])
        fpsHistory.current = []
      } else if (avgFps > 55 && quality !== 'ultra') {
        console.log('Performance good, increasing quality')
        const levels: QualityLevel[] = ['ultra', 'high', 'medium', 'low', 'minimal']
        const currentIndex = levels.indexOf(quality)
        setQuality(levels[Math.max(currentIndex - 1, 0)])
        fpsHistory.current = []
      }
    }
  })

  return (
    <Canvas
      dpr={settings.dpr}
      shadows={settings.shadows}
      gl={{ antialias: settings.antialias }}
    >
      <Scene
        particleCount={settings.particleCount}
        textureQuality={settings.textureSize}
      />

      {settings.postProcessing && <Effects />}
    </Canvas>
  )
}
```

### Device-Based Initial Quality

```tsx
function getInitialQuality(): QualityLevel {
  const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
  const isLowEndMobile = isMobile && (
    /Android [1-6]/.test(navigator.userAgent) ||
    /iPhone OS [1-9]_/.test(navigator.userAgent)
  )

  // Check GPU tier if possible
  const canvas = document.createElement('canvas')
  const gl = canvas.getContext('webgl')
  const debugInfo = gl?.getExtension('WEBGL_debug_renderer_info')
  const renderer = debugInfo ? gl?.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : null

  // Integrated graphics detection
  const isIntegrated = renderer?.includes('Intel') || renderer?.includes('Mali')

  if (isLowEndMobile) return 'minimal'
  if (isMobile) return 'low'
  if (isIntegrated) return 'medium'

  // Desktop with dedicated GPU
  return 'high'
}

const SmartDefaultQuality = () => {
  const [quality] = useState<QualityLevel>(() => getInitialQuality())

  return <AdaptiveQualityScene initialQuality={quality} />
}
```

---

## Static Alternatives

### Prerendered Images

```tsx
const StaticSceneFallback = ({ sceneName }) => {
  return (
    <div className="static-fallback">
      <img
        src={`/static-renders/${sceneName}.jpg`}
        alt="3D Scene Preview"
        style={{ width: '100%', height: 'auto' }}
      />
      <div className="fallback-message">
        <p>Your browser doesn't support WebGL.</p>
        <p>Showing static preview instead.</p>
      </div>
    </div>
  )
}
```

### Video Fallback for Animations

```tsx
const VideoFallback = ({ videoPath, posterPath }) => {
  return (
    <div className="video-fallback">
      <video
        autoPlay
        loop
        muted
        playsInline
        poster={posterPath}
        style={{ width: '100%', height: 'auto' }}
      >
        <source src={`${videoPath}.webm`} type="video/webm" />
        <source src={`${videoPath}.mp4`} type="video/mp4" />
        Your browser doesn't support video playback.
      </video>

      <div className="fallback-notice">
        WebGL not available. Showing video preview.
      </div>
    </div>
  )
}
```

### CSS 3D Transform Fallback

```tsx
const CSS3DFallback = () => {
  return (
    <div className="css-3d-scene">
      <style>{`
        .css-3d-scene {
          perspective: 1000px;
        }

        .css-3d-box {
          width: 200px;
          height: 200px;
          position: relative;
          transform-style: preserve-3d;
          animation: rotate 5s infinite linear;
        }

        .css-3d-box__face {
          position: absolute;
          width: 200px;
          height: 200px;
          background: rgba(100, 150, 255, 0.8);
          border: 2px solid #fff;
        }

        .css-3d-box__face--front  { transform: translateZ(100px); }
        .css-3d-box__face--back   { transform: rotateY(180deg) translateZ(100px); }
        .css-3d-box__face--right  { transform: rotateY(90deg) translateZ(100px); }
        .css-3d-box__face--left   { transform: rotateY(-90deg) translateZ(100px); }
        .css-3d-box__face--top    { transform: rotateX(90deg) translateZ(100px); }
        .css-3d-box__face--bottom { transform: rotateX(-90deg) translateZ(100px); }

        @keyframes rotate {
          from { transform: rotateX(0deg) rotateY(0deg); }
          to   { transform: rotateX(360deg) rotateY(360deg); }
        }
      `}</style>

      <div className="css-3d-box">
        <div className="css-3d-box__face css-3d-box__face--front"></div>
        <div className="css-3d-box__face css-3d-box__face--back"></div>
        <div className="css-3d-box__face css-3d-box__face--right"></div>
        <div className="css-3d-box__face css-3d-box__face--left"></div>
        <div className="css-3d-box__face css-3d-box__face--top"></div>
        <div className="css-3d-box__face css-3d-box__face--bottom"></div>
      </div>

      <p className="fallback-notice">
        WebGL not available. Using CSS 3D transforms.
      </p>
    </div>
  )
}
```

### Canvas 2D Fallback

```tsx
const Canvas2DFallback = ({ data }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Draw 2D representation
    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Draw data as 2D visualization
      data.forEach((point, i) => {
        ctx.fillStyle = `hsl(${i * 10}, 70%, 50%)`
        ctx.beginPath()
        ctx.arc(point.x, point.y, 5, 0, Math.PI * 2)
        ctx.fill()
      })

      requestAnimationFrame(draw)
    }

    draw()
  }, [data])

  return (
    <div>
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        style={{ border: '1px solid #ccc' }}
      />
      <p className="fallback-notice">
        WebGL not available. Using Canvas 2D rendering.
      </p>
    </div>
  )
}
```

---

## Feature Detection

### Extension Support Checking

```tsx
function checkRequiredExtensions(gl: WebGLRenderingContext, required: string[]): boolean {
  const supported = gl.getSupportedExtensions() || []
  return required.every(ext => supported.includes(ext))
}

const ExtensionDependentFeature = () => {
  const requiredExtensions = [
    'WEBGL_depth_texture',
    'OES_texture_float',
    'ANGLE_instanced_arrays',
  ]

  const [supported, setSupported] = useState(false)

  useEffect(() => {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl')

    if (gl) {
      setSupported(checkRequiredExtensions(gl, requiredExtensions))
    }
  }, [])

  return supported ? (
    <AdvancedFeature />
  ) : (
    <SimplifiedFeature message="Advanced features not supported on this device" />
  )
}
```

### Floating Point Texture Support

```tsx
function checkFloatTextureSupport(): boolean {
  const canvas = document.createElement('canvas')
  const gl = canvas.getContext('webgl')

  if (!gl) return false

  const ext = gl.getExtension('OES_texture_float')
  if (!ext) return false

  // Test if we can actually render to float texture
  const texture = gl.createTexture()
  gl.bindTexture(gl.TEXTURE_2D, texture)
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.FLOAT, null)

  const fb = gl.createFramebuffer()
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb)
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0)

  const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER)
  return status === gl.FRAMEBUFFER_COMPLETE
}
```

---

## User Controls

### Quality Settings UI

```tsx
const QualityControl = ({ onQualityChange }) => {
  const [quality, setQuality] = useState<QualityLevel>('auto')
  const [autoAdjust, setAutoAdjust] = useState(true)

  const handleChange = (newQuality: QualityLevel) => {
    setQuality(newQuality)
    setAutoAdjust(newQuality === 'auto')
    onQualityChange(newQuality)
  }

  return (
    <div className="quality-control">
      <h3>Graphics Quality</h3>

      <select value={quality} onChange={e => handleChange(e.target.value as QualityLevel)}>
        <option value="auto">Auto (Recommended)</option>
        <option value="ultra">Ultra (High-end PC)</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
        <option value="minimal">Minimal (Mobile)</option>
      </select>

      <div className="quality-options">
        <label>
          <input
            type="checkbox"
            checked={autoAdjust}
            onChange={e => setAutoAdjust(e.target.checked)}
          />
          Auto-adjust based on performance
        </label>
      </div>

      <div className="quality-info">
        {quality !== 'auto' && (
          <small>
            Manual quality selected. Auto-adjustment disabled.
          </small>
        )}
      </div>
    </div>
  )
}
```

### Performance Mode Toggle

```tsx
const PerformanceModeToggle = () => {
  const [performanceMode, setPerformanceMode] = useState(false)

  return (
    <div className="performance-toggle">
      <button
        onClick={() => setPerformanceMode(!performanceMode)}
        className={performanceMode ? 'active' : ''}
      >
        {performanceMode ? '⚡ Performance Mode ON' : '🎨 Full Quality'}
      </button>

      <Canvas>
        {performanceMode ? (
          <PerformanceOptimizedScene />
        ) : (
          <FullQualityScene />
        )}
      </Canvas>
    </div>
  )
}
```

### Accessibility Preferences

```tsx
const AccessibleVisualization = () => {
  const [reducedMotion, setReducedMotion] = useState(false)
  const [highContrast, setHighContrast] = useState(false)

  // Detect user preferences
  useEffect(() => {
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const contrastQuery = window.matchMedia('(prefers-contrast: high)')

    setReducedMotion(motionQuery.matches)
    setHighContrast(contrastQuery.matches)

    const handleMotionChange = (e: MediaQueryListEvent) => setReducedMotion(e.matches)
    const handleContrastChange = (e: MediaQueryListEvent) => setHighContrast(e.matches)

    motionQuery.addEventListener('change', handleMotionChange)
    contrastQuery.addEventListener('change', handleContrastChange)

    return () => {
      motionQuery.removeEventListener('change', handleMotionChange)
      contrastQuery.removeEventListener('change', handleContrastChange)
    }
  }, [])

  return (
    <Canvas>
      <Scene
        animationSpeed={reducedMotion ? 0.1 : 1}
        highContrast={highContrast}
      />
    </Canvas>
  )
}
```

---

## Complete Fallback System

### Unified Fallback Strategy

```tsx
type ViewMode = 'webgl2-full' | 'webgl2-reduced' | 'webgl1' | '2d' | 'static'

const UnifiedFallbackSystem = ({ data }) => {
  const [mode, setMode] = useState<ViewMode>('webgl2-full')
  const [userOverride, setUserOverride] = useState<ViewMode | null>(null)

  useEffect(() => {
    // Auto-detect best mode
    const detected = detectBestViewMode()
    if (!userOverride) {
      setMode(detected)
    }
  }, [userOverride])

  const currentMode = userOverride || mode

  return (
    <div className="visualization-wrapper">
      <div className="mode-selector">
        <select
          value={currentMode}
          onChange={e => setUserOverride(e.target.value as ViewMode)}
        >
          <option value="webgl2-full">Full Quality (WebGL 2)</option>
          <option value="webgl2-reduced">Reduced Quality (WebGL 2)</option>
          <option value="webgl1">Basic 3D (WebGL 1)</option>
          <option value="2d">2D View</option>
          <option value="static">Static Image</option>
        </select>
      </div>

      {currentMode === 'webgl2-full' && <FullQuality3D data={data} />}
      {currentMode === 'webgl2-reduced' && <ReducedQuality3D data={data} />}
      {currentMode === 'webgl1' && <BasicWebGL1Scene data={data} />}
      {currentMode === '2d' && <Canvas2DVisualization data={data} />}
      {currentMode === 'static' && <StaticImageFallback data={data} />}
    </div>
  )
}

function detectBestViewMode(): ViewMode {
  if (!detectWebGL()) return 'static'
  if (!detectWebGL2()) return 'webgl1'

  const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
  if (isMobile) return 'webgl2-reduced'

  return 'webgl2-full'
}
```

---

## Summary

Fallback strategies checklist:

- [ ] Detect WebGL support and version
- [ ] Implement tiered quality levels (ultra → minimal)
- [ ] Provide static alternatives (images/video)
- [ ] Auto-adjust quality based on FPS
- [ ] Respect user accessibility preferences
- [ ] Allow manual quality override
- [ ] Test on low-end devices
- [ ] Gracefully degrade features
- [ ] Show helpful error messages
- [ ] Provide CSS/Canvas 2D fallbacks when possible

Always ensure your application is usable even when WebGL is unavailable or performing poorly.
