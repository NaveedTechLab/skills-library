---
name: brand-guidelines
description: Applies Anthropic's official brand colors and typography to any sort of artifact that may benefit from having Anthropic's look-and-feel. Use it when brand colors or style guidelines, visual formatting, or company design standards apply.
license: Complete terms in LICENSE.txt
---

# Anthropic Brand Styling

## Overview

To access Anthropic's official brand identity and style resources, use this skill.

**Keywords**: branding, corporate identity, visual identity, post-processing, styling, brand colors, typography, Anthropic brand, visual formatting, visual design

## Brand Guidelines

### Colors

**Main Colors:**

- Dark: `#141413` - Primary text and dark backgrounds
- Light: `#faf9f5` - Light backgrounds and text on dark
- Mid Gray: `#b0aea5` - Secondary elements
- Light Gray: `#e8e6dc` - Subtle backgrounds

**Accent Colors:**

- Orange: `#d97757` - Primary accent
- Blue: `#6a9bcc` - Secondary accent
- Green: `#788c5d` - Tertiary accent

### Typography

- **Headings**: Poppins (with Arial fallback)
- **Body Text**: Lora (with Georgia fallback)
- **Note**: Fonts should be pre-installed in your environment for best results

## Features

### Smart Font Application

- Applies Poppins font to headings (24pt and larger)
- Applies Lora font to body text
- Automatically falls back to Arial/Georgia if custom fonts unavailable
- Preserves readability across all systems

### Text Styling

- Headings (24pt+): Poppins font
- Body text: Lora font
- Smart color selection based on background
- Preserves text hierarchy and formatting

### Shape and Accent Colors

- Non-text shapes use accent colors
- Cycles through orange, blue, and green accents
- Maintains visual interest while staying on-brand

## Technical Details

### Font Management

- Uses system-installed Poppins and Lora fonts when available
- Provides automatic fallback to Arial (headings) and Georgia (body)
- No font installation required - works with existing system fonts
- For best results, pre-install Poppins and Lora fonts in your environment

### Color Application

- Uses RGB color values for precise brand matching
- Applied via python-pptx's RGBColor class
- Maintains color fidelity across different systems

## When NOT to Use This Skill

- **Personal projects without a brand identity** — brand guidelines require intentional brand decisions; don't generate them as a placeholder
- **Rebranding an existing organization** — rebrands need stakeholder input and strategic alignment, not AI-generated guidelines alone
- **Legal trademark or IP documentation** — brand guidelines don't substitute for proper trademark filings; consult a legal professional for IP protection

## Common Mistakes

- Generating color palettes without checking accessibility contrast ratios — WCAG 2.1 AA requires 4.5:1 contrast for body text
- Defining brand voice without real-world examples — abstract tone descriptions ("bold but approachable") are unactionable; always include do/don't examples
- Not specifying minimum logo sizes and clear-space rules — logos get misused when usage constraints are absent from the guide

## Related Skills

- [`canvas-design`](../canvas-design/SKILL.md) — Implement the brand guidelines in Canvas-based visual assets
- [`theme-factory`](../theme-factory/SKILL.md) — Convert brand guidelines into code-ready design tokens and themes
- [`ui-ux-futuristic-designer`](../ui-ux-futuristic-designer/SKILL.md) — Apply brand guidelines to futuristic UI design systems
