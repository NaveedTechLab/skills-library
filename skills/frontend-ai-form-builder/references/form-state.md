# Form State Reference

## Table of Contents
1. [useFormWizard Hook](#1-useformwizard-hook)
2. [Per-Step Zod Validation](#2-per-step-zod-validation)
3. [Review Step Pattern](#3-review-step-pattern)
4. [Step Progress Indicator](#4-step-progress-indicator)
5. [Preserving State on Back Navigation](#5-preserving-state-on-back-navigation)

---

## 1. useFormWizard Hook

```ts
// hooks/useFormWizard.ts
import { useState, useCallback } from 'react';
import { z } from 'zod';

export interface StepDefinition {
  id: string;
  title: string;
  schema: z.ZodTypeAny;
  component: React.ComponentType<StepProps>;
}

export interface StepProps {
  formData: Record<string, unknown>;
  errors: Record<string, string>;
  setField: (key: string, value: unknown) => void;
}

export function useFormWizard(steps: StepDefinition[], initial: Record<string, unknown> = {}) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<Record<string, unknown>>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const setField = useCallback((key: string, value: unknown) => {
    setFormData(prev => ({ ...prev, [key]: value }));
    setErrors(prev => { const n = { ...prev }; delete n[key]; return n; });
  }, []);

  const validate = useCallback((): boolean => {
    const schema = steps[currentStep]?.schema;
    if (!schema) return true;
    const result = schema.safeParse(formData);
    if (result.success) { setErrors({}); return true; }
    const flat = result.error.flatten().fieldErrors;
    setErrors(Object.fromEntries(
      Object.entries(flat).map(([k, v]) => [k, (v as string[])[0] ?? 'Invalid'])
    ));
    return false;
  }, [currentStep, formData, steps]);

  const next = useCallback(() => {
    if (validate()) setCurrentStep(s => Math.min(s + 1, steps.length - 1));
  }, [validate, steps.length]);

  const back = useCallback(() => {
    setErrors({});
    setCurrentStep(s => Math.max(s - 1, 0));
  }, []);

  const goTo = useCallback((index: number) => {
    setErrors({});
    setCurrentStep(Math.max(0, Math.min(index, steps.length - 1)));
  }, [steps.length]);

  return {
    currentStep,
    totalSteps: steps.length,
    stepDef: steps[currentStep],
    formData,
    errors,
    next,
    back,
    goTo,
    setField,
    isFirst: currentStep === 0,
    isLast: currentStep === steps.length - 1,
    isReview: steps[currentStep]?.id === 'review',
  };
}
```

---

## 2. Per-Step Zod Validation

Define one schema per content step. The review step uses an empty schema (no validation needed — data was already validated).

```ts
// schemas/formSchemas.ts
import { z } from 'zod';

export const BasicsSchema = z.object({
  name:     z.string().min(1, 'Name is required').max(100),
  email:    z.string().email('Invalid email address'),
  company:  z.string().min(1, 'Company is required'),
});

export const DetailsSchema = z.object({
  industry: z.string().min(1, 'Select an industry'),
  goals:    z.string().min(10, 'Describe your goals (min 10 chars)').max(1000),
  budget:   z.coerce.number({ invalid_type_error: 'Enter a number' }).positive('Must be positive'),
});

// Review step — pass-through (data already validated per step)
export const ReviewSchema = z.object({}).passthrough();
```

**Field error display pattern:**
```tsx
function FieldError({ errors, name }: { errors: Record<string, string>; name: string }) {
  return errors[name]
    ? <p style={{ color: '#dc2626', fontSize: 12, marginTop: 4 }}>{errors[name]}</p>
    : null;
}
```

---

## 3. Review Step Pattern

The Review step shows all accumulated `formData` grouped by their originating step. Each group has an Edit button that calls `goTo(stepIndex)`.

```tsx
// components/ReviewStep.tsx
interface ReviewStepProps {
  formData: Record<string, unknown>;
  steps: StepDefinition[];          // content steps only (exclude review + final)
  goTo: (index: number) => void;
}

export function ReviewStep({ formData, steps, goTo }: ReviewStepProps) {
  return (
    <div>
      <h2>Review Your Answers</h2>
      <p style={{ color: '#6b7280', marginBottom: 24 }}>
        Check your answers below. Click Edit to change a section.
      </p>

      {steps.map((step, i) => (
        <div key={step.id} style={{
          border: '1px solid #e5e7eb', borderRadius: 8,
          padding: 16, marginBottom: 16,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <strong>{step.title}</strong>
            <button onClick={() => goTo(i)} style={{ color: '#6366f1', background: 'none', border: 'none', cursor: 'pointer', fontSize: 14 }}>
              Edit
            </button>
          </div>
          <ReviewFields schema={step.schema} formData={formData} />
        </div>
      ))}
    </div>
  );
}

function ReviewFields({ schema, formData }: { schema: z.ZodTypeAny; formData: Record<string, unknown> }) {
  const keys = Object.keys((schema as z.ZodObject<any>).shape ?? {});
  return (
    <dl style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '8px 16px' }}>
      {keys.map(key => (
        <Fragment key={key}>
          <dt style={{ color: '#9ca3af', fontSize: 13, textTransform: 'capitalize' }}>
            {key.replace(/_/g, ' ')}
          </dt>
          <dd style={{ margin: 0, fontSize: 14 }}>
            {String(formData[key] ?? '—')}
          </dd>
        </Fragment>
      ))}
    </dl>
  );
}
```

---

## 4. Step Progress Indicator

```tsx
function StepProgress({ currentStep, steps }: { currentStep: number; steps: StepDefinition[] }) {
  return (
    <div style={{ display: 'flex', gap: 8, marginBottom: 32 }}>
      {steps.map((step, i) => (
        <div key={step.id} style={{ flex: 1 }}>
          <div style={{
            height: 4, borderRadius: 2,
            background: i <= currentStep ? '#6366f1' : '#e5e7eb',
            transition: 'background 0.2s',
          }} />
          <div style={{ fontSize: 11, color: i <= currentStep ? '#6366f1' : '#9ca3af', marginTop: 4 }}>
            {step.title}
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## 5. Preserving State on Back Navigation

`useFormWizard` preserves `formData` across all steps. When the user goes Back and changes a field, the updated value persists because `setField` merges into the shared `formData` object.

**Edge case — dependent fields:** If step 2 fields depend on step 1 choices (e.g., industry changes available goal options), clear the dependent fields when the parent changes:

```ts
function handleIndustryChange(value: string) {
  setField('industry', value);
  setField('goals', '');  // clear dependent field
}
```
