# LMS Dashboard Development Guide

## Dashboard Architecture

### Core Dashboard Components Structure
```
dashboard/
├── components/
│   ├── common/
│   │   ├── Header.jsx
│   │   ├── Sidebar.jsx
│   │   ├── Navigation.jsx
│   │   └── UserMenu.jsx
│   ├── dashboard/
│   │   ├── StatsCard.jsx
│   │   ├── ProgressOverview.jsx
│   │   ├── RecentActivity.jsx
│   │   ├── CourseProgress.jsx
│   │   └── QuickActions.jsx
│   ├── courses/
│   │   ├── CourseCard.jsx
│   │   ├── CourseList.jsx
│   │   ├── CourseProgress.jsx
│   │   └── LessonCard.jsx
│   ├── charts/
│   │   ├── BarChart.jsx
│   │   ├── LineChart.jsx
│   │   ├── PieChart.jsx
│   │   └── ProgressChart.jsx
│   └── ui/
│       ├── Button.jsx
│       ├── Card.jsx
│       ├── Modal.jsx
│       └── DataTable.jsx
├── hooks/
│   ├── useDashboardData.js
│   ├── useCourseProgress.js
│   └── useUserStats.js
├── lib/
│   ├── api.js
│   ├── utils.js
│   └── constants.js
└── pages/
    ├── dashboard/
    │   └── index.jsx
    └── courses/
        └── index.jsx
```

## Dashboard Layout Components

### Main Dashboard Layout
```jsx
// components/common/DashboardLayout.jsx
import React, { useState } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

const DashboardLayout = ({ children, title }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar for desktop */}
      <div className="hidden md:flex md:w-64 md:flex-shrink-0">
        <Sidebar />
      </div>

      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-40 flex md:hidden ${sidebarOpen ? '' : 'hidden'}`}>
        <div className="fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-gray-600 opacity-75"
            onClick={() => setSidebarOpen(false)}
          ></div>
        </div>
        <div className="relative flex w-full max-w-xs flex-1 flex-col bg-white pt-5 pb-4">
          <Sidebar onClose={() => setSidebarOpen(false)} />
        </div>
      </div>

      <div className="flex flex-1 flex-col md:pl-64 w-full">
        <Header
          title={title}
          onMenuClick={() => setSidebarOpen(true)}
        />

        <main className="flex-1 p-6">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
```

### Dashboard Header Component
```jsx
// components/common/Header.jsx
import React from 'react';
import { BellIcon, SearchIcon, MenuIcon } from '@heroicons/react/outline';

const Header = ({ title, onMenuClick }) => {
  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center">
            <button
              type="button"
              className="md:hidden mr-2"
              onClick={onMenuClick}
            >
              <MenuIcon className="h-6 w-6 text-gray-500" />
            </button>
            <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
          </div>

          <div className="flex items-center space-x-4">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <SearchIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                placeholder="Search..."
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              />
            </div>

            <button className="p-1 rounded-full text-gray-400 hover:text-gray-500 focus:outline-none">
              <BellIcon className="h-6 w-6" />
            </button>

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
      </div>
    </header>
  );
};

export default Header;
```

### Dashboard Sidebar Component
```jsx
// components/common/Sidebar.jsx
import React from 'react';
import { HomeIcon, BookOpenIcon, ChartBarIcon, UserGroupIcon, CogIcon } from '@heroicons/react/outline';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Courses', href: '/courses', icon: BookOpenIcon },
  { name: 'Progress', href: '/progress', icon: ChartBarIcon },
  { name: 'Students', href: '/students', icon: UserGroupIcon },
  { name: 'Settings', href: '/settings', icon: CogIcon },
];

