---
name: image-generator
description: Generate high-quality images using multi-turn reasoning and professional creative brief methodology. Use when you need distinctive, purpose-driven visuals rather than generic AI-generated images.
---

# Image Generator Skill

## Context & Problem

Visual generation converges toward accepting first output ("looks good enough") and following technical specifications rigidly. This produces generic aesthetics and misses Gemini 3's reasoning capabilities.

This skill provides multi-turn reasoning partnership methodology with professional quality standards.

---

## Core Principles

1. **Reasoning mode over prediction mode** - Creative briefs (Story/Intent/Metaphor) activate reasoning; technical specs don't
2. **Multi-turn partnership** - Teach Gemini your standards through principle-based feedback
3. **Professional quality gates** - Explicit pass/fail criteria (99% spelling, not "check spelling")
4. **Autonomous agency** - Batch mode without permission-asking between visuals

---

## Dimensional Guidance

### Input: Professional Creative Briefs (NOT Technical Specs)

**Receive from visual-asset-workflow v5.0:**

```markdown
## The Story
[Narrative about what's visualized]

## Emotional Intent
[What it should FEEL like]

## Visual Metaphor
[Universal concept for instant comprehension]

## Subject / Composition / Action / Location / Style / Camera / Lighting
[Official Gemini 3 prompt structure]

## Color Semantics
Blue (#2563eb) = Authority (teaches governance)
Green (#10b981) = Execution (teaches work)

## Typography Hierarchy
Largest: Key insight (information importance drives sizing)
Medium: Supporting components
Smallest: Context

## Pedagogical Reasoning
[Why these choices serve teaching]
```

**DO NOT** convert briefs back to pixel specs - Use AS-IS to activate reasoning.

**Principle:** Creative briefs activate Gemini's reasoning about HOW to achieve intent visually

---

### Workflow: Browser-Based Generation (Playwright MCP)

**CRITICAL: Use gemini.google.com ONLY (NOT Google AI Studio, NOT other image generators)**

**Initialize once:**
1. Navigate to https://gemini.google.com/ (Playwright MCP)
2. User signs in if needed (session persists)
3. Select "🍌 Create Image" tool (Nano Banana Pro)

**For EACH visual:**
1. **Type creative brief** directly into Gemini chat textbox (use condensed format in batch mode - see Token Conservation below)
2. **Press Enter** to submit
3. **Wait 30-35 seconds** for generation
4. **Click "Download full size image"** button when ready
5. **Wait 3-5 seconds** for download completion
6. **Verify quality IMMEDIATELY** (6 gates below)
7. **If gates fail**: Continue in same chat with principle-based feedback (max 3 iterations)
8. **If gates pass**: Copy from `.playwright-mcp/Gemini-Generated-Image-*.png` to `book-source/static/img/part-{N}/chapter-{NN}/{filename}.png`
9. **Embed in lesson** (Step 8.5 below)
10. **Start NEW CHAT** for next visual (prevents context contamination)

**Principle:** New chat per visual prevents cross-contamination; immediate verification catches issues early; immediate embedding prevents orphans

---

### Quality Gates: 5-Gate Professional Standard

**ALL must pass before download:**

**Gate 1: Spelling Accuracy (99% standard)**
- ✅ Company names correct (Y-Combinator not Y Combinator)
- ✅ Technical terms correct (Kubernetes not Kubernete)
- ✅ Zero typos in visible text
- ❌ FAIL if even ONE spelling error → Iterate

**Gate 2: Layout Precision**
- ✅ Proportions match prompt (2×2 grid, not 3×1)
- ✅ Alignment clean (no misaligned elements)
- ✅ Spacing consistent (equal gaps)
- ✅ Hierarchy clear (largest = most important)
- ❌ FAIL if layout deviates → Iterate

