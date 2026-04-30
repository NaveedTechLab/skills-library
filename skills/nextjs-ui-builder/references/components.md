# Component Patterns

## Table of Contents
1. [Component Structure](#component-structure)
2. [Common UI Components](#common-ui-components)
3. [Form Patterns](#form-patterns)
4. [Loading & Error States](#loading--error-states)

---

## Component Structure

### File Organization

```
src/
├── app/                    # App Router pages
│   ├── layout.tsx
│   ├── page.tsx
│   ├── loading.tsx
│   ├── error.tsx
│   └── (routes)/
├── components/
│   ├── ui/                 # Reusable UI primitives
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   └── Card.tsx
│   ├── forms/              # Form components
│   └── layout/             # Layout components
│       ├── Header.tsx
│       ├── Footer.tsx
│       └── Sidebar.tsx
├── hooks/                  # Custom hooks
├── lib/                    # Utilities
│   ├── api.ts
│   └── utils.ts
└── types/                  # TypeScript types
```

### Component Template

```tsx
// components/ui/Button.tsx
interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  loading?: boolean;
}

export function Button({
  children,
  onClick,
  variant = 'primary',
  disabled = false,
  loading = false,
}: ButtonProps) {
  const baseStyles = 'px-4 py-2 rounded font-medium transition-colors';
  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`${baseStyles} ${variants[variant]} ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      }`}
    >
      {loading ? 'Loading...' : children}
    </button>
  );
}
```

---

## Common UI Components

### Card

```tsx
interface CardProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
}

export function Card({ children, title, className = '' }: CardProps) {
  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
      {children}
    </div>
  );
}
```

### Input

```tsx
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, className = '', ...props }: InputProps) {
  return (
    <div className="space-y-1">
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <input
        className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
          error ? 'border-red-500' : 'border-gray-300'
        } ${className}`}
        {...props}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
```

### Modal

```tsx
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export function Modal({ isOpen, onClose, title, children }: ModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">{title}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
```

### Empty State

```tsx
interface EmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="text-center py-12">
      <h3 className="text-lg font-medium text-gray-900">{title}</h3>
      {description && (
        <p className="mt-2 text-sm text-gray-500">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
```

---

## Form Patterns

### Controlled Form with Validation

```tsx
'use client';

import { useState } from 'react';

interface FormData {
  title: string;
  description: string;
}

interface FormErrors {
  title?: string;
  description?: string;
}

export function TodoForm({ onSubmit }: { onSubmit: (data: FormData) => void }) {
  const [formData, setFormData] = useState<FormData>({ title: '', description: '' });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = (): boolean => {
    const newErrors: FormErrors = {};
    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await onSubmit(formData);
      setFormData({ title: '', description: '' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label="Title"
        value={formData.title}
        onChange={(e) => setFormData({ ...formData, title: e.target.value })}
        error={errors.title}
      />
      <Input
        label="Description"
        value={formData.description}
        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
        error={errors.description}
      />
      <Button type="submit" loading={isSubmitting}>
        Create Todo
      </Button>
    </form>
  );
}
```

### Form with Server Action (App Router)

```tsx
// app/actions.ts
'use server';

import { revalidatePath } from 'next/cache';

export async function createTodo(formData: FormData) {
  const title = formData.get('title') as string;

  const res = await fetch(`${process.env.API_URL}/todos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });

  if (!res.ok) throw new Error('Failed to create todo');

  revalidatePath('/todos');
}

// components/forms/TodoForm.tsx
import { createTodo } from '@/app/actions';

export function TodoForm() {
  return (
    <form action={createTodo} className="space-y-4">
      <Input name="title" label="Title" required />
      <Button type="submit">Create</Button>
    </form>
  );
}
```

---

## Loading & Error States

### Loading Skeleton

```tsx
export function TodoSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-gray-200 h-16 rounded-lg" />
      ))}
    </div>
  );
}
```

### Page-Level Loading (App Router)

```tsx
// app/todos/loading.tsx
export default function Loading() {
  return (
    <div className="space-y-4">
      <div className="h-8 w-48 bg-gray-200 rounded animate-pulse" />
      <TodoSkeleton />
    </div>
  );
}
```

### Error Boundary

```tsx
// app/todos/error.tsx
'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="text-center py-12">
      <h2 className="text-xl font-semibold text-red-600">Something went wrong</h2>
      <p className="mt-2 text-gray-600">{error.message}</p>
      <button
        onClick={reset}
        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Try again
      </button>
    </div>
  );
}
```

### Inline Error Display

```tsx
interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <p className="text-red-800">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
        >
          Try again
        </button>
      )}
    </div>
  );
}
```
