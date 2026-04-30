---
name: frontend-ai-form-builder
description: "Build multi-step forms with validation, state handling, and AI API integration. Use when the user needs to: (1) build a multi-step wizard form with step navigation and per-step Zod validation, (2) manage form state across steps with a custom hook, (3) call an LLM API (OpenAI or Anthropic) from a React frontend with loading and error states, (4) render structured AI-generated output with section formatting, (5) export the result as a print-ready PDF using jsPDF or html2canvas. Triggers on keywords like: multi-step form, form wizard, step navigation, AI form, PDF export, jsPDF, html2canvas, review step, print-ready, structured output, form validation."
---

# Frontend AI Form Builder

Build wizard forms that collect structured input, send it to an AI API, and produce a print-ready output.

## Build Workflow

```
1. Define step definitions (title, fields, Zod schema per step)
2. Implement useFormWizard hook (currentStep, formData, next/back/goTo)
3. Build per-step field components with validation on Next click
4. Add Review step (always second-to-last) — shows all answers, allows editing
5. On Submit: call AI API, show loading state, render structured response
6. Wire PDF export button on the result panel
```

**Constraints — enforce always:**
- Review step is always the penultimate step (before submit/loading)
- PDF output must use print-safe fonts, no transparent backgrounds, white base

---

## Boilerplate Template

A complete starter scaffold is in `assets/form-template/`. Files included:

```
form-template/src/
├── components/
│   ├── FormWizard.tsx       Step navigator, progress bar, step renderer
│   ├── ReviewStep.tsx       Summary of all answers + Edit links
│   └── AIResultPanel.tsx    Structured AI output + Export PDF button
├── hooks/
│   ├── useFormWizard.ts     Step state machine (currentStep, formData, validation)
│   └── useAIGenerate.ts     API call hook (loading, error, result, streaming)
├── lib/
│   └── exportPdf.ts         html2canvas + jsPDF export utility
└── styles/
    └── print.css            Print-ready CSS (page breaks, margins, fonts)
```

---

## 1. Step Architecture

```ts
interface StepDefinition {
  id: string;
  title: string;
  schema: z.ZodTypeAny;          // validates this step's fields
  component: React.ComponentType<StepProps>;
}

// Steps array — review is always second-to-last
const STEPS: StepDefinition[] = [
  { id: 'basics',    title: 'Basic Info',  schema: BasicsSchema,    component: BasicsStep },
  { id: 'details',   title: 'Details',     schema: DetailsSchema,   component: DetailsStep },
  { id: 'review',    title: 'Review',      schema: z.object({}),    component: ReviewStep },
  // Submit/loading is handled by FormWizard, not a step
];
```

---

## 2. Step State Hook

```ts
// Minimal contract from useFormWizard
const {
  currentStep,      // 0-based index
  totalSteps,
  stepDef,          // current StepDefinition
  formData,         // accumulated data across all steps
  errors,           // validation errors for current step
  next,             // validates current step, advances if valid
  back,             // go to previous step
  goTo,             // jump to specific step (for Review → Edit)
  setField,         // update a single field in formData
  isFirst, isLast,  // convenience booleans
} = useFormWizard(STEPS, initialData);
```

See `assets/form-template/src/hooks/useFormWizard.ts` for full implementation.

---

## 3. AI API Call Pattern

```ts
const { generate, result, isLoading, error, reset } = useAIGenerate();

// In submit handler
await generate({
  prompt: buildPrompt(formData),
  model: 'gpt-4o-mini',          // or claude-haiku-4-5
});
```

**Prompt construction from form data:**
```ts
function buildPrompt(data: FormData): string {
  return `Based on the following information, generate a structured report:

Name: ${data.name}
Industry: ${data.industry}
Goals: ${data.goals}

Return a JSON object with sections: { summary, recommendations, nextSteps }`;
}
```

For streaming support and Anthropic variant, see [references/ai-integration.md](references/ai-integration.md).

---

## 4. PDF Export Pattern

```ts
import { exportToPdf } from '../lib/exportPdf';

// Attach to the result panel's Export button
<button onClick={() => exportToPdf('ai-result-panel', 'report.pdf')}>
  Export PDF
</button>
```

The `exportToPdf` utility targets a DOM element by ID, captures it with html2canvas, and writes it to a jsPDF page. The element must have `id="ai-result-panel"` and must be visible in the DOM (not hidden).

For print CSS and jsPDF direct-write alternative, see [references/pdf-export.md](references/pdf-export.md).

---

## Resources

- [references/form-state.md](references/form-state.md) — Full useFormWizard hook, per-step validation, Review step edit pattern
- [references/ai-integration.md](references/ai-integration.md) — API call hook, streaming, structured JSON parsing, error handling
- [references/pdf-export.md](references/pdf-export.md) — html2canvas + jsPDF, print CSS, multi-page handling, print-ready rules
- `assets/form-template/` — Complete boilerplate to copy and adapt
