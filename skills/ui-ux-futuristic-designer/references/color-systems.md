# Extended Color Palette Systems (2026)

## Table of Contents

1. [Dark Theme Palettes](#dark-theme-palettes)
2. [Accent Color Systems](#accent-color-systems)
3. [Semantic Colors](#semantic-colors)
4. [Gradient Collections](#gradient-collections)
5. [Color Utilities](#color-utilities)

---

## Dark Theme Palettes

### Midnight Blue (Professional SaaS)

**Background Layers**:
```
BG Primary:   #0A0E1A  (Deep navy-black)
BG Secondary: #0F1420  (Slightly lighter navy)
BG Tertiary:  #151B2B  (Card background)

Surface 1:    rgba(255, 255, 255, 0.04)  (Subtle glass)
Surface 2:    rgba(255, 255, 255, 0.07)  (Elevated glass)
Surface 3:    rgba(255, 255, 255, 0.10)  (Highest elevation)
Surface 4:    rgba(255, 255, 255, 0.13)  (Modal/dropdown)
```

**Text Hierarchy**:
```
Text Primary:     #FFFFFF           (100% opacity - Headings)
Text Secondary:   rgba(255, 255, 255, 0.87)  (Body text)
Text Tertiary:    rgba(255, 255, 255, 0.60)  (Labels, captions)
Text Disabled:    rgba(255, 255, 255, 0.38)  (Disabled state)
Text Placeholder: rgba(255, 255, 255, 0.30)  (Input placeholders)
```

**Use Case**: Finance apps, analytics dashboards, enterprise SaaS

---

### Carbon Black (Modern & Sleek)

**Background Layers**:
```
BG Primary:   #0D0D0D  (Pure dark)
BG Secondary: #161616  (Charcoal)
BG Tertiary:  #1F1F1F  (Card background)

Surface 1:    rgba(255, 255, 255, 0.05)
Surface 2:    rgba(255, 255, 255, 0.08)
Surface 3:    rgba(255, 255, 255, 0.11)
Surface 4:    rgba(255, 255, 255, 0.14)
```

**Accent**: Pair with neon accents (#00FF88, #FF006E, #00D4FF)

**Use Case**: Creative tools, developer platforms, design apps

---

### Deep Purple (Creative & Bold)

**Background Layers**:
```
BG Primary:   #0F0518  (Deep purple-black)
BG Secondary: #1A0B2E  (Dark purple)
BG Tertiary:  #251447  (Purple card)

Surface 1:    rgba(138, 92, 246, 0.08)  (Purple-tinted glass)
Surface 2:    rgba(138, 92, 246, 0.12)
Surface 3:    rgba(138, 92, 246, 0.16)
Surface 4:    rgba(138, 92, 246, 0.20)
```

**Use Case**: Gaming platforms, music apps, entertainment SaaS

---

## Accent Color Systems

### Vibrant Indigo (Primary Choice)

**Main Palette**:
```
50:  #EEF2FF
100: #E0E7FF
200: #C7D2FE
300: #A5B4FC
400: #818CF8
500: #6366F1  ← Primary (most used)
600: #4F46E5
700: #4338CA
800: #3730A3
900: #312E81
```

**Usage**:
- Primary: Buttons, links, active states
- Hover: 600 shade
- Active: 700 shade
- Disabled: 400 shade with 40% opacity

---

### Electric Cyan (Modern Tech)

**Main Palette**:
```
50:  #ECFEFF
100: #CFFAFE
200: #A5F3FC
300: #67E8F9
400: #22D3EE
500: #06B6D4  ← Primary
600: #0891B2
700: #0E7490
800: #155E75
900: #164E63
```

**Usage**: Tech products, developer tools, data platforms

---

### Neon Green (Bold & Energetic)

**Main Palette**:
```
50:  #F0FDF4
100: #DCFCE7
200: #BBF7D0
300: #86EFAC
400: #4ADE80
500: #22C55E  ← Primary
600: #16A34A
700: #15803D
800: #166534
900: #14532D
```

**Usage**: Fitness apps, growth metrics, positive actions

---

### Vivid Purple (Premium & Creative)

**Main Palette**:
```
50:  #FAF5FF
100: #F3E8FF
200: #E9D5FF
300: #D8B4FE
400: #C084FC
500: #A855F7  ← Primary
600: #9333EA
700: #7E22CE
800: #6B21A8
900: #581C87
```

**Usage**: Creative tools, premium features, branding

---

## Semantic Colors

### Success States

```
Primary Success:   #10B981  (Emerald 500)
Success BG Light:  rgba(16, 185, 129, 0.15)  (For success cards)
Success Border:    rgba(16, 185, 129, 0.30)
Success Text:      #34D399  (Lighter for dark bg)
Success Glow:      0 0 20px rgba(16, 185, 129, 0.4)
```

**Use**: Completed tasks, positive trends, confirmations

---

### Warning States

```
Primary Warning:   #F59E0B  (Amber 500)
Warning BG Light:  rgba(245, 158, 11, 0.15)
Warning Border:    rgba(245, 158, 11, 0.30)
Warning Text:      #FCD34D  (Lighter for dark bg)
Warning Glow:      0 0 20px rgba(245, 158, 11, 0.4)
```

**Use**: Pending actions, cautions, quota alerts

---

### Error States

```
Primary Error:     #EF4444  (Red 500)
Error BG Light:    rgba(239, 68, 68, 0.15)
Error Border:      rgba(239, 68, 68, 0.30)
Error Text:        #F87171  (Lighter for dark bg)
Error Glow:        0 0 20px rgba(239, 68, 68, 0.4)
```

**Use**: Failed actions, destructive operations, validation errors

---

### Info States

```
Primary Info:      #3B82F6  (Blue 500)
Info BG Light:     rgba(59, 130, 246, 0.15)
Info Border:       rgba(59, 130, 246, 0.30)
Info Text:         #60A5FA  (Lighter for dark bg)
Info Glow:         0 0 20px rgba(59, 130, 246, 0.4)
```

**Use**: Informational messages, tips, neutral notifications

---

## Gradient Collections

### Premium Gradients (Buttons, Headers)

**Indigo Dream**:
```
linear-gradient(135deg, #667EEA 0%, #764BA2 100%)
Use: Premium CTAs, hero sections
```

**Cyber Purple**:
```
linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%)
Use: Primary buttons, feature highlights
```

**Ocean Blue**:
```
linear-gradient(135deg, #0EA5E9 0%, #06B6D4 100%)
Use: Info panels, tech features
```

**Mint Fresh**:
```
linear-gradient(135deg, #10B981 0%, #34D399 100%)
Use: Success states, growth indicators
```

**Sunset Orange**:
```
linear-gradient(135deg, #F59E0B 0%, #F97316 100%)
Use: Warning states, call attention
```

**Neon Glow**:
```
linear-gradient(135deg, #06B6D4 0%, #8B5CF6 50%, #EC4899 100%)
Use: Hero sections, futuristic effects
```

---

### Background Gradients (Subtle)

**Dark Mesh**:
```
radial-gradient(at 40% 20%, rgba(99, 102, 241, 0.15) 0, transparent 50%),
radial-gradient(at 80% 80%, rgba(139, 92, 246, 0.15) 0, transparent 50%),
radial-gradient(at 20% 80%, rgba(6, 182, 212, 0.15) 0, transparent 50%)

Use: Dashboard backgrounds, hero sections
```

**Purple Haze**:
```
radial-gradient(circle at 20% 50%, rgba(138, 92, 246, 0.2) 0, transparent 60%),
radial-gradient(circle at 80% 50%, rgba(168, 85, 247, 0.15) 0, transparent 60%)

Use: Landing pages, creative sections
```

---

## Color Utilities

### Opacity Scale (For Text & Overlays)

```
100%: Primary headings, active states
 87%: Body text, labels
 75%: Secondary text
 60%: Tertiary text, placeholders
 50%: Dividers, subtle borders
 38%: Disabled text
 25%: Subtle backgrounds
 15%: Hover states
 10%: Card backgrounds
  5%: Subtle overlays
  3%: Barely visible backgrounds
```

---

### Border Colors

```
Subtle:    rgba(255, 255, 255, 0.08)  (Most cards)
Moderate:  rgba(255, 255, 255, 0.12)  (Inputs, elevated cards)
Strong:    rgba(255, 255, 255, 0.18)  (Focus states)
Accent:    Use primary color at 50% opacity
```

---

### Glow Effects (For Accent Elements)

**Soft Glow**:
```
box-shadow: 0 0 20px rgba(99, 102, 241, 0.3)
Use: Buttons, active states
```

**Medium Glow**:
```
box-shadow: 0 0 40px rgba(99, 102, 241, 0.5)
Use: Hero CTAs, modals
```

**Strong Glow**:
```
box-shadow: 0 0 60px rgba(99, 102, 241, 0.7)
Use: Neon effects, futuristic highlights
```

---

## Choosing the Right Palette

**Professional SaaS (Finance, Analytics)**:
- Background: Midnight Blue
- Accent: Indigo or Cyan
- Semantic: Standard (Green/Amber/Red)

**Creative Tools (Design, Music, Gaming)**:
- Background: Deep Purple or Carbon Black
- Accent: Vivid Purple or Neon Green
- Semantic: Vibrant versions with glows

**Developer Platforms**:
- Background: Carbon Black
- Accent: Electric Cyan or Neon Green
- Semantic: High contrast versions

**Enterprise Apps**:
- Background: Midnight Blue
- Accent: Professional Indigo
- Semantic: Muted versions (less saturation)

---

## Accessibility Testing

**Check All Color Combinations**:
- Text on BG Primary: Minimum 7:1 (AAA)
- Text on Surface layers: Minimum 4.5:1 (AA)
- Accent on BG: Minimum 3:1 for UI components
- Interactive elements: Minimum 3:1 contrast with surroundings

**Tools**:
- WebAIM Contrast Checker
- Accessible Colors Palette Generator
- Chrome DevTools Color Picker (shows contrast ratios)
