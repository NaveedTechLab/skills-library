# Component Templates for Next.js/React Applications

This collection provides standardized templates for common UI components used in educational applications and LMS dashboards.

## 1. Button Component

### Basic Button Template
```jsx
// components/ui/Button.jsx
import React from 'react';

const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  iconLeft,
  iconRight,
  onClick,
  className = '',
  type = 'button',
  ...props
}) => {
  const baseClasses = 'inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 whitespace-nowrap';

  const variantClasses = {
    primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
    secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
    destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
    outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
    ghost: 'hover:bg-accent hover:text-accent-foreground',
    link: 'text-primary underline-offset-4 hover:underline',
  };

  const sizeClasses = {
    sm: 'h-9 px-3 text-xs',
    md: 'h-10 px-4 py-2 text-sm',
    lg: 'h-11 px-8 text-base',
    xl: 'h-12 px-8 text-lg',
  };

  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      onClick={onClick}
      disabled={disabled || loading}
      type={type}
      {...props}
    >
      {loading && (
        <span className="mr-2 h-4 w-4 animate-spin" role="status">
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </span>
      )}
      {iconLeft && <span className="mr-2">{iconLeft}</span>}
      {children}
      {iconRight && <span className="ml-2">{iconRight}</span>}
    </button>
  );
};

export default Button;
```

## 2. Card Component

### Basic Card Template
```jsx
// components/ui/Card.jsx
import React from 'react';

const Card = ({ children, className = '', ...props }) => {
  return (
    <div
      className={`rounded-xl border bg-card text-card-foreground shadow ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

const CardHeader = ({ children, className = '', ...props }) => {
  return (
    <div className={`flex flex-col space-y-1.5 p-6 ${className}`} {...props}>
      {children}
    </div>
  );
};

const CardTitle = ({ children, className = '', ...props }) => {
  return (
    <h3
      className={`text-2xl font-semibold leading-none tracking-tight ${className}`}
      {...props}
    >
      {children}
    </h3>
  );
};

const CardDescription = ({ children, className = '', ...props }) => {
  return (
    <p className={`text-sm text-muted-foreground ${className}`} {...props}>
      {children}
    </p>
  );
};

const CardContent = ({ children, className = '', ...props }) => {
  return (
    <div className={`p-6 pt-0 ${className}`} {...props}>
      {children}
    </div>
  );
};

const CardFooter = ({ children, className = '', ...props }) => {
  return (
    <div className={`flex items-center p-6 pt-0 ${className}`} {...props}>
      {children}
    </div>
  );
};

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
};
```

## 3. Form Input Component

### Text Input Template
```jsx
// components/ui/Input.jsx
import React from 'react';

