#!/usr/bin/env node

/**
 * Next.js Project Setup Script
 * Creates a new Next.js project with recommended configuration for LMS applications
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function askQuestion(question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer);
    });
  });
}

function createDirectory(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    console.log(`✅ Created directory: ${dirPath}`);
  }
}

function writeFile(filePath, content) {
  fs.writeFileSync(filePath, content);
  console.log(`✅ Created file: ${filePath}`);
}

function createNextJSConfig() {
  return `/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true, // Enable App Router
  },
  images: {
    domains: [
      'images.unsplash.com', // For demo images
      'avatars.githubusercontent.com', // For avatars
      'lh3.googleusercontent.com', // For Google auth
      'graph.facebook.com', // For Facebook auth
      'r2.cloudflarestorage.com', // For Cloudflare R2
      'your-storage-domain.com' // Add your image domains here
    ],
  },
  env: {
    // Environment variables will be added to .env.local
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
`;
}

function createTailwindConfig() {
  return `/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        secondary: {
          50: '#f8fafc',
          500: '#64748b',
          600: '#475569',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
`;
}

function createPostCSSConfig() {
  return `module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
`;
}

function createGlobalCSS() {
  return `@tailwind base;
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

/* LMS-specific styles */
.course-card {
  @apply transition-all duration-300 hover:shadow-lg hover:-translate-y-1;
}

.dashboard-container {
  @apply w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8;
}
`;
}

function createPackageJson(projectName) {
  return `{
  "name": "${projectName.toLowerCase().replace(/\s+/g, '-')}",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "prettier": "prettier --write ."
  },
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "openai": "^4.0.0",
    "react-circular-progressbar": "^2.1.0",
    "ai": "^2.2.0"
  },
  "devDependencies": {
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.3.0",
    "eslint": "^8.0.0",
    "eslint-config-next": "14.0.0",
    "prettier": "^3.0.0",
    "@types/node": "^20.0.0",
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0"
  }
}
`;
}

function createESLintConfig() {
  return `{
  "extends": ["next/core-web-vitals", "prettier"],
  "plugins": ["prettier"],
  "rules": {
    "prettier/prettier": "error"
  }
}
`;
}

function createPrettierConfig() {
  return `{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 80,
  "tabWidth": 2,
  "useTabs": false,
  "bracketSpacing": true,
  "arrowParens": "avoid"
}
`;
}

function createGitignore() {
  return `# Dependencies
node_modules/

# Environment variables
.env.local
.env.development.local
.env.test.local
.env.production.local

# Next.js
.next/
out/

# IDEs
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Build outputs
dist/
build/
`;
}

function createEnvLocal() {
  return `# Next.js
NEXT_PUBLIC_SITE_URL=http://localhost:3000

# OpenAI
OPENAI_API_KEY=

# Database
DATABASE_URL=""

# Cloudflare R2
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_R2_ACCESS_KEY_ID=
CLOUDFLARE_R2_SECRET_ACCESS_KEY=
CLOUDFLARE_R2_BUCKET_NAME=
`;
}

function createAppRouterStructure(projectDir) {
  const appDir = path.join(projectDir, 'app');

  // Create app directory structure
  createDirectory(path.join(appDir));
  createDirectory(path.join(appDir, 'api'));
  createDirectory(path.join(appDir, 'dashboard'));
  createDirectory(path.join(appDir, 'courses'));
  createDirectory(path.join(appDir, 'components'));
  createDirectory(path.join(appDir, 'components', 'ui'));
  createDirectory(path.join(appDir, 'components', 'dashboard'));
  createDirectory(path.join(appDir, 'components', 'chat'));
  createDirectory(path.join(appDir, 'lib'));

  // Create main layout
  const layoutContent = `import './globals.css';
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
          {children}
        </div>
      </body>
    </html>
  );
}
`;
  writeFile(path.join(appDir, 'layout.js'), layoutContent);

  // Create home page
  const pageContent = `import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
            Welcome to <span className="text-blue-600">Course Companion</span>
          </h1>
          <p className="text-xl text-gray-600 mb-10">
            Your AI-powered learning platform for personalized education experiences.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/dashboard"
              className="btn-primary px-8 py-3 text-lg font-semibold"
            >
              Go to Dashboard
            </Link>
            <Link
              href="/courses"
              className="px-8 py-3 text-lg font-semibold text-blue-600 hover:text-blue-700"
            >
              Browse Courses
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
`;
  writeFile(path.join(appDir, 'page.js'), pageContent);

  // Create dashboard page
  const dashboardPage = `import DashboardLayout from '@/components/layout/DashboardLayout';

