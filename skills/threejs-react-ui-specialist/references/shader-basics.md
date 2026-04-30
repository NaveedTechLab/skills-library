# Shader Basics for UI Effects

## Table of Contents

1. [Shader Fundamentals](#shader-fundamentals)
2. [Simple UI Shaders](#simple-ui-shaders)
3. [Animated Gradients](#animated-gradients)
4. [Glassmorphism Shaders](#glassmorphism-shaders)
5. [Glow Effects](#glow-effects)
6. [Performance Considerations](#performance-considerations)

---

## Shader Fundamentals

### What Are Shaders?

**Shaders**: Programs that run on the GPU to calculate pixel colors and vertex positions.

**Two Types**:
1. **Vertex Shader**: Transforms 3D positions to screen space
2. **Fragment Shader**: Calculates each pixel's color

**When to Use Custom Shaders**:
- Standard materials can't achieve the effect
- Need better performance than standard materials
- Want unique visual effects (holographic, glitch, etc.)

**When NOT to Use**:
- Simple solid colors (use `MeshBasicMaterial`)
- Standard lighting (use `MeshStandardMaterial`)
- You're targeting low-end devices (shaders are expensive)

---

## Simple UI Shaders

### Pattern 1: Animated Gradient Background

**Use Case**: Hero sections, card backgrounds

**Implementation**:
```tsx
import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { shaderMaterial } from '@react-three/drei'
import { extend } from '@react-three/fiber'
import * as THREE from 'three'

// Create custom shader material
const GradientMaterial = shaderMaterial(
  {
    uTime: 0,
    uColor1: new THREE.Color('#6366F1'),
    uColor2: new THREE.Color('#8B5CF6'),
  },
  // Vertex shader
  `
    varying vec2 vUv;

    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  // Fragment shader
  `
    uniform float uTime;
    uniform vec3 uColor1;
    uniform vec3 uColor2;
    varying vec2 vUv;

    void main() {
      // Animated gradient
      float mixValue = sin(vUv.y * 3.14 + uTime) * 0.5 + 0.5;
      vec3 color = mix(uColor1, uColor2, mixValue);

      gl_FragColor = vec4(color, 1.0);
    }
  `
)

// Extend to make it available as JSX
extend({ GradientMaterial })

// Component
export function AnimatedGradient() {
  const materialRef = useRef<any>()

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uTime = state.clock.elapsedTime
    }
  })

  return (
    <mesh>
      <planeGeometry args={[10, 10]} />
      <gradientMaterial ref={materialRef} />
    </mesh>
  )
}
```

**Shader Breakdown**:
- `vUv`: UV coordinates (0 to 1 for x and y)
- `uTime`: Uniform (global variable) for animation
- `mix()`: Blend two colors based on value (0-1)
- `sin()`: Oscillate between -1 and 1

---

### Pattern 2: Holographic Effect

**Use Case**: Futuristic UI cards, premium features

**Implementation**:
```tsx
const HolographicMaterial = shaderMaterial(
  {
    uTime: 0,
    uMouse: new THREE.Vector2(0, 0),
  },
  // Vertex shader
  `
    varying vec2 vUv;
    varying vec3 vNormal;

    void main() {
      vUv = uv;
      vNormal = normalize(normalMatrix * normal);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  // Fragment shader
  `
    uniform float uTime;
    uniform vec2 uMouse;
    varying vec2 vUv;
    varying vec3 vNormal;

    void main() {
      // Rainbow effect based on normal
      vec3 rainbow = vec3(
        abs(sin(vNormal.x * 2.0 + uTime)),
        abs(sin(vNormal.y * 2.0 + uTime + 2.0)),
        abs(sin(vNormal.z * 2.0 + uTime + 4.0))
      );

      // Fresnel effect (edge glow)
      float fresnel = pow(1.0 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.0);

      // Combine
      vec3 color = rainbow * fresnel;

      gl_FragColor = vec4(color, 0.8);
    }
  `
)

extend({ HolographicMaterial })

export function HolographicCard() {
  const materialRef = useRef<any>()

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uTime = state.clock.elapsedTime
      materialRef.current.uMouse.set(state.mouse.x, state.mouse.y)
    }
  })

  return (
    <mesh>
      <roundedBoxGeometry args={[2, 3, 0.2, 5, 0.1]} />
      <holographicMaterial ref={materialRef} transparent />
    </mesh>
  )
}
```

**Effect Breakdown**:
- **Rainbow**: Sinusoidal RGB based on surface normals
- **Fresnel**: Edge glow effect (brighter at glancing angles)
- **Mouse tracking**: Passed via uniform for interactivity

---

## Animated Gradients

### Pattern 3: Flowing Gradient (Wave Effect)

**Implementation**:
```tsx
const WaveGradientMaterial = shaderMaterial(
  {
    uTime: 0,
    uSpeed: 0.5,
    uIntensity: 0.3,
  },
  // Vertex shader
  `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  // Fragment shader
  `
    uniform float uTime;
    uniform float uSpeed;
    uniform float uIntensity;
    varying vec2 vUv;

    void main() {
      // Wave pattern
      float wave1 = sin(vUv.x * 10.0 + uTime * uSpeed) * uIntensity;
      float wave2 = cos(vUv.y * 10.0 + uTime * uSpeed * 0.7) * uIntensity;

      // Gradient colors
      vec3 color1 = vec3(0.39, 0.40, 0.95); // #6366F1
      vec3 color2 = vec3(0.55, 0.36, 0.96); // #8B5CF6

      // Mix based on waves
      float mixValue = (wave1 + wave2 + vUv.y) * 0.5 + 0.5;
      vec3 finalColor = mix(color1, color2, mixValue);

      gl_FragColor = vec4(finalColor, 1.0);
    }
  `
)

extend({ WaveGradientMaterial })

export function WavingBackground() {
  const materialRef = useRef<any>()

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uTime = state.clock.elapsedTime
    }
  })

  return (
    <mesh>
      <planeGeometry args={[20, 20]} />
      <waveGradientMaterial ref={materialRef} />
    </mesh>
  )
}
```

---

## Glassmorphism Shaders

### Pattern 4: Frosted Glass Effect

**Use Case**: Modern UI cards, overlay panels

**Implementation**:
```tsx
const FrostedGlassMaterial = shaderMaterial(
  {
    uBlur: 0.02,
    uOpacity: 0.3,
    uTintColor: new THREE.Color('#6366F1'),
  },
  // Vertex shader
  `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  // Fragment shader
  `
    uniform float uBlur;
    uniform float uOpacity;
    uniform vec3 uTintColor;
    varying vec2 vUv;

    void main() {
      // Noise function for frosted effect
      float noise = fract(sin(dot(vUv, vec2(12.9898, 78.233))) * 43758.5453);

      // Blur simulation (simple noise-based)
      vec2 blurredUv = vUv + vec2(noise * uBlur);

      // Tint with color
      vec3 finalColor = uTintColor * (0.8 + noise * 0.2);

      gl_FragColor = vec4(finalColor, uOpacity);
    }
  `
)

extend({ FrostedGlassMaterial })

export function GlassCard() {
  return (
    <mesh>
      <roundedBoxGeometry args={[2, 3, 0.2, 5, 0.1]} />
      <frostedGlassMaterial transparent />
    </mesh>
  )
}
```

**Note**: Real frosted glass requires post-processing. This is a lightweight approximation.

---

## Glow Effects

### Pattern 5: Neon Glow Shader

**Use Case**: Buttons, accent elements, futuristic UI

**Implementation**:
```tsx
const NeonGlowMaterial = shaderMaterial(
  {
    uTime: 0,
    uGlowColor: new THREE.Color('#6366F1'),
    uGlowIntensity: 1.5,
  },
  // Vertex shader
  `
    varying vec2 vUv;
    varying vec3 vNormal;

    void main() {
      vUv = uv;
      vNormal = normalize(normalMatrix * normal);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  // Fragment shader
  `
    uniform float uTime;
    uniform vec3 uGlowColor;
    uniform float uGlowIntensity;
    varying vec2 vUv;
    varying vec3 vNormal;

    void main() {
      // Fresnel glow (brighter at edges)
      float fresnel = pow(1.0 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.0);

      // Pulsing animation
      float pulse = sin(uTime * 2.0) * 0.2 + 0.8;

      // Combine
      vec3 glow = uGlowColor * fresnel * uGlowIntensity * pulse;

      gl_FragColor = vec4(glow, fresnel);
    }
  `
)

extend({ NeonGlowMaterial })

export function NeonButton() {
  const materialRef = useRef<any>()

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uTime = state.clock.elapsedTime
    }
  })

  return (
    <mesh>
      <roundedBoxGeometry args={[2, 0.6, 0.2, 5, 0.1]} />
      <neonGlowMaterial ref={materialRef} transparent />
    </mesh>
  )
}
```

---

## Performance Considerations

### 1. Shader Complexity

**Cost Hierarchy** (Cheapest → Most Expensive):
1. Simple math (`+`, `-`, `*`, `/`)
2. Trigonometry (`sin`, `cos`, `tan`)
3. Power functions (`pow`, `sqrt`)
4. Conditionals (`if`, `else`)
5. Loops (`for`, `while`)
6. Texture lookups (`texture2D`)

**Best Practice**: Avoid loops and conditionals in shaders. Pre-calculate on CPU if possible.

### 2. Precision Qualifiers

**Use appropriate precision**:
```glsl
// Fragment shader
precision mediump float; // Good for mobile

