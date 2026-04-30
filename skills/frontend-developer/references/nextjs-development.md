# Next.js Development Guide

## Project Setup

### Creating a New Next.js Project
```bash
# Using create-next-app
npx create-next-app@latest my-app --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

# Or manually
mkdir my-app
cd my-app
npm init -y
npm install next react react-dom
npm install -D typescript @types/react @types/node @types/react-dom
```

### Basic Next.js Configuration (next.config.js)
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true, // Enable App Router
  },
  images: {
    domains: ['example.com', 'r2.cloudflarestorage.com'], // Add your image domains
  },
  env: {
    // Environment variables
  },
  webpack: (config, { isServer }) => {
    // Custom webpack configuration
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
      };
    }
    return config;
  },
};

module.exports = nextConfig;
```

## App Router Structure

### Basic App Directory Structure
```
app/
├── layout.js              # Root layout
├── page.js                # Homepage
├── globals.css            # Global styles
├── error.js              # Error boundary
├── loading.js            # Loading UI
├── not-found.js          # 404 page
├── api/                  # API routes
│   └── route.js
├── dashboard/            # Dashboard route
│   ├── page.js
│   └── layout.js
└── courses/              # Courses route
    ├── [id]/             # Dynamic route for course
    │   ├── page.js
    │   └── layout.js
    └── page.js
```

### Root Layout (app/layout.js)
```jsx
import './globals.css';
import { Inter } from 'next/font/google';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'Course Companion',
  description: 'Learn with AI-powered assistance',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-background">
          {/* Your app shell */}
          <header>...</header>
          <main>{children}</main>
          <footer>...</footer>
        </div>
      </body>
    </html>
  );
}
```

## Component Architecture

### Server and Client Components
```jsx
// app/components/ServerComponent.jsx (Server Component)
import { getCourses } from '@/lib/courses';

export default async function ServerComponent() {
  const courses = await getCourses();

  return (
    <div>
      {courses.map(course => (
        <CourseCard key={course.id} course={course} />
      ))}
    </div>
  );
}

// app/components/ClientComponent.jsx (Client Component)
'use client';

import { useState } from 'react';

export default function ClientComponent() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <button onClick={() => setIsOpen(!isOpen)}>
      Toggle Panel
    </button>
  );
}
```

### Data Fetching Patterns
```jsx
// app/dashboard/page.js
import { getCourses } from '@/lib/courses';
import { Suspense } from 'react';
import CourseList from './CourseList';

// Server Component that fetches data
export default async function DashboardPage() {
  const courses = await getCourses();

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold">Dashboard</h1>

      {/* Static content */}
      <Suspense fallback={<div>Loading courses...</div>}>
        <CourseList initialCourses={courses} />
      </Suspense>
    </div>
  );
}

// app/dashboard/CourseList.jsx
'use client';

import { useState, useEffect } from 'react';
import CourseCard from '@/components/CourseCard';

export default function CourseList({ initialCourses }) {
  const [courses, setCourses] = useState(initialCourses);

  // Client-side data fetching if needed
  useEffect(() => {
    // Additional client-side logic
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {courses.map(course => (
        <CourseCard key={course.id} course={course} />
      ))}
    </div>
  );
}
```

## API Routes

### Basic API Route (app/api/route.js)
```javascript
import { NextResponse } from 'next/server';

// GET request
export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  // Your logic here
  const data = await fetchData(id);

  return NextResponse.json({ data });
}

