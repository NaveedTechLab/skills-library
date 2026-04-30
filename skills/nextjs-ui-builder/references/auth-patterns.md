# Authentication Patterns

## Table of Contents
1. [Simple Token Auth](#simple-token-auth)
2. [Auth Context](#auth-context)
3. [Protected Routes](#protected-routes)
4. [Login/Logout Flow](#loginlogout-flow)

---

## Simple Token Auth

### Token Storage

```typescript
// lib/auth.ts
export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token');
}

export function setToken(token: string): void {
  localStorage.setItem('token');
}

export function removeToken(): void {
  localStorage.removeItem('token');
}

// For SSR, use cookies instead
import { cookies } from 'next/headers';

export function getServerToken(): string | undefined {
  return cookies().get('token')?.value;
}
```

---

## Auth Context

### `contexts/AuthContext.tsx`

```tsx
'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

interface User {
  id: number;
  email: string;
  name: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    checkAuth();
  }, []);

  async function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const user = await api.get<User>('/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUser(user);
    } catch {
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  }

  async function login(email: string, password: string) {
    const { access_token, user } = await api.post<{
      access_token: string;
      user: User;
    }>('/auth/login', { email, password });

    localStorage.setItem('token', access_token);
    setUser(user);
    router.push('/');
  }

  function logout() {
    localStorage.removeItem('token');
    setUser(null);
    router.push('/login');
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

### Provider Setup

```tsx
// app/providers.tsx
'use client';

import { AuthProvider } from '@/contexts/AuthContext';

export function Providers({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

// app/layout.tsx
import { Providers } from './providers';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

---

## Protected Routes

### Client-Side Protection

```tsx
// components/ProtectedRoute.tsx
'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return <div className="flex justify-center p-8">Loading...</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}

// Usage in page
export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
}
```

### Middleware Protection (Recommended)

```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const publicPaths = ['/login', '/register', '/'];

export function middleware(request: NextRequest) {
  const token = request.cookies.get('token')?.value;
  const { pathname } = request.nextUrl;

  // Allow public paths
  if (publicPaths.some((path) => pathname === path)) {
    return NextResponse.next();
  }

  // Redirect to login if no token
  if (!token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('from', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
```

---

## Login/Logout Flow

### Login Page

```tsx
// app/login/page.tsx
'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-2xl font-bold mb-6 text-center">Login</h1>

        {error && (
          <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Button type="submit" loading={loading} className="w-full">
            Sign In
          </Button>
        </form>
      </div>
    </div>
  );
}
```

### Logout Button

```tsx
// components/LogoutButton.tsx
'use client';

import { useAuth } from '@/contexts/AuthContext';

export function LogoutButton() {
  const { logout } = useAuth();

  return (
    <button
      onClick={logout}
      className="text-gray-600 hover:text-gray-900"
    >
      Logout
    </button>
  );
}
```

### Auth-Aware Header

```tsx
// components/layout/Header.tsx
'use client';

import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { LogoutButton } from '@/components/LogoutButton';

export function Header() {
  const { user, isAuthenticated } = useAuth();

  return (
    <header className="bg-white shadow">
      <div className="container mx-auto px-4 py-4 flex justify-between items-center">
        <Link href="/" className="text-xl font-bold">
          MyApp
        </Link>

        <nav className="flex items-center gap-4">
          {isAuthenticated ? (
            <>
              <span className="text-gray-600">{user?.email}</span>
              <LogoutButton />
            </>
          ) : (
            <Link href="/login" className="text-blue-600 hover:underline">
              Login
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
```
