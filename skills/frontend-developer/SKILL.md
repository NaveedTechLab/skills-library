---
name: frontend-developer
description: Skilled in developing Next.js/React web applications for Phase 3 and integrating with the OpenAI Apps SDK for Phase 1. Focuses on responsive LMS dashboards and conversational UI integration.
---

# Frontend Developer

Skilled in developing Next.js/React web applications for Phase 3 and integrating with the OpenAI Apps SDK for Phase 1. Focuses on responsive LMS dashboards and conversational UI integration.

## When to Use This Skill

Use this skill when developing:
- Next.js/React web applications with modern UI/UX patterns
- OpenAI Apps SDK integrations for conversational interfaces
- Responsive Learning Management System (LMS) dashboards
- Educational technology applications with rich interactivity
- Conversational UI components for student engagement

## Core Capabilities

### Next.js/React Development
- Component architecture and state management
- Responsive design with Tailwind CSS and other frameworks
- Performance optimization techniques
- SEO and accessibility best practices
- TypeScript integration for type safety

### OpenAI Apps SDK Integration
- Chat completion implementations
- Conversation history management
- Streaming responses for real-time interaction
- Custom instruction and system message handling
- Error handling and fallback strategies

### LMS Dashboard Development
- Data visualization for progress tracking
- Responsive layouts for various screen sizes
- Interactive elements for course navigation
- Real-time updates and notifications
- Student/teacher role-based interfaces

## Project Structure

### Recommended Next.js Structure
```
my-app/
├── components/           # Reusable UI components
│   ├── ui/              # Low-level UI components
│   ├── dashboard/       # Dashboard-specific components
│   └── chat/            # Chat/conversation components
├── pages/               # Next.js pages
│   ├── api/             # API routes
│   ├── dashboard/       # Dashboard pages
│   └── courses/         # Course-related pages
├── lib/                 # Utilities and helper functions
├── hooks/               # Custom React hooks
├── styles/              # Global styles and CSS modules
├── types/               # TypeScript type definitions
├── public/              # Static assets
└── services/            # API service functions
```

## Component Development Patterns

### Reusable UI Components
```jsx
// components/ui/Button.jsx
import React from 'react';

const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  onClick,
  className = ''
}) => {
  const baseClasses = 'inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50';

  const variantClasses = {
    primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
    secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
    destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
    outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
    ghost: 'hover:bg-accent hover:text-accent-foreground',
  };

  const sizeClasses = {
    sm: 'h-9 px-3 text-xs',
    md: 'h-10 px-4 py-2 text-sm',
    lg: 'h-11 px-8 text-base',
  };

  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
};

export default Button;
```

### Dashboard Card Component
```jsx
// components/dashboard/DashboardCard.jsx
import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui/Card';

const DashboardCard = ({
  title,
  description,
  children,
  footer,
  className = ''
}) => {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        {children}
      </CardContent>
      {footer && <CardFooter>{footer}</CardFooter>}
    </Card>
  );
};

export default DashboardCard;
```

## OpenAI Apps SDK Integration

