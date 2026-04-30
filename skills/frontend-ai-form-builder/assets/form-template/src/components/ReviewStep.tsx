import React, { Fragment } from 'react';
import { z } from 'zod';
import { StepDefinition, StepProps } from '../hooks/useFormWizard';

interface ReviewStepProps extends StepProps {
  goTo: (index: number) => void;
  steps: StepDefinition[];  // content steps only (pass all steps; review filters itself)
}

export function ReviewStep({ formData, goTo, steps }: ReviewStepProps) {
  // Exclude the review step itself from the summary
  const contentSteps = steps.filter(s => s.id !== 'review');

  return (
    <div>
      <p style={{ color: '#6b7280', marginBottom: 24 }}>
        Review your answers below. Click <strong>Edit</strong> to update any section.
      </p>

      {contentSteps.map((step, i) => {
        const shape = (step.schema as z.ZodObject<z.ZodRawShape>).shape ?? {};
        const keys = Object.keys(shape);

        return (
          <div key={step.id} style={{
            border: '1px solid #e5e7eb', borderRadius: 8,
            padding: 16, marginBottom: 16,
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', marginBottom: 12,
            }}>
              <strong style={{ fontSize: 15 }}>{step.title}</strong>
              <button
                onClick={() => goTo(i)}
                style={{
                  color: '#6366f1', background: 'none',
                  border: 'none', cursor: 'pointer', fontSize: 13,
                }}
              >
                Edit
              </button>
            </div>

            <dl style={{
              display: 'grid', gridTemplateColumns: '140px 1fr',
              gap: '6px 16px', margin: 0,
            }}>
              {keys.map(key => (
                <Fragment key={key}>
                  <dt style={{ color: '#9ca3af', fontSize: 13, textTransform: 'capitalize' }}>
                    {key.replace(/_/g, ' ')}
                  </dt>
                  <dd style={{ margin: 0, fontSize: 14, wordBreak: 'break-word' }}>
                    {formData[key] != null && formData[key] !== '' ? String(formData[key]) : '—'}
                  </dd>
                </Fragment>
              ))}
            </dl>
          </div>
        );
      })}
    </div>
  );
}
