import React, { useState } from 'react';
import { useDarkMode } from '../hooks/useDarkMode';

interface NavItem { label: string; href: string; icon?: React.ReactNode; }

interface DashboardLayoutProps {
  title: string;
  navItems?: NavItem[];
  children: React.ReactNode;
}

export function DashboardLayout({ title, navItems = [], children }: DashboardLayoutProps) {
  const { isDark, toggle } = useDarkMode();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-20 bg-black/40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-30 w-64 bg-white dark:bg-gray-900
        border-r border-gray-200 dark:border-gray-800
        transform transition-transform lg:translate-x-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex items-center h-16 px-6 border-b border-gray-200 dark:border-gray-800">
          <span className="text-lg font-bold text-indigo-600 dark:text-indigo-400">{title}</span>
        </div>
        <nav className="p-4 space-y-1">
          {navItems.map(item => (
            <a key={item.href} href={item.href}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
              {item.icon && <span className="text-gray-400">{item.icon}</span>}
              {item.label}
            </a>
          ))}
        </nav>
      </aside>

      {/* Main */}
      <div className="lg:pl-64 flex flex-col min-h-screen">
        {/* Top bar */}
        <header className="h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between px-4 lg:px-6">
          <button onClick={() => setSidebarOpen(v => !v)} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 lg:hidden" aria-label="Open menu">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="flex-1" />
          {/* Dark mode toggle */}
          <button onClick={toggle} aria-label="Toggle dark mode"
            className="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            {isDark ? (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-6 xl:p-8 max-w-screen-2xl mx-auto w-full">
          {children}
        </main>
      </div>
    </div>
  );
}