// POST request
export async function POST(request) {
  try {
    const body = await request.json();

    // Validate body
    if (!body.title) {
      return NextResponse.json(
        { error: 'Title is required' },
        { status: 400 }
      );
    }

    // Process data
    const result = await createResource(body);

    return NextResponse.json({ result }, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
```

### OpenAI Integration API Route
```javascript
// app/api/openai/chat/route.js
import OpenAI from 'openai';
import { NextResponse } from 'next/server';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(request) {
  try {
    const body = await request.json();
    const { messages, model = 'gpt-3.5-turbo', temperature = 0.7 } = body;

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json(
        { error: 'Invalid messages' },
        { status: 400 }
      );
    }

    const response = await openai.chat.completions.create({
      model,
      messages,
      temperature,
    });

    return NextResponse.json({
      choices: response.choices,
      usage: response.usage,
    });
  } catch (error) {
    console.error('OpenAI API error:', error);
    return NextResponse.json(
      {
        error: 'Failed to call OpenAI API',
        message: error.message
      },
      { status: 500 }
    );
  }
}
```

## Styling with Tailwind CSS

### Global Styles (app/globals.css)
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 47.4% 11.2%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 47.4% 11.2%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 47.4% 11.2%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 100% 50%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 47.4% 11.2%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 224 71% 4%;
    --foreground: 213 31% 91%;
    --card: 224 71% 4%;
    --card-foreground: 213 31% 91%;
    --popover: 224 71% 4%;
    --popover-foreground: 213 31% 91%;
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 1.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 63% 31%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}

/* Custom utility classes */
.container {
  @apply w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8;
}

.btn-primary {
  @apply inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500;
}
```

### Component Styling with CSS Modules
```css
/* components/CourseCard.module.css */
.card {
  @apply bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden transition-all duration-300 hover:shadow-md;
}

.card:hover {
  @apply -translate-y-1;
}

.progressContainer {
  @apply w-full bg-gray-200 rounded-full h-2.5;
}

.progressBar {
  @apply bg-blue-600 h-2.5 rounded-full transition-all duration-500;
}
```

## Performance Optimization

### Image Optimization
```jsx
// Using Next.js Image component
import Image from 'next/image';

export default function CourseImage({ src, alt, priority = false }) {
  return (
    <div className="relative w-full h-48">
      <Image
        src={src}
        alt={alt}
        fill
        className="object-cover"
        priority={priority}
        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
      />
    </div>
  );
}
```

### Code Splitting and Lazy Loading
```jsx
// app/components/LazyComponent.jsx
import dynamic from 'next/dynamic';

// Dynamically import heavy components
const HeavyChart = dynamic(() => import('./charts/HeavyChart'), {
  loading: () => <div>Loading chart...</div>,
  ssr: false // Only render on client-side
});

// Lazy load with custom loading component
const DashboardCharts = dynamic(
  () => import('./DashboardCharts'),
  {
    loading: () => <SkeletonLoader />,
  }
);

export default function PageWithLazyComponents() {
  return (
    <div>
      <h1>Dashboard</h1>
      <Suspense fallback={<div>Loading charts...</div>}>
        <HeavyChart />
      </Suspense>
    </div>
  );
}
```

### Route-based Code Splitting
```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  // Enable granular chunking
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            chunks: 'all',
          },
        },
      };
    }
    return config;
  },
};

module.exports = nextConfig;
```

## Internationalization (i18n)

### Basic i18n Setup
```javascript
// next-i18next.config.js
module.exports = {
  i18n: {
    locales: ['en', 'es', 'fr'],
    defaultLocale: 'en',
  },
};

// app/i18n.js
import { notFound } from 'next/navigation';
import { getRequestConfig } from 'next-intl/server';

export default getRequestConfig(async ({ locale }) => {
  try {
    return {
      messages: (await import(`../messages/${locale}.json`)).default,
    };
  } catch (error) {
    notFound();
  }
});
```

## Environment Configuration

### Environment Variables (.env.local)
```
# Next.js
NEXT_PUBLIC_SITE_URL=http://localhost:3000

# Database
DATABASE_URL="your-database-url"

# OpenAI
OPENAI_API_KEY="your-openai-api-key"

# Cloudinary or other image services
NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME="your-cloud-name"

# Third-party services
NEXT_PUBLIC_ANALYTICS_ID="your-analytics-id"
```

## Testing Setup

### Jest Configuration (jest.config.js)
```javascript
const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: './',
});

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleDirectories: ['node_modules', '<rootDir>/'],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
};

module.exports = createJestConfig(customJestConfig);
```

### Example Test File
```javascript
// __tests__/CourseCard.test.js
import { render, screen } from '@testing-library/react';
import CourseCard from '@/components/CourseCard';

describe('CourseCard', () => {
  const mockCourse = {
    id: '1',
    title: 'Introduction to React',
    description: 'Learn React basics',
    progress: 50,
  };

  it('renders course title', () => {
    render(<CourseCard course={mockCourse} />);
    expect(screen.getByText('Introduction to React')).toBeInTheDocument();
  });

  it('displays progress percentage', () => {
    render(<CourseCard course={mockCourse} />);
    expect(screen.getByText('50%')).toBeInTheDocument();
  });
});
```

## Deployment Configuration

### Production Build Commands
```bash
# Build the application
npm run build

# Start production server
npm start

# Or use npx
npx next build
npx next start
```

### Docker Configuration (Dockerfile)
```dockerfile
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./
RUN \
  if [ -f yarn.lock ]; then yarn --frozen-lockfile; \
  elif [ -f package-lock.json ]; then npm ci; \
  elif [ -f pnpm-lock.yaml ]; then yarn global add pnpm && pnpm i --frozen-lockfile; \
  else echo "Lockfile not found." && exit 1; \
  fi

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED 1

RUN npx next build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
```