const Input = React.forwardRef(({ className, type, ...props }, ref) => {
  return (
    <input
      type={type}
      className={`flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      ref={ref}
      {...props}
    />
  );
});
Input.displayName = "Input";

export { Input };
```

### Select Component Template
```jsx
// components/ui/Select.jsx
import React from 'react';

const Select = ({ options, value, onChange, placeholder, className = '', ...props }) => {
  return (
    <select
      value={value}
      onChange={onChange}
      className={`flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    >
      {placeholder && (
        <option value="" disabled>
          {placeholder}
        </option>
      )}
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
};

export { Select };
```

## 4. Dashboard Stat Card

### Stats Card Template
```jsx
// components/dashboard/StatsCard.jsx
import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const StatsCard = ({
  title,
  value,
  change,
  icon: Icon,
  trend,
  footer,
  loading = false
}) => {
  const trendIcon = {
    up: <TrendingUp className="h-4 w-4 text-green-500" />,
    down: <TrendingDown className="h-4 w-4 text-red-500" />,
    neutral: <Minus className="h-4 w-4 text-gray-500" />
  }[trend] || null;

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          {loading ? (
            <div className="h-8 w-24 bg-gray-200 rounded mt-2 animate-pulse"></div>
          ) : (
            <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
          )}
        </div>
        {Icon && (
          <div className="p-3 rounded-full bg-blue-100">
            <Icon className="h-6 w-6 text-blue-600" />
          </div>
        )}
      </div>

      {change !== undefined && (
        <div className="flex items-center mt-4">
          <div className="flex items-center">
            {trendIcon}
            <span className={`text-sm font-medium ml-1 ${
              trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-600'
            }`}>
              {change}
            </span>
          </div>
          <span className="text-sm text-gray-500 ml-2">from last month</span>
        </div>
      )}

      {footer && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          {footer}
        </div>
      )}
    </div>
  );
};

export default StatsCard;
```

## 5. Progress Bar Component

### Progress Bar Template
```jsx
// components/ui/ProgressBar.jsx
import React from 'react';

const ProgressBar = ({
  value = 0,
  max = 100,
  variant = 'default',
  showLabel = true,
  className = ''
}) => {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const variantColors = {
    default: 'bg-blue-600',
    success: 'bg-green-600',
    warning: 'bg-yellow-500',
    error: 'bg-red-600',
  };

  return (
    <div className={`w-full ${className}`}>
      <div className="flex justify-between text-sm mb-1">
        {showLabel && (
          <span className="text-gray-600">
            {value} / {max} ({Math.round(percentage)}%)
          </span>
        )}
        <span className="text-gray-600">
          {Math.round(percentage)}%
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className={`h-2.5 rounded-full ${variantColors[variant] || variantColors.default} transition-all duration-300 ease-out`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
    </div>
  );
};

export default ProgressBar;
```

## 6. Modal Component

### Modal Template
```jsx
// components/ui/Modal.jsx
import React, { useEffect } from 'react';

const Modal = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  size = 'md'
}) => {
  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
  };

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4 text-center sm:block sm:p-0">
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        ></div>

        <div className="inline-block transform overflow-hidden rounded-lg bg-white text-left align-bottom shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6 sm:align-middle">
          <div className="sm:flex sm:items-start">
            <div className="mt-3 w-full sm:mt-0 sm:ml-4 sm:text-left">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium leading-6 text-gray-900">
                  {title}
                </h3>
                <button
                  type="button"
                  className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none"
                  onClick={onClose}
                >
                  <span className="sr-only">Close</span>
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="mt-4">
                {children}
              </div>
              {footer && (
                <div className="mt-6 flex justify-end space-x-3">
                  {footer}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Modal;
```

## 7. Course Card Component

### Course Card Template
```jsx
// components/courses/CourseCard.jsx
import React from 'react';
import { PlayIcon, ClockIcon, UserIcon, BookOpenIcon } from '@heroicons/react/24/outline';

const CourseCard = ({
  course,
  onClick,
  showProgress = true,
  showActions = true
}) => {
  const {
    id,
    title,
    description,
    progress = 0,
    instructor,
    duration,
    thumbnail,
    category,
    level
  } = course;

  return (
    <div
      className="bg-white rounded-xl shadow-sm border overflow-hidden hover:shadow-md transition-shadow cursor-pointer group"
      onClick={() => onClick && onClick(course)}
    >
      {thumbnail && (
        <div className="relative h-48 overflow-hidden">
          <img
            src={thumbnail}
            alt={title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-4">
            <button className="bg-white text-gray-900 rounded-full p-3 shadow-lg hover:bg-gray-100 transition-colors">
              <PlayIcon className="h-6 w-6" />
            </button>
          </div>
        </div>
      )}

      <div className="p-6">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
            {title}
          </h3>
          {level && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              {level}
            </span>
          )}
        </div>

        {category && (
          <span className="inline-block px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded mb-2">
            {category}
          </span>
        )}

        <p className="text-gray-600 text-sm mb-4 line-clamp-2">{description}</p>

        <div className="flex items-center text-sm text-gray-500 mb-4 space-x-4">
          {instructor && (
            <div className="flex items-center">
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

        {showProgress && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Progress</span>
              <span className="font-medium text-gray-900">{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>
        )}

        {showActions && (
          <div className="mt-4 flex space-x-2">
            <button
              className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                onClick && onClick(course);
              }}
            >
              {progress > 0 ? 'Continue' : 'Start Course'}
            </button>
            <button className="p-2 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors">
              <svg className="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 12h.01M12 12h.01M19 12h.01M6 12a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0z" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CourseCard;
```

## 8. Chat Interface Component

### Chat Interface Template
```jsx
// components/chat/ChatInterface.jsx
import React, { useState, useRef, useEffect } from 'react';

const ChatInterface = ({
  initialMessages = [],
  onSendMessage,
  showTypingIndicator = true,
  title = 'Assistant'
}) => {
  const [messages, setMessages] = useState(initialMessages);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!inputValue.trim()) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      // Simulate API call - replace with actual implementation
      const response = await onSendMessage(inputValue, messages);

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-sm border">
      <div className="border-b p-4">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-96">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-xs sm:max-w-md px-4 py-2 rounded-lg ${
              message.role === 'user'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-800'
            }`}>
              <div className="whitespace-pre-wrap">{message.content}</div>
              <div className={`text-xs mt-1 ${
                message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
              }`}>
                {message.timestamp?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        ))}

        {isTyping && showTypingIndicator && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-800 px-4 py-2 rounded-lg max-w-xs">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="border-t p-4">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            disabled={isTyping}
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isTyping}
            className="px-4 py-2 bg-blue-500 text-white rounded-md text-sm font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
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

These templates provide a solid foundation for building educational applications with consistent, well-structured components that follow modern React/Next.js best practices.