const Sidebar = ({ onClose }) => {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-center h-16 px-4 bg-indigo-700">
        <div className="text-white font-bold text-xl">CourseCompanion</div>
      </div>

      <div className="flex-1 overflow-y-auto py-4">
        <nav className="px-2 space-y-1">
          {navigation.map((item) => (
            <a
              key={item.name}
              href={item.href}
              className="text-gray-700 hover:bg-gray-100 hover:text-gray-900 group flex items-center px-2 py-2 text-sm font-medium rounded-md"
            >
              <item.icon
                className="mr-3 flex-shrink-0 h-6 w-6 text-gray-400 group-hover:text-gray-500"
                aria-hidden="true"
              />
              {item.name}
            </a>
          ))}
        </nav>
      </div>
    </div>
  );
};

export default Sidebar;
```

## Dashboard Data Visualization

### Stats Cards Component
```jsx
// components/dashboard/StatsCard.jsx
import React from 'react';
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/outline';

const StatsCard = ({ title, value, change, icon: Icon, trend }) => {
  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className="p-3 rounded-md bg-blue-100">
              {Icon && <Icon className="h-6 w-6 text-blue-600" />}
            </div>
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
              <dd className="flex items-baseline">
                <div className="text-2xl font-semibold text-gray-900">{value}</div>
                {change && (
                  <div className={`ml-2 flex items-baseline text-sm font-semibold ${
                    trend === 'up' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {trend === 'up' ? (
                      <ArrowUpIcon className="self-center flex-shrink-0 h-5 w-5 text-green-500" />
                    ) : (
                      <ArrowDownIcon className="self-center flex-shrink-0 h-5 w-5 text-red-500" />
                    )}
                    <span className="sr-only">{trend === 'up' ? 'Increased' : 'Decreased'} by</span>
                    {change}
                  </div>
                )}
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatsCard;
```

### Progress Overview Component
```jsx
// components/dashboard/ProgressOverview.jsx
import React from 'react';
import { CircularProgressbar, buildStyles } from 'react-circular-progressbar';
import 'react-circular-progressbar/dist/styles.css';

const ProgressOverview = ({ courses }) => {
  // Calculate overall progress
  const totalCourses = courses.length;
  const completedCourses = courses.filter(course => course.progress === 100).length;
  const overallProgress = totalCourses > 0 ? Math.round((completedCourses / totalCourses) * 100) : 0;

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Learning Overview</h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="flex flex-col items-center">
          <div style={{ width: 100, height: 100 }}>
            <CircularProgressbar
              value={overallProgress}
              text={`${overallProgress}%`}
              styles={buildStyles({
                textSize: '16px',
                pathColor: '#3b82f6',
                textColor: '#3b82f6',
                trailColor: '#e5e7eb',
              })}
            />
          </div>
          <p className="mt-2 text-sm text-gray-600">Overall Progress</p>
        </div>

        <div className="space-y-4">
          <div className="flex justify-between">
            <span className="text-sm font-medium text-gray-600">Total Courses</span>
            <span className="text-sm font-semibold text-gray-900">{totalCourses}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm font-medium text-gray-600">Completed</span>
            <span className="text-sm font-semibold text-gray-900">{completedCourses}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm font-medium text-gray-600">In Progress</span>
            <span className="text-sm font-semibold text-gray-900">{totalCourses - completedCourses}</span>
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Course Distribution</h4>
          <div className="space-y-2">
            {courses.slice(0, 3).map((course, index) => (
              <div key={course.id} className="flex items-center">
                <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                <span className="text-sm text-gray-600 truncate">{course.title}</span>
                <span className="text-sm text-gray-500 ml-auto">{course.progress}%</span>
              </div>
            ))}
            {courses.length > 3 && (
              <div className="text-sm text-gray-500">+{courses.length - 3} more courses</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProgressOverview;
```

## Course Management Components

### Course Card Component
```jsx
// components/courses/CourseCard.jsx
import React from 'react';
import { ClockIcon, UserIcon, BookOpenIcon } from '@heroicons/react/outline';

const CourseCard = ({ course, onClick }) => {
  const {
    id,
    title,
    description,
    progress,
    instructor,
    duration,
    thumbnail,
    lastAccessed
  } = course;

  return (
    <div
      className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
      onClick={() => onClick && onClick(course)}
    >
      {thumbnail && (
        <img
          src={thumbnail}
          alt={title}
          className="w-full h-48 object-cover"
        />
      )}

      <div className="p-6">
        <div className="flex justify-between items-start">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            progress === 100
              ? 'bg-green-100 text-green-800'
              : progress > 50
                ? 'bg-blue-100 text-blue-800'
                : 'bg-yellow-100 text-yellow-800'
          }`}>
            {progress === 100 ? 'Completed' : progress > 0 ? `${progress}% Complete` : 'Not Started'}
          </span>
        </div>

        <p className="text-gray-600 text-sm mb-4">{description}</p>

        <div className="flex items-center text-sm text-gray-500 mb-4">
          {instructor && (
            <div className="flex items-center mr-4">
              <UserIcon className="h-4 w-4 mr-1" />
              <span>{instructor}</span>
            </div>
          )}

          {duration && (
            <div className="flex items-center">
              <ClockIcon className="h-4 w-4 mr-1" />
              <span>{duration}</span>
            </div>
          )}
        </div>

        <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          ></div>
        </div>

        {lastAccessed && (
          <p className="text-xs text-gray-500">Last accessed: {lastAccessed}</p>
        )}
      </div>
    </div>
  );
};

export default CourseCard;
```

### Course List Component
```jsx
// components/courses/CourseList.jsx
import React, { useState, useMemo } from 'react';
import CourseCard from './CourseCard';
import { SearchIcon } from '@heroicons/react/outline';

const CourseList = ({ courses, onCourseSelect }) => {
  const [searchTerm, setSearchTerm] = useState('');

  // Filter courses based on search term
  const filteredCourses = useMemo(() => {
    if (!searchTerm) return courses;

    return courses.filter(course =>
      course.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      course.description.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [courses, searchTerm]);

  return (
    <div className="space-y-6">
      {/* Search Bar */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <SearchIcon className="h-5 w-5 text-gray-400" />
        </div>
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search courses..."
          className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
        />
      </div>

      {/* Course Grid */}
      {filteredCourses.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCourses.map(course => (
            <CourseCard
              key={course.id}
              course={course}
              onClick={onCourseSelect}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <div className="text-gray-500">
            {searchTerm ? 'No courses found matching your search.' : 'No courses available.'}
          </div>
        </div>
      )}
    </div>
  );
};

export default CourseList;
```

## Data Hooks for Dashboard

### Dashboard Data Hook
```javascript
// hooks/useDashboardData.js
import { useState, useEffect } from 'react';
import { fetchDashboardStats, fetchRecentActivity, fetchCourseProgress } from '../lib/api';

export const useDashboardData = () => {
  const [stats, setStats] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [courseProgress, setCourseProgress] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);

        // Fetch all data concurrently
        const [statsData, activityData, progressData] = await Promise.all([
          fetchDashboardStats(),
          fetchRecentActivity(),
          fetchCourseProgress()
        ]);

        setStats(statsData);
        setRecentActivity(activityData);
        setCourseProgress(progressData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  return {
    stats,
    recentActivity,
    courseProgress,
    loading,
    error,
    refetch: () => {
      // Implement refetch logic
    }
  };
};
```

### Course Progress Hook
```javascript
// hooks/useCourseProgress.js
import { useState, useEffect } from 'react';
import { fetchCourseProgress, updateLessonProgress } from '../lib/api';

export const useCourseProgress = (courseId) => {
  const [progress, setProgress] = useState(0);
  const [lessons, setLessons] = useState([]);
  const [currentLesson, setCurrentLesson] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadProgress = async () => {
      try {
        setLoading(true);
        const data = await fetchCourseProgress(courseId);
        setProgress(data.overallProgress);
        setLessons(data.lessons);
        setCurrentLesson(data.currentLesson);
      } catch (error) {
        console.error('Error loading course progress:', error);
      } finally {
        setLoading(false);
      }
    };

    if (courseId) {
      loadProgress();
    }
  }, [courseId]);

  const markLessonComplete = async (lessonId) => {
    try {
      const updatedProgress = await updateLessonProgress(courseId, lessonId, true);
      setProgress(updatedProgress.overallProgress);
      setLessons(updatedProgress.lessons);
      return updatedProgress;
    } catch (error) {
      console.error('Error updating lesson progress:', error);
      throw error;
    }
  };

  return {
    progress,
    lessons,
    currentLesson,
    loading,
    markLessonComplete
  };
};
```

## Responsive Design Patterns

### Responsive Grid System
```jsx
// components/layout/ResponsiveGrid.jsx
import React from 'react';

const ResponsiveGrid = ({ children, cols = 'auto', gap = '6' }) => {
  const gridClass = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
    auto: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5'
  }[cols];

  return (
    <div className={`grid ${gridClass} gap-${gap}`}>
      {children}
    </div>
  );
};

export default ResponsiveGrid;
```

### Breakpoint-Specific Components
```jsx
// components/common/ResponsiveSidebar.jsx
import React, { useState, useEffect } from 'react';
import { useMediaQuery } from '../../hooks/useMediaQuery';

const ResponsiveSidebar = ({ children }) => {
  const [isOpen, setIsOpen] = useState(false);
  const isMobile = useMediaQuery('(max-width: 768px)');
  const isTablet = useMediaQuery('(max-width: 1024px)');

  const sidebarWidth = isMobile ? 'full' : isTablet ? '280px' : '320px';

  useEffect(() => {
    if (!isMobile) {
      setIsOpen(true);
    } else {
      setIsOpen(false);
    }
  }, [isMobile]);

  return (
    <>
      {/* Mobile Overlay */}
      {isMobile && isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 h-full bg-white z-50 transform transition-transform duration-300 ease-in-out ${
          isMobile
            ? isOpen
              ? 'translate-x-0 w-full'
              : '-translate-x-full w-full'
            : `translate-x-0 w-${sidebarWidth.replace('px', '')}`
        }`}
      >
        {children}
      </aside>
    </>
  );
};

export default ResponsiveSidebar;
```

### Custom Media Query Hook
```javascript
// hooks/useMediaQuery.js
import { useState, useEffect } from 'react';

export const useMediaQuery = (query) => {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    if (media.matches !== matches) {
      setMatches(media.matches);
    }

    const listener = () => setMatches(media.matches);
    media.addEventListener('change', listener);

    return () => media.removeEventListener('change', listener);
  }, [matches, query]);

  return matches;
};
```

## Accessibility Features

### Keyboard Navigation
```jsx
// components/common/KeyboardNavigable.jsx
import React, { useState } from 'react';

const KeyboardNavigable = ({ children, items, onSelect }) => {
  const [focusedIndex, setFocusedIndex] = useState(0);

  const handleKeyDown = (e) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setFocusedIndex(prev => (prev + 1) % items.length);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setFocusedIndex(prev => (prev - 1 + items.length) % items.length);
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        onSelect(items[focusedIndex]);
        break;
    }
  };

  return (
    <div onKeyDown={handleKeyDown} tabIndex={0} className="focus:outline-none">
      {React.Children.map(children, (child, index) =>
        React.cloneElement(child, {
          ...child.props,
          tabIndex: index === focusedIndex ? 0 : -1,
          className: `${child.props.className} ${index === focusedIndex ? 'ring-2 ring-blue-500' : ''}`
        })
      )}
    </div>
  );
};
```

## Performance Optimization

### Virtual Scrolling for Large Lists
```jsx
// components/common/VirtualList.jsx
import React, { useRef, useEffect, useCallback } from 'react';

const VirtualList = ({ items, itemHeight, renderItem, overscan = 5 }) => {
  const containerRef = useRef(null);
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 0 });

  const updateVisibleRange = useCallback(() => {
    if (!containerRef.current) return;

    const { scrollTop, clientHeight } = containerRef.current;
    const start = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const end = Math.min(
      items.length,
      Math.ceil((scrollTop + clientHeight) / itemHeight) + overscan
    );

    setVisibleRange({ start, end });
  }, [items.length, itemHeight, overscan]);

  useEffect(() => {
    const container = containerRef.current;
    container?.addEventListener('scroll', updateVisibleRange);
    updateVisibleRange();

    return () => {
      container?.removeEventListener('scroll', updateVisibleRange);
    };
  }, [updateVisibleRange]);

  const totalHeight = items.length * itemHeight;
  const visibleItems = items.slice(visibleRange.start, visibleRange.end);

  return (
    <div
      ref={containerRef}
      className="overflow-auto"
      style={{ height: '400px' }} // Fixed height container
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        <div
          style={{
            position: 'absolute',
            top: visibleRange.start * itemHeight,
            width: '100%',
          }}
        >
          {visibleItems.map((item, index) => (
            <div key={item.id} style={{ height: itemHeight }}>
              {renderItem(item, visibleRange.start + index)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

## Data Management and State

### Global State with Context
```javascript
// context/DashboardContext.js
import React, { createContext, useContext, useReducer } from 'react';

const DashboardStateContext = createContext();
const DashboardDispatchContext = createContext();

const dashboardReducer = (state, action) => {
  switch (action.type) {
    case 'SET_STATS':
      return { ...state, stats: action.payload };
    case 'SET_RECENT_ACTIVITY':
      return { ...state, recentActivity: action.payload };
    case 'SET_COURSE_PROGRESS':
      return { ...state, courseProgress: action.payload };
    case 'UPDATE_LESSON_PROGRESS':
      return {
        ...state,
        courseProgress: state.courseProgress.map(course =>
          course.id === action.courseId
            ? {
                ...course,
                lessons: course.lessons.map(lesson =>
                  lesson.id === action.lessonId
                    ? { ...lesson, completed: action.completed }
                    : lesson
                ),
                progress: action.newProgress
              }
            : course
        )
      };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    default:
      return state;
  }
};

export const DashboardProvider = ({ children }) => {
  const [state, dispatch] = useReducer(dashboardReducer, {
    stats: null,
    recentActivity: [],
    courseProgress: [],
    loading: false
  });

  return (
    <DashboardStateContext.Provider value={state}>
      <DashboardDispatchContext.Provider value={dispatch}>
        {children}
      </DashboardDispatchContext.Provider>
    </DashboardStateContext.Provider>
  );
};

export const useDashboardState = () => {
  const context = useContext(DashboardStateContext);
  if (context === undefined) {
    throw new Error('useDashboardState must be used within a DashboardProvider');
  }
  return context;
};

export const useDashboardDispatch = () => {
  const context = useContext(DashboardDispatchContext);
  if (context === undefined) {
    throw new Error('useDashboardDispatch must be used within a DashboardProvider');
  }
  return context;
};
```

### API Service Layer
```javascript
// lib/api.js
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;

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
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Dashboard endpoints
  async getDashboardStats() {
    return this.request('/dashboard/stats');
  }

  async getRecentActivity() {
    return this.request('/dashboard/activity');
  }

  async getCourseProgress(courseId) {
    return this.request(`/courses/${courseId}/progress`);
  }

  async updateLessonProgress(courseId, lessonId, completed) {
    return this.request(`/courses/${courseId}/lessons/${lessonId}/progress`, {
      method: 'PATCH',
      body: JSON.stringify({ completed }),
    });
  }

  // Courses endpoints
  async getCourses(filters = {}) {
    const params = new URLSearchParams(filters);
    return this.request(`/courses?${params}`);
  }

  async getCourse(courseId) {
    return this.request(`/courses/${courseId}`);
  }
}

export default new ApiService();
```