// Desktop can use highp
precision highp float;

// Per-variable precision
lowp float roughValue;     // Color values (0-1)
mediump vec2 uv;           // UV coordinates
highp vec3 position;       // Precise calculations
```

### 3. Uniform vs Varying

**Uniforms**: Same value for all pixels (cheap)
```glsl
uniform float uTime; // Changed once per frame
```

**Varyings**: Interpolated per pixel (more expensive)
```glsl
varying vec2 vUv; // Different for each pixel
```

**Rule**: Pass data as uniforms when possible.

### 4. Optimize Math

**Avoid**:
```glsl
// Expensive
float result = pow(value, 2.0);
float distance = sqrt(x*x + y*y);
```

**Prefer**:
```glsl
// Cheaper
float result = value * value;
float distanceSq = x*x + y*y; // Use squared distance if possible
```

---

## Common Shader Patterns (Copy-Paste Ready)

### Simple Fade

```glsl
// Fragment shader
void main() {
  float alpha = 1.0 - vUv.y; // Fade top to bottom
  gl_FragColor = vec4(color, alpha);
}
```

### Radial Gradient

```glsl
void main() {
  float dist = length(vUv - 0.5) * 2.0; // 0 at center, 1 at edges
  vec3 color = mix(color1, color2, dist);
  gl_FragColor = vec4(color, 1.0);
}
```

### Pulsing Glow

```glsl
uniform float uTime;