export default function DashboardPage() {
  return (
    <DashboardLayout title="Dashboard">
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Stats cards will go here */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium text-gray-900">Total Courses</h3>
            <p className="text-3xl font-bold text-blue-600">12</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium text-gray-900">Completed</h3>
            <p className="text-3xl font-bold text-green-600">5</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium text-gray-900">In Progress</h3>
            <p className="text-3xl font-bold text-yellow-600">4</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium text-gray-900">Hours Learned</h3>
            <p className="text-3xl font-bold text-purple-600">48</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Activity</h2>
          <div className="space-y-4">
            <div className="flex items-center p-4 border rounded-lg">
              <div className="bg-blue-100 p-3 rounded-full mr-4">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
                </svg>
              </div>
              <div>
                <p className="font-medium">Started "Advanced React Patterns"</p>
                <p className="text-sm text-gray-500">2 hours ago</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
`;
  writeFile(path.join(appDir, 'dashboard', 'page.js'), dashboardPage);

  // Create basic dashboard layout component
  const dashboardLayoutComponent = `'use client';

import { useState } from 'react';
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline';

const navigation = [
  { name: 'Dashboard', href: '/dashboard' },
  { name: 'Courses', href: '/courses' },
  { name: 'Progress', href: '#' },
  { name: 'Students', href: '#' },
];

export default function DashboardLayout({ children, title }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Mobile sidebar */}
      <div className="md:hidden">
        <div className={\`fixed inset-0 z-40 flex \${sidebarOpen ? '' : 'hidden'}\`}>
          <div className="fixed inset-0 z-40" onClick={() => setSidebarOpen(false)}>
            <div className="absolute inset-0 bg-gray-600 opacity-75"></div>
          </div>
          <div className="relative flex w-full max-w-xs flex-1 flex-col bg-white pt-5 pb-4">
            <div className="flex flex-shrink-0 items-center px-4">
              <h1 className="text-xl font-bold text-gray-900">CourseCompanion</h1>
            </div>
            <nav className="mt-5 flex-1 space-y-1 px-2">
              {navigation.map((item) => (
                <a
                  key={item.name}
                  href={item.href}
                  className="text-gray-700 hover:bg-gray-100 hover:text-gray-900 group flex items-center px-2 py-2 text-sm font-medium rounded-md"
                >
                  {item.name}
                </a>
              ))}
            </nav>
          </div>
        </div>
      </div>

      {/* Static sidebar for desktop */}
      <div className="hidden md:flex md:w-64 md:flex-shrink-0">
        <div className="flex flex-col border-r border-gray-200 bg-white">
          <div className="flex flex-shrink-0 items-center border-b border-gray-200 p-4">
            <h1 className="text-xl font-bold text-gray-900">CourseCompanion</h1>
          </div>
          <nav className="flex flex-1 flex-col space-y-1 px-2 py-4">
            {navigation.map((item) => (
              <a
                key={item.name}
                href={item.href}
                className="text-gray-700 hover:bg-gray-100 hover:text-gray-900 group flex items-center px-2 py-2 text-sm font-medium rounded-md"
              >
                {item.name}
              </a>
            ))}
          </nav>
        </div>
      </div>

      <div className="flex flex-1 flex-col overflow-hidden md:pl-64">
        <header className="bg-white shadow-sm">
          <div className="mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
            <button
              type="button"
              className="border-r border-gray-200 pr-3 text-gray-500 md:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <span className="sr-only">Open sidebar</span>
              <Bars3Icon className="h-6 w-6" aria-hidden="true" />
            </button>
            <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
            <div className="flex items-center">
              <div className="ml-3 relative">
                <div>
                  <button className="flex text-sm rounded-full focus:outline-none">
                    <img
                      className="h-8 w-8 rounded-full"
                      src="/avatar-placeholder.jpg"
                      alt="User avatar"
                    />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
`;
  writeFile(path.join(appDir, 'components', 'layout', 'DashboardLayout.js'), dashboardLayoutComponent);
}

async function main() {
  console.log('🚀 Next.js Project Setup Wizard');
  console.log('This will create a new Next.js project with recommended configuration for LMS applications.\n');

  const projectName = await askQuestion('Enter project name: ');
  const projectDir = path.join(process.cwd(), projectName);

  // Check if directory already exists
  if (fs.existsSync(projectDir)) {
    console.error(`❌ Directory ${projectDir} already exists!`);
    process.exit(1);
  }

  console.log(`\n📁 Creating project directory: ${projectName}`);
  createDirectory(projectDir);

  // Change to project directory
  process.chdir(projectDir);

  console.log('\n📄 Creating configuration files...');

  // Create configuration files
  writeFile('next.config.js', createNextJSConfig());
  writeFile('tailwind.config.js', createTailwindConfig());
  writeFile('postcss.config.js', createPostCSSConfig());
  writeFile('package.json', createPackageJson(projectName));
  writeFile('.eslintrc.json', createESLintConfig());
  writeFile('.prettierrc', createPrettierConfig());
  writeFile('.gitignore', createGitignore());

  // Create app directory structure
  console.log('\n🏗️  Creating app directory structure...');
  createAppRouterStructure(projectDir);

  // Create global CSS
  createDirectory(path.join(projectDir, 'app'));
  writeFile(path.join(projectDir, 'app', 'globals.css'), createGlobalCSS());

  // Create lib directory with basic API client
  const apiClientContent = `// lib/api.js
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

class ApiClient {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = \`\${this.baseURL}\${endpoint}\`;

    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    const response = await fetch(url, config);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || \`HTTP error! status: \${response.status}\`);
    }

    return response.json();
  }

  // Example API methods
  async getDashboardStats() {
    return this.request('/dashboard/stats');
  }

  async getCourses() {
    return this.request('/courses');
  }
}

export default new ApiClient();
`;
  writeFile(path.join(projectDir, 'app', 'lib', 'api.js'), apiClientContent);

  // Create .env.local
  writeFile('.env.local', createEnvLocal());

  console.log('\n📦 Installing dependencies...');
  try {
    execSync('npm install', { stdio: 'inherit' });
    console.log('✅ Dependencies installed successfully!');
  } catch (error) {
    console.error('❌ Error installing dependencies:', error.message);
    process.exit(1);
  }

  console.log('\n🎨 Installing Tailwind CSS and dependencies...');
  try {
    execSync('npx tailwindcss init -p', { stdio: 'inherit' });
    console.log('✅ Tailwind CSS configured successfully!');
  } catch (error) {
    console.error('❌ Error configuring Tailwind CSS:', error.message);
    process.exit(1);
  }

  console.log('\n🎉 Project setup complete!');
  console.log(`\nYour Next.js project "${projectName}" is ready!`);
  console.log('\nTo get started:');
  console.log(`  cd ${projectName}`);
  console.log('  npm run dev');
  console.log('\nYour application will be available at http://localhost:3000');

  rl.close();
}

// Run the main function
main().catch((error) => {
  console.error('❌ Setup failed:', error.message);
  process.exit(1);
});