### Basic Chat Component
```jsx
// components/chat/ChatInterface.jsx
import React, { useState, useRef, useEffect } from 'react';
import { useOpenAI } from '../../hooks/useOpenAI';

const ChatInterface = ({ initialMessages = [] }) => {
  const [messages, setMessages] = useState(initialMessages);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { sendMessage } = useOpenAI();
  const messagesEndRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!inputValue.trim() || isLoading) return;

    // Add user message
    const userMessage = { id: Date.now(), role: 'user', content: inputValue };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Send to OpenAI and get response
      const response = await sendMessage([...messages, userMessage]);

      // Add assistant message
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: response
      }]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
              message.role === 'user'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-800'
            }`}>
              {message.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg max-w-xs">
              Thinking...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="border-t p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isLoading}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;
```

### OpenAI Hook Implementation
```javascript
// hooks/useOpenAI.js
import { useState } from 'react';

export const useOpenAI = () => {
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (messages, options = {}) => {
    setIsLoading(true);

    try {
      // Example implementation using fetch
      // In real implementation, use the OpenAI Apps SDK
      const response = await fetch('/api/openai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages,
          model: options.model || 'gpt-3.5-turbo',
          temperature: options.temperature || 0.7,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.choices[0]?.message?.content || '';
    } catch (error) {
      console.error('Error calling OpenAI API:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    sendMessage,
    isLoading
  };
};
```

## API Route for OpenAI Integration
```javascript
// pages/api/openai/chat.js
import { OpenAIApi, Configuration } from 'openai';

const configuration = new Configuration({
  apiKey: process.env.OPENAI_API_KEY,
});

const openai = new OpenAIApi(configuration);

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { messages, model = 'gpt-3.5-turbo', temperature = 0.7 } = req.body;

  if (!messages || !Array.isArray(messages)) {
    return res.status(400).json({ error: 'Invalid messages' });
  }

  try {
    const response = await openai.createChatCompletion({
      model,
      messages,
      temperature,
    });

    res.status(200).json({
      choices: response.data.choices,
      usage: response.data.usage,
    });
  } catch (error) {
    console.error('OpenAI API error:', error);
    res.status(500).json({
      error: 'Failed to call OpenAI API',
      message: error.message
    });
  }
}
```

## LMS Dashboard Components

### Progress Tracking Component
```jsx
// components/dashboard/ProgressTracker.jsx
import React from 'react';
import { CircularProgressbar, buildStyles } from 'react-circular-progressbar';
import 'react-circular-progressbar/dist/styles.css';

const ProgressTracker = ({
  progressPercentage = 0,
  title = 'Course Progress',
  subtitle = '',
  size = 120
}) => {
  return (
    <div className="flex flex-col items-center p-4 bg-white rounded-lg shadow">
      <div style={{ width: size, height: size }}>
        <CircularProgressbar
          value={progressPercentage}
          text={`${progressPercentage}%`}
          styles={buildStyles({
            textSize: '16px',
            pathColor: '#3b82f6',
            textColor: '#3b82f6',
            trailColor: '#e5e7eb',
          })}
        />
      </div>
      <div className="mt-4 text-center">
        <h3 className="font-semibold text-gray-800">{title}</h3>
        {subtitle && <p className="text-sm text-gray-600">{subtitle}</p>}
      </div>
    </div>
  );
};

export default ProgressTracker;
```

### Course Card Component
```jsx
// components/dashboard/CourseCard.jsx
import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';

const CourseCard = ({
  title,
  description,
  progress = 0,
  lastAccessed,
  onStartClick,
  onViewClick
}) => {
  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Progress</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>

          {lastAccessed && (
            <p className="text-sm text-gray-500">Last accessed: {lastAccessed}</p>
          )}

          <div className="flex gap-2 pt-2">
            <Button onClick={onStartClick} className="flex-1">
              {progress > 0 ? 'Continue' : 'Start'}
            </Button>
            <Button variant="outline" onClick={onViewClick}>
              View
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default CourseCard;
```

## Responsive Design with Tailwind CSS

### Responsive Grid Layout
```jsx
// components/layout/ResponsiveGrid.jsx
import React from 'react';

const ResponsiveGrid = ({ children, cols = 'auto' }) => {
  const gridClass = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
    auto: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
  }[cols];

  return (
    <div className={`grid ${gridClass} gap-6`}>
      {children}
    </div>
  );
};

export default ResponsiveGrid;
```

### Mobile-First Approach
```css
/* styles/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Custom styles for LMS */
.course-card {
  @apply transition-all duration-300 hover:shadow-lg hover:-translate-y-1;
}

.dashboard-container {
  @apply w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8;
}

/* Responsive typography */
.h1-responsive {
  @apply text-3xl sm:text-4xl md:text-5xl font-bold;
}

.h2-responsive {
  @apply text-2xl sm:text-3xl md:text-4xl font-semibold;
}

.text-responsive {
  @apply text-base sm:text-lg;
}
```

## Best Practices

### Performance Optimization
- Use React.memo for components that render frequently
- Implement lazy loading for images and components
- Optimize bundle size with code splitting
- Use Next.js Image component for optimized images
- Implement proper caching strategies

### Accessibility
- Use semantic HTML elements
- Implement proper ARIA attributes
- Ensure sufficient color contrast
- Provide keyboard navigation support
- Use focus management in modals and dropdowns

### SEO
- Use Next.js Head component for meta tags
- Implement structured data with JSON-LD
- Optimize page loading speed
- Create descriptive URLs
- Use alt text for images

### Type Safety with TypeScript
```typescript
// types/course.ts
export interface Course {
  id: string;
  title: string;
  description: string;
  progress: number;
  lastAccessed?: string;
  thumbnail?: string;
  duration?: string;
  instructor?: string;
}

// types/message.ts
export interface Message {
  id: string | number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: Date;
}
```