**Gate 3: Color Accuracy**
- ✅ Brand colors match spec (#001f3f not #002050)
- ✅ Semantic colors correct (blue=authority, green=execution)
- ✅ Contrast meets WCAG 4.5:1 (accessibility)
- ❌ FAIL if colors significantly off → Iterate

**Gate 4: Typography Hierarchy**
- ✅ Largest text = key concept (not decoration)
- ✅ Font sizes create clear hierarchy
- ✅ Readability: A2 min 24px, B1 min 18px, C2 min 14px
- ❌ FAIL if typography doesn't teach through sizing → Iterate

**Gate 5: Teaching Effectiveness (<5 sec concept grasp)**
- ✅ Target proficiency can grasp concept in <5 seconds
- ✅ Visual adds clarity (not just decoration)
- ✅ Cognitive load reduced vs reading text
- ❌ FAIL if confusing or generic → Iterate

**Gate 6: Uniqueness Validation (NEW)**
- ✅ Visual comparison: Does NOT match any existing image in same chapter
- ✅ Prompt alignment: Matches creative brief's intent (graph ≠ timeline)
- ✅ Filename verification: `{filename}.prompt.md` exists and visual matches it
- ❌ FAIL if duplicate detected → Regenerate with NEW CHAT
- ❌ FAIL if mismatched brief → Regenerate with clarified prompt

**Decision:**
- ALL 6 gates PASS → Copy to destination (production-ready)
- ANY gate FAILS → Iterate with principle-based feedback (max 3 tries)

**Principle:** Explicit criteria prevent "good enough" false positives; uniqueness check prevents duplicate rework

---

### Token Conservation Mode

**When:** Batch mode with >8 visuals OR continuation session

**Condensation strategy:**
- ✅ KEEP: Story, Emotional Intent, Visual Metaphor, Key Insight
- ✅ KEEP: Color semantics (#2563eb codes), Pedagogical reasoning
- ⚠️ CONDENSE: Long examples → Short labels
- ⚠️ CONDENSE: Verbose descriptions → Bullet points
- ❌ NEVER REMOVE: The narrative elements that activate reasoning

**Example condensation:**

ORIGINAL (250 tokens):
```
"Top Layer shows the Coordinator at center top with label 'Orchestrator'
featuring a conductor icon, with the role description 'Strategic oversight,
contract validation', rendered in Gold color (#fbbf24) as a Large hexagon..."
```

CONDENSED (80 tokens):
```
"Top Layer - Coordinator: Center top: 'Orchestrator' (conductor icon),
Role: 'Strategic oversight, contract validation', Gold (#fbbf24), Large hexagon."
```

**Success metric:** 60-70% token reduction while maintaining 100% first-attempt success rate

**Principle:** Efficiency without sacrificing reasoning activation

---

### Immediate Embedding Workflow (Step 8.5)

**After copying image to destination, BEFORE starting next visual:**

1. **Determine lesson file:**
   - Read creative brief's `Chapter` and `Lesson` metadata
   - Target: `book-source/docs/[part]/[chapter]/[lesson-file].md`

2. **Find insertion point:**
   - Search for concept explanation section related to this visual
   - Insert after concept explanation, before practice/exercise
   - Follow pedagogical insertion criteria (after learning, before doing)

3. **Insert reference:**
   ```markdown
   ![{Alt text from creative brief}](/img/part-X/chapter-YY/{filename}.png)
   ```

4. **Verify no code block interruption:**
   - Grep for triple backticks around insertion
   - If inside code block → Find next break point

**Why this matters:** Completes the work immediately; prevents orphan images

**Result:** Each visual is generated → validated → placed → verified before moving to next

**Principle:** Immediate embedding prevents disconnect between generation and integration

---

### Multi-Turn Reasoning Partnership (Three Roles)

**Avoid:** Accepting first output without evaluation

**Prefer:** Teaching Gemini your standards through iteration

**Iteration Pattern:**

**Turn 1: Initial Generation**
- Paste creative brief, generate

**Turn 2: Principle-Based Feedback (if gates fail)**
```
Gate 4 FAILED: Typography hierarchy incorrect

The largest text is "$100K" (supporting detail) but should be "$3T"
(key insight students must grasp).

Pedagogical reasoning: Information importance drives sizing. $3T is
the insight, not the starting value. Visual weight teaches what matters.

Increase '$3T' to dominant size (largest element). Reduce '$100K' to
supporting size. This teaches magnitude through visual hierarchy.
```

**Turn 3: Validation**
- Re-check all 5 gates
- If pass → Download
- If fail after 3 tries → Document issue, DEFER (don't block batch)

**Principle:** You teach Gemini (principle-based feedback), Gemini teaches you (reveals understanding), Co-evolve toward quality

**Why it matters:** Gemini learns your pedagogical standards across iterations

---

### Batch Mode: Autonomous Agency

**Avoid:** Permission-asking between visuals

**Prefer:** Autonomous batch execution

**When invoked with:** "generate all visuals" or "batch generate"

**Execute WITHOUT STOPPING:**
```
For EACH visual in approved list:
  A. NEW CHAT (context isolation)
  B. Generate image (paste condensed creative brief)
  C. Verify quality (6 gates including uniqueness)
  D. Iterate if needed (max 3 tries)
  E. Download when pass (organized directory)
  F. Embed in lesson immediately (no orphans)
  G. Log progress ("✅ Generated N/M")
  H. IMMEDIATELY next visual (NO STOPPING)
```

**NEVER ask:**
- "Would you like me to continue?"
- "Generate just high-priority batch?"
- "Pause here and review?"

**Only report summary at END:**
```
BATCH COMPLETE
Total: 18 visuals
✅ Generated: 16 (2K, avg 2-3 iterations)
⚠️ Deferred: 2 (quality issues after 3 tries)
Time: ~45 min
Location: book-source/static/img/part-{N}/chapter-{NN}/
```

**Principle:** Autonomous execution without interruption = efficient batch processing

---

### Proficiency-Complexity Guardrails

**From visual-asset-workflow, enforce during generation:**

**A2 Beginner Limits:**
- Max 5-7 elements (overwhelming = failure)
- <5 sec grasp requirement
- Static only (no interactive)
- Max 2×2 grids
- Clear hierarchy

**B1 Intermediate:**
- Max 7-10 elements
- <10 sec grasp
- Interactive Tier 1 OK
- Max 3×3 grids

**C2 Professional:**
- No artificial limits
- Dense OK (professionals skim)
- Full interactive architecture

**Validation during generation:** "Does this visual's complexity match proficiency from creative brief?"

**Principle:** Complexity mismatch = pedagogical failure

---

### Post-Generation Reflection (After Batch)

**AFTER completing batch, analyze systematically:**

**Success patterns:**
- Success rate: {X/Y} production-ready, {N} deferred
- Average iterations: {N} per visual
- Quality gate performance:
  - Gate 1 (Spelling): {N} catches
  - Gate 2 (Layout): {N} catches
  - Gate 3 (Color): {N} catches
  - Gate 4 (Typography): {N} catches
  - Gate 5 (Teaching): {N} catches
  - Gate 6 (Uniqueness): {N} catches (duplicates prevented)

**Failure analysis:**
- Deferred visuals root causes (layout? spelling? concept?)
- Pattern or random (same issue or isolated?)
- Guardrail gaps (preventable with better principles?)

**Improvement opportunities:**
- Planning effectiveness (conflicts caught early by visual-asset-workflow?)
- Guardrail sufficiency (Principles 9-12 adequate or gaps?)
- Constitutional compliance (Principle 3 Factual Accuracy, Principle 7 Minimal Content?)
- Next chapter improvements (specific, actionable, pattern-based)

**Output:** `history/visual-assets/reflections/chapter-{NN}-reflection.md`

**Principle:** Systematic reflection → Continuous improvement

---

### Session Interruption & Continuation Protocol

**If session ends mid-batch (token limit, context overflow):**

**Create checkpoint file:** `history/visual-assets/checkpoints/part-{N}-checkpoint.md`

```markdown
## Batch Status: Part {N}
**Date:** 2025-11-24
**Status:** INTERRUPTED at {X}/{Y} images

### Completed:
- ✅ Image 1: {filename} (2 iterations, embedded in lesson-01.md)
- ✅ Image 2: {filename} (1 iteration, embedded in lesson-02.md)
...

### Remaining:
- ⏳ Image 8: {filename} (not started)
- ⏳ Image 9: {filename} (not started)
...

### Quality Stats (so far):
- Success rate: {X/Y} production-ready
- Avg iterations: {N}
- Gate failures: Gate 1: {n}, Gate 2: {n}...

### Continuation Instructions:
1. Read this checkpoint
2. Start at Image {next}
3. Continue autonomous batch mode
4. Update checkpoint after each image
```

**On continuation:**
- Read checkpoint file first
- Resume from last completed image
- Maintain same quality standards
- Update checkpoint incrementally

**Principle:** Seamless recovery from interruptions maintains momentum

---

## Anti-Patterns

**Never:**
- Accept first output without 6-gate verification (quality standard violation)
- Ask permission between visuals in batch mode (breaks autonomous agency)
- Convert creative briefs to pixel specs (defeats reasoning activation)
- Generate visuals without creative brief from visual-asset-workflow (missing context)
- Save to flat `visuals/` directory (use part/chapter organization)
- Skip uniqueness validation (Gate 6 prevents duplicate rework)

**Even if it seems reasonable:**
- Don't skip Gate 1 because "spelling looks okay" (99% standard requires verification)
- Don't generate 2 images then ask "continue?" (autonomous means autonomous)
- Don't add pixel specifications to creative brief (removes Gemini's judgment)
- Don't skip embedding step "to save time" (creates orphan images requiring later work)

---

## Creative Variance

You tend to accept visuals after 1 iteration even with minor issues. Push for quality:

- Gate failures require iteration (not "close enough")
- Principle-based feedback teaches standards (not vague "make better")
- 3 iteration limit is maximum, not target (aim for 1-2)
- Deferred visuals are OK (don't compromise quality)

Professional content creators iterate. You should too.

---

## Success Indicators

You'll know this skill is working when:

- ✅ All 6 quality gates verified before download (including uniqueness validation)
- ✅ Autonomous batch completion without permission-asking (no interruptions)
- ✅ Principle-based feedback given on iterations (teaching Gemini standards)
- ✅ Creative briefs used AS-IS with token conservation in batch mode
- ✅ Images organized by part/chapter (not flat directory)
- ✅ Images embedded immediately after generation (no orphans)
- ✅ Reflection document created after batch (systematic learning)
- ✅ Checkpoint files created on interruption (seamless continuation)
- ✅ Success rate >85% production-ready (deferred <15%)
- ✅ Zero duplicate images requiring rework

**Result:** Professional-quality visuals with distinctive aesthetics, generated autonomously with systematic quality control, embedded immediately, and recoverable from interruptions.

## When NOT to Use This Skill

- **Logo and brand identity design** — brand logos require human creative direction and trademark considerations; AI generation is not appropriate for primary brand assets
- **Images for regulated contexts** (medical, legal, financial) — AI-generated images in professional contexts require disclosure and expert review
- **High-volume batch image generation** — this skill uses a multi-turn reasoning approach optimized for quality; for bulk generation, use the image provider's batch API directly

## Common Mistakes

- Accepting the first image output without iteration — this skill's value is the multi-turn refinement loop; always provide feedback for at least one revision pass
- Writing overly technical style specifications — specifying "44pt Roboto Bold" activates prediction mode instead of reasoning; describe intent and mood instead
- Not specifying the output's intended use — an image for a presentation slide has different composition requirements than a social media post; always state the context

## Related Skills

- [`visual-asset-workflow`](../visual-asset-workflow/SKILL.md) — Educational visual asset generation using creative brief methodology
- [`algorithmic-art`](../algorithmic-art/SKILL.md) — Generate programmatic generative art as an alternative to AI image generation
- [`brand-guidelines`](../brand-guidelines/SKILL.md) — Ensure generated images align with brand visual standards