void main() {
  float pulse = sin(uTime * 3.0) * 0.5 + 0.5; // 0 to 1
  vec3 glow = color * pulse;
  gl_FragColor = vec4(glow, 1.0);
}
```

### Mouse-Interactive

```glsl
uniform vec2 uMouse; // Pass mouse position

void main() {
  float dist = distance(vUv, uMouse * 0.5 + 0.5);
  float intensity = 1.0 - smoothstep(0.0, 0.5, dist);
  gl_FragColor = vec4(color * intensity, 1.0);
}
```

---

## Debugging Shaders

### Visualize Values

**Show UV coordinates as colors**:
```glsl
void main() {
  gl_FragColor = vec4(vUv.x, vUv.y, 0.0, 1.0);
  // Red = X axis, Green = Y axis
}
```

**Show normals**:
```glsl
void main() {
  gl_FragColor = vec4(vNormal * 0.5 + 0.5, 1.0);
}
```

**Show time**:
```glsl
void main() {
  float t = fract(uTime); // Loop 0 to 1
  gl_FragColor = vec4(vec3(t), 1.0);
}
```

### Common Errors

**Black screen**: Check shader compilation errors in console

**Flickering**: Divide by zero or NaN values

**Wrong colors**: Check color space (0-1 in shaders, 0-255 in CSS)

**No animation**: Forgot to update uniform in `useFrame`

---

## When to Use Standard Materials Instead

### Use `MeshBasicMaterial` for:
- Solid colors without lighting
- UI elements (buttons, icons)
- 2D sprites

### Use `MeshStandardMaterial` for:
- Realistic lighting
- Metallic/roughness surfaces
- Most 3D objects

### Use Custom Shaders for:
- Unique effects (holographic, neon, glitch)
- Performance-critical scenes (optimize specific materials)
- Effects impossible with standard materials

---

## Shader Resources

**Learning**:
- [The Book of Shaders](https://thebookofshaders.com/) - Interactive tutorial
- [ShaderToy](https://www.shadertoy.com/) - Community shader examples
- [GLSL Sandbox](http://glslsandbox.com/) - Live shader editor

**Tools**:
- [Shader Editor (VS Code)](https://marketplace.visualstudio.com/items?itemName=slevesque.shader)
- [glslViewer](https://github.com/patriciogonzalezvivo/glslViewer) - Terminal shader viewer

---

**Remember**: Shaders are powerful but expensive. Use standard materials when possible. Profile performance.
