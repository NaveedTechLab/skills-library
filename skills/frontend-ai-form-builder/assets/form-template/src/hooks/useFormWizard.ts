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
  const [formData, setFormData]       = useState<Record<string, unknown>>(initial);
  const [errors, setErrors]           = useState<Record<string, string>>({});

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
    isFirst:  currentStep === 0,
    isLast:   currentStep === steps.length - 1,
    isReview: steps[currentStep]?.id === 'review',
  };
}
