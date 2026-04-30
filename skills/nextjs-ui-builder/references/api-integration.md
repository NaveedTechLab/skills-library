# API Integration Patterns

## Table of Contents
1. [Fetch Utilities](#fetch-utilities)
2. [Server Components](#server-components)
3. [Client-Side Fetching](#client-side-fetching)
4. [Server Actions](#server-actions)

---

## Fetch Utilities

### `lib/api.ts`

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: 'Request failed' }));
    throw new ApiError(res.status, error.message || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  get: async <T>(path: string, options?: RequestInit): Promise<T> => {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    return handleResponse<T>(res);
  },

  post: async <T>(path: string, data: unknown, options?: RequestInit): Promise<T> => {
    const res = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      body: JSON.stringify(data),
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    return handleResponse<T>(res);
  },

  put: async <T>(path: string, data: unknown, options?: RequestInit): Promise<T> => {
    const res = await fetch(`${API_URL}${path}`, {
      method: 'PUT',
      body: JSON.stringify(data),
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    return handleResponse<T>(res);
  },

  delete: async <T>(path: string, options?: RequestInit): Promise<T> => {
    const res = await fetch(`${API_URL}${path}`, {
      method: 'DELETE',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    return handleResponse<T>(res);
  },
};
```

### With Authentication Token

```typescript
export function createAuthenticatedApi(token: string) {
  const authHeaders = { Authorization: `Bearer ${token}` };

  return {
    get: <T>(path: string) => api.get<T>(path, { headers: authHeaders }),
    post: <T>(path: string, data: unknown) => api.post<T>(path, data, { headers: authHeaders }),
    put: <T>(path: string, data: unknown) => api.put<T>(path, data, { headers: authHeaders }),
    delete: <T>(path: string) => api.delete<T>(path, { headers: authHeaders }),
  };
}
```

---

## Server Components

### Fetching in Server Components

```tsx
// app/todos/page.tsx
import { api } from '@/lib/api';
import { TodoList } from '@/components/TodoList';

interface Todo {
  id: number;
  title: string;
  status: string;
}

interface TodosResponse {
  items: Todo[];
  total: number;
}

export default async function TodosPage() {
  const data = await api.get<TodosResponse>('/todos');

  return (
    <main className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">My Todos</h1>
      <TodoList todos={data.items} />
    </main>
  );
}
```

### With Caching Options

```tsx
// Force dynamic rendering (no cache)
export const dynamic = 'force-dynamic';

// Or configure fetch caching
async function getTodos() {
  const res = await fetch(`${API_URL}/todos`, {
    next: { revalidate: 60 }, // Revalidate every 60 seconds
  });
  return res.json();
}

// For user-specific data (no caching)
async function getUserTodos(token: string) {
  const res = await fetch(`${API_URL}/todos`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store', // Always fetch fresh
  });
  return res.json();
}
```

---

## Client-Side Fetching

### Custom Hook with SWR-like Pattern

```tsx
// hooks/useTodos.ts
'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

interface Todo {
  id: number;
  title: string;
  status: string;
}

export function useTodos() {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchTodos = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.get<{ items: Todo[] }>('/todos');
      setTodos(data.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTodos();
  }, [fetchTodos]);

  const createTodo = async (title: string) => {
    const newTodo = await api.post<Todo>('/todos', { title });
    setTodos((prev) => [newTodo, ...prev]);
    return newTodo;
  };

  const deleteTodo = async (id: number) => {
    await api.delete(`/todos/${id}`);
    setTodos((prev) => prev.filter((t) => t.id !== id));
  };

  return { todos, loading, error, refetch: fetchTodos, createTodo, deleteTodo };
}
```

### Using the Hook

```tsx
'use client';

import { useTodos } from '@/hooks/useTodos';

export function TodoList() {
  const { todos, loading, error, createTodo, deleteTodo } = useTodos();

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <ul className="space-y-2">
      {todos.map((todo) => (
        <li key={todo.id} className="flex justify-between items-center p-3 bg-white rounded shadow">
          <span>{todo.title}</span>
          <button
            onClick={() => deleteTodo(todo.id)}
            className="text-red-600 hover:text-red-800"
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  );
}
```

---

## Server Actions

### Basic Server Action

```tsx
// app/actions.ts
'use server';

import { revalidatePath } from 'next/cache';
import { cookies } from 'next/headers';

export async function createTodo(formData: FormData) {
  const title = formData.get('title') as string;
  const token = cookies().get('token')?.value;

  const res = await fetch(`${process.env.API_URL}/todos`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ title }),
  });

  if (!res.ok) {
    throw new Error('Failed to create todo');
  }

  revalidatePath('/todos');
}

export async function deleteTodo(id: number) {
  const token = cookies().get('token')?.value;

  await fetch(`${process.env.API_URL}/todos/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });

  revalidatePath('/todos');
}
```

### Using Server Actions in Components

```tsx
// Form with server action
import { createTodo } from '@/app/actions';

export function CreateTodoForm() {
  return (
    <form action={createTodo} className="flex gap-2">
      <input
        name="title"
        placeholder="New todo..."
        className="flex-1 px-3 py-2 border rounded"
        required
      />
      <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">
        Add
      </button>
    </form>
  );
}

// Button with server action
import { deleteTodo } from '@/app/actions';

export function DeleteButton({ id }: { id: number }) {
  const deleteWithId = deleteTodo.bind(null, id);

  return (
    <form action={deleteWithId}>
      <button type="submit" className="text-red-600">
        Delete
      </button>
    </form>
  );
}
```

### With Optimistic Updates

```tsx
'use client';

import { useOptimistic, useTransition } from 'react';
import { deleteTodo } from '@/app/actions';

export function TodoItem({ todo }: { todo: Todo }) {
  const [isPending, startTransition] = useTransition();
  const [optimisticDeleted, setOptimisticDeleted] = useOptimistic(false);

  if (optimisticDeleted) return null;

  return (
    <li className={`flex justify-between ${isPending ? 'opacity-50' : ''}`}>
      <span>{todo.title}</span>
      <button
        onClick={() => {
          startTransition(async () => {
            setOptimisticDeleted(true);
            await deleteTodo(todo.id);
          });
        }}
      >
        Delete
      </button>
    </li>
  );
}
```
