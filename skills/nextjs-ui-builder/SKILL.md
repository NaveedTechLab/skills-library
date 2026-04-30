---
name: nextjs-ui-builder
description: Build clean, simple Next.js user interfaces optimized for hackathons and rapid prototyping. Use when creating frontend UIs, React pages, components, API integration, auth-aware layouts, or demo-ready web applications. Prioritizes simplicity, fast loading, and working demos over visual polish.
---

# Next.js UI Builder

Build hackathon-ready Next.js frontends with minimal setup. Focus on working demos, not pixel-perfect designs.

## Quick Start

Copy the template to start a new project:

```bash
cp -r assets/template/ ./frontend
cd frontend
npm install
npm run dev
```

## Hackathon Principles

1. **Simplicity over beauty** - Use Tailwind defaults, avoid custom designs
2. **Fast loading** - Minimize client-side JS, prefer Server Components
3. **Demo-ready** - Focus on core flows, skip edge cases
4. **Copy-paste friendly** - Reusable patterns, not abstractions

## Project Structure

```
src/
├── app/                    # Pages (App Router)
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Home page
│   ├── loading.tsx         # Loading state
│   └── error.tsx           # Error boundary
├── components/
│   ├── ui/                 # Button, Input, Card
│   └── layout/             # Header, Footer
├── lib/
│   └── api.ts              # API client
└── hooks/                  # Custom hooks
```

## Adding a Page

### Server Component (Default)

```tsx
// app/todos/page.tsx
import { api } from '@/lib/api';

export default async function TodosPage() {
  const { items } = await api.get<{ items: Todo[] }>('/todos');

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Todos</h1>
      <ul className="space-y-2">
        {items.map((todo) => (
          <li key={todo.id} className="p-4 bg-white rounded shadow">
            {todo.title}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Client Component (Interactive)

```tsx
// components/TodoForm.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

export function TodoForm({ onSubmit }: { onSubmit: (title: string) => void }) {
  const [title, setTitle] = useState('');

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(title); setTitle(''); }}>
      <div className="flex gap-2">
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="New todo..."
        />
        <Button type="submit">Add</Button>
      </div>
    </form>
  );
}
```

## UI Components (Included)

### Button
```tsx
<Button variant="primary">Save</Button>
<Button variant="secondary">Cancel</Button>
<Button variant="danger" loading={isDeleting}>Delete</Button>
```

### Input
```tsx
<Input label="Email" type="email" error={errors.email} />
```

### Card
```tsx
<Card title="Settings">
  <p>Card content here</p>
</Card>
```

## API Integration

### Fetching Data

```tsx
// Server Component - recommended for lists
const data = await api.get<{ items: Todo[] }>('/todos');

// Client Component - for mutations
const res = await api.post<Todo>('/todos', { title: 'New todo' });
await api.delete(`/todos/${id}`);
```

### With Authentication

```tsx
const token = localStorage.getItem('token');
const data = await api.get('/todos', {
  headers: { Authorization: `Bearer ${token}` },
});
```

## Common Patterns

### List with CRUD

```tsx
// app/todos/page.tsx
import { api } from '@/lib/api';
import { TodoList } from './TodoList';

export default async function TodosPage() {
  const { items } = await api.get<{ items: Todo[] }>('/todos');
  return <TodoList initialTodos={items} />;
}

// app/todos/TodoList.tsx
'use client';
export function TodoList({ initialTodos }: { initialTodos: Todo[] }) {
  const [todos, setTodos] = useState(initialTodos);
  // ... CRUD operations
}
```

### Loading State

```tsx
// app/todos/loading.tsx
export default function Loading() {
  return <div className="animate-pulse bg-gray-200 h-32 rounded" />;
}
```

### Error State

```tsx
// app/todos/error.tsx
'use client';
export default function Error({ error, reset }) {
  return (
    <div className="text-center py-8">
      <p className="text-red-600">{error.message}</p>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
```

## Demo Tips

1. **Seed data** - Pre-populate with realistic examples
2. **Happy path first** - Make the main flow work, then handle errors
3. **Visual feedback** - Loading spinners, success messages
4. **Mobile-friendly** - Use Tailwind responsive classes

## References

- [references/components.md](references/components.md) - Component patterns, forms, loading states
- [references/api-integration.md](references/api-integration.md) - Fetch utilities, server actions
- [references/auth-patterns.md](references/auth-patterns.md) - Login flow, protected routes, auth context
