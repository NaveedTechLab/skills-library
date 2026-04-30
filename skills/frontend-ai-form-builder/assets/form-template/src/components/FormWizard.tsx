import React from 'react';
import { useFormWizard, StepDefinition } from '../hooks/useFormWizard';

interface FormWizardProps {
  steps: StepDefinition[];
  initialData?: Record<string, unknown>;
  onSubmit: (formData: Record<string, unknown>) => void;
  isSubmitting?: boolean;
}

export function FormWizard({ steps, initialData, onSubmit, isSubmitting }: FormWizardProps) {
  const wizard = useFormWizard(steps, initialData);
  const { stepDef, currentStep, formData, errors, next, back, goTo, setField, isFirst, isLast, isReview } = wizard;

  if (!stepDef) return null;

  const StepComponent = stepDef.component;

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: '24px 16px' }}>
      {/* Progress bar */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 32 }}>
        {steps.map((s, i) => (
          <div key={s.id} style={{ flex: 1 }}>
            <div style={{
              height: 4, borderRadius: 2,
              background: i <= currentStep ? '#6366f1' : '#e5e7eb',
              transition: 'background 0.2s',
            }} />
            <div style={{ fontSize: 11, marginTop: 4, color: i <= currentStep ? '#6366f1' : '#9ca3af' }}>
              {s.title}
            </div>
          </div>
        ))}
      </div>

      {/* Step title */}
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>{stepDef.title}</h2>

      {/* Step content */}
      <StepComponent formData={formData} errors={errors} setField={setField} goTo={goTo} steps={steps} />

      {/* Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 32 }}>
        <button
          onClick={back}
          disabled={isFirst}
          style={{
            padding: '10px 24px', borderRadius: 6,
            border: '1px solid #d1d5db', background: '#fff',
            cursor: isFirst ? 'not-allowed' : 'pointer',
            opacity: isFirst ? 0.4 : 1,
          }}
        >
          Back
        </button>

        {isLast ? (
          <button
            onClick={() => onSubmit(formData)}
            disabled={isSubmitting}
            style={{
              padding: '10px 24px', borderRadius: 6,
              background: '#6366f1', color: '#fff', border: 'none',
              cursor: isSubmitting ? 'wait' : 'pointer',
              opacity: isSubmitting ? 0.7 : 1,
            }}
          >
            {isSubmitting ? 'Generating...' : 'Generate Report'}
          </button>
        ) : (
          <button
            onClick={next}
            style={{
              padding: '10px 24px', borderRadius: 6,
              background: '#6366f1', color: '#fff', border: 'none', cursor: 'pointer',
            }}
          >
            {isReview ? 'Confirm & Submit' : 'Next'}
          </button>
        )}
      </div>
    </div>
  );
}
