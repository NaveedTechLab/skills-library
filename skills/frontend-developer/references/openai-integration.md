# OpenAI Integration Guide

## Setup and Installation

### Installing OpenAI SDK
```bash
# For Node.js/Next.js applications
npm install openai

# For browser-only applications
npm install openai @types/openai
```

### Environment Configuration
```
# .env.local
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ORGANIZATION=your_org_id_optional
OPENAI_PROJECT=your_project_id_optional
```

## Basic OpenAI Client Setup

### JavaScript/TypeScript Client
```javascript
import OpenAI from 'openai';

// Initialize the OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY, // This is the default and can be omitted
  organization: process.env.OPENAI_ORGANIZATION,
  project: process.env.OPENAI_PROJECT,
});

// Or with custom configuration
const customOpenAI = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: 'https://api.openai.com/v1', // Default, can be customized
  timeout: 30000, // 30 seconds timeout
  maxRetries: 2,
});
```

## Chat Completions API

### Basic Chat Completion
```javascript
async function getChatCompletion() {
  const completion = await openai.chat.completions.create({
    messages: [{ role: 'user', content: 'Hello!' }],
    model: 'gpt-3.5-turbo',
  });

  console.log(completion.choices[0].message.content);
  return completion.choices[0].message;
}
```

### Advanced Chat Completion with Options
```javascript
async function getAdvancedChatCompletion(userInput, context = []) {
  const messages = [
    {
      role: 'system',
      content: 'You are a helpful assistant for an educational platform. Be concise and informative.'
    },
    ...context,
    { role: 'user', content: userInput }
  ];

  const completion = await openai.chat.completions.create({
    model: 'gpt-4-turbo',
    messages: messages,
    temperature: 0.7,
    max_tokens: 1000,
    top_p: 1,
    frequency_penalty: 0,
    presence_penalty: 0,
    stream: false, // Set to true for streaming
  });

  return completion.choices[0].message;
}
```

## Streaming Responses

### Streaming with Async Generator
```javascript
async function* streamChatCompletion(messages) {
  const stream = await openai.chat.completions.create({
    model: 'gpt-3.5-turbo',
    messages: messages,
    stream: true,
  });

  for await (const chunk of stream) {
    yield chunk.choices[0]?.delta?.content || '';
  }
}

// Usage in React component
async function handleStreamResponse(userInput, setMessageCallback) {
  const messages = [{ role: 'user', content: userInput }];

  for await (const chunk of streamChatCompletion(messages)) {
    setMessageCallback(prev => prev + chunk);
  }
}
```

### Streaming in React Components
```jsx
// components/StreamingChat.jsx
import React, { useState, useRef, useEffect } from 'react';

const StreamingChat = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!inputValue.trim() || isStreaming) return;

    // Add user message
    const userMessage = { id: Date.now(), role: 'user', content: inputValue };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsStreaming(true);

    try {
      abortControllerRef.current = new AbortController();

      const response = await fetch('/api/openai/stream-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, userMessage],
          signal: abortControllerRef.current.signal
        }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = { id: Date.now() + 1, role: 'assistant', content: '' };

      setMessages(prev => [...prev, assistantMessage]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);
              if (parsed.choices?.[0]?.delta?.content) {
                assistantMessage.content += parsed.choices[0].delta.content;

                setMessages(prev => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = { ...assistantMessage };
                  return newMessages;
                });
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Streaming error:', error);
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.'
        }]);
      }
    } finally {
      setIsStreaming(false);
    }
  };

  const stopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  };

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
        {isStreaming && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg max-w-xs flex items-center">
              <span>Thinking</span>
              <span className="ml-2 animate-pulse">...</span>
              <button
                onClick={stopStreaming}
                className="ml-2 text-xs bg-red-500 text-white px-2 py-1 rounded"
              >
                Stop
              </button>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="border-t p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isStreaming}
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isStreaming}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isStreaming ? 'Sending...' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default StreamingChat;
```

### Streaming API Route (Next.js App Router)
```javascript
// app/api/openai/stream-chat/route.js
import OpenAI from 'openai';
import { StreamingTextResponse, streamText } from 'ai'; // Using Vercel AI SDK
import { NextResponse } from 'next/server';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(req) {
  try {
    const { messages } = await req.json();

    const response = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages,
      stream: true,
    });

    // Convert OpenAI stream to text stream for response
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        for await (const chunk of response) {
          const content = chunk.choices[0]?.delta?.content || '';
          if (content) {
            const text = `data: ${JSON.stringify({ choices: [{ delta: { content } }] })}\n\n`;
            controller.enqueue(encoder.encode(text));
          }
        }
        controller.enqueue(encoder.encode(`data: [DONE]\n\n`));
        controller.close();
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    console.error('Streaming error:', error);
    return NextResponse.json({ error: 'Failed to stream response' }, { status: 500 });
  }
}
```

## Conversation History Management

### Context Window Management
```javascript
class ConversationManager {
  constructor(maxTokens = 4096, safetyMargin = 500) {
    this.maxTokens = maxTokens - safetyMargin;
    this.messages = [];
    this.tokenCount = 0;
  }

  async addMessage(role, content) {
    const newMessage = { role, content };
    const newTokenCount = await this.estimateTokens(newMessage);

    // Trim conversation if it exceeds token limit
    while ((this.tokenCount + newTokenCount) > this.maxTokens && this.messages.length > 0) {
      const removedMessage = this.messages.shift();
      this.tokenCount -= await this.estimateTokens(removedMessage);
    }

    this.messages.push(newMessage);
    this.tokenCount += newTokenCount;
  }

  async estimateTokens(message) {
    // Simple estimation - in production, use tiktoken or similar
    const text = `${message.role} ${message.content}`;
    return Math.ceil(text.length / 4); // Rough estimation
  }

  getMessages() {
    return this.messages;
  }

  clear() {
    this.messages = [];
    this.tokenCount = 0;
  }
}

// Usage
const conversation = new ConversationManager();

// Add messages with automatic context management
await conversation.addMessage('user', 'Hello, teach me about React hooks');
await conversation.addMessage('assistant', 'React hooks...');
```

### Session-Based Conversation Storage
```javascript
// hooks/useConversation.js
import { useState, useCallback } from 'react';

export const useConversation = (sessionId) => {
  const [messages, setMessages] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(`conversation_${sessionId}`);
      return saved ? JSON.parse(saved) : [];
    }
    return [];
  });

  const addMessage = useCallback((message) => {
    setMessages(prev => {
      const newMessages = [...prev, message];
      if (typeof window !== 'undefined') {
        localStorage.setItem(`conversation_${sessionId}`, JSON.stringify(newMessages));
      }
      return newMessages;
    });
  }, [sessionId]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    if (typeof window !== 'undefined') {
      localStorage.removeItem(`conversation_${sessionId}`);
    }
  }, [sessionId]);

  const updateLastMessage = useCallback((content) => {
    setMessages(prev => {
      const newMessages = [...prev];
      if (newMessages.length > 0) {
        newMessages[newMessages.length - 1].content = content;
        if (typeof window !== 'undefined') {
          localStorage.setItem(`conversation_${sessionId}`, JSON.stringify(newMessages));
        }
      }
      return newMessages;
    });
  }, [sessionId]);

  return {
    messages,
    addMessage,
    clearMessages,
    updateLastMessage,
  };
};
```

## Error Handling and Fallbacks

### Robust Error Handling
```javascript
import OpenAI from 'openai';

class OpenAIService {
  constructor() {
    this.client = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
    });
    this.maxRetries = 3;
    this.retryDelay = 1000; // 1 second
  }

  async callWithRetry(options, retries = 0) {
    try {
      return await this.client.chat.completions.create(options);
    } catch (error) {
      if (retries < this.maxRetries && this.isRetryableError(error)) {
        await this.delay(this.retryDelay * Math.pow(2, retries)); // Exponential backoff
        return this.callWithRetry(options, retries + 1);
      }

      throw error;
    }
  }

  isRetryableError(error) {
    return (
      error.status === 429 || // Rate limit
      error.status >= 500 ||  // Server errors
      error.message.includes('network') ||
      error.message.includes('timeout')
    );
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async generateResponse(prompt, options = {}) {
    const defaultOptions = {
      model: 'gpt-3.5-turbo',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.7,
      ...options,
    };

    try {
      const response = await this.callWithRetry(defaultOptions);
      return {
        success: true,
        content: response.choices[0].message.content,
        usage: response.usage,
      };
    } catch (error) {
      console.error('OpenAI API error:', error);

      // Return fallback response
      return {
        success: false,
        content: 'I\'m having trouble connecting right now. Please try again.',
        error: error.message,
        fallback: true,
      };
    }
  }
}

// Usage
const aiService = new OpenAIService();
const result = await aiService.generateResponse('Explain quantum computing');
```

## Educational Context Integration

### Course-Specific Instructions
```javascript
// services/educationalAI.js
export class EducationalAI {
  constructor() {
    this.client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  }

  async getLessonExplanation(topic, difficulty = 'beginner', courseContext = '') {
    const systemMessage = {
      role: 'system',
      content: `You are an educational assistant helping students learn.
      Adapt your explanations to the student's level: ${difficulty}.
      Use clear examples and encourage questions.
      ${courseContext ? `Current course context: ${courseContext}` : ''}`
    };

    const userMessage = { role: 'user', content: `Explain ${topic} in simple terms.` };

    const response = await this.client.chat.completions.create({
      model: 'gpt-4-turbo',
      messages: [systemMessage, userMessage],
      temperature: 0.7,
      max_tokens: 500,
    });

    return response.choices[0].message.content;
  }

  async generatePracticeQuestion(topic, questionType = 'multiple-choice', courseContext = '') {
    const systemMessage = {
      role: 'system',
      content: `Generate educational content for the topic: ${topic}.
      Question type: ${questionType}.
      ${courseContext ? `Course context: ${courseContext}` : ''}
      Return in JSON format with the question, options (for MCQ), and explanation.`
    };

    const response = await this.client.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [systemMessage],
      temperature: 0.5,
      response_format: { type: "json_object" },
    });

    return JSON.parse(response.choices[0].message.content);
  }
}
```

## Rate Limiting and Caching

### API Call Rate Limiting
```javascript
// lib/rateLimiter.js
export class RateLimiter {
  constructor(maxRequests = 60, windowMs = 60000) { // 60 requests per minute
    this.maxRequests = maxRequests;
    this.windowMs = windowMs;
    this.requests = new Map();
  }

  isAllowed(userId) {
    const now = Date.now();
    const userRequests = this.requests.get(userId) || [];

    // Remove old requests outside the window
    const validRequests = userRequests.filter(timestamp => now - timestamp < this.windowMs);

    if (validRequests.length >= this.maxRequests) {
      return false;
    }

    // Add current request
    validRequests.push(now);
    this.requests.set(userId, validRequests);

    return true;
  }
}

// Usage with OpenAI calls
const rateLimiter = new RateLimiter(10, 60000); // 10 requests per minute

export async function safeOpenAICall(userId, messages) {
  if (!rateLimiter.isAllowed(userId)) {
    throw new Error('Rate limit exceeded. Please try again later.');
  }

  const response = await openai.chat.completions.create({
    model: 'gpt-3.5-turbo',
    messages,
  });

  return response;
}
```

### Response Caching
```javascript
// lib/cache.js
export class SimpleCache {
  constructor(ttl = 300000) { // 5 minutes default TTL
    this.cache = new Map();
    this.ttl = ttl;
  }

  set(key, value) {
    this.cache.set(key, {
      value,
      timestamp: Date.now()
    });
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;

    if (Date.now() - item.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }

    return item.value;
  }

  has(key) {
    return this.get(key) !== null;
  }

  clear() {
    this.cache.clear();
  }
}

// Using cache with OpenAI
const cache = new SimpleCache(60000); // 1 minute cache

export async function cachedOpenAIRequest(prompt) {
  const cacheKey = `openai:${prompt.substring(0, 50)}:${prompt.length}`;

  // Check cache first
  const cached = cache.get(cacheKey);
  if (cached) {
    return cached;
  }

  // Make API call
  const response = await openai.chat.completions.create({
    model: 'gpt-3.5-turbo',
    messages: [{ role: 'user', content: prompt }],
  });

  // Cache the response
  cache.set(cacheKey, response);

  return response;
}
```

## Security Considerations

### Input Sanitization
```javascript
// lib/inputSanitizer.js
export function sanitizeUserInput(input) {
  // Remove potential prompt injection attempts
  return input
    .replace(/<system>/gi, '&lt;system&gt;')
    .replace(/<user>/gi, '&lt;user&gt;')
    .replace(/<assistant>/gi, '&lt;assistant&gt;')
    .replace(/\{\{/g, '&#123;&#123;')
    .replace(/\}\}/g, '&#125;&#125;')
    .trim();
}

// Safe API call wrapper
export async function safeChatCompletion(userInput) {
  const sanitizedInput = sanitizeUserInput(userInput);

  const response = await openai.chat.completions.create({
    model: 'gpt-3.5-turbo',
    messages: [{ role: 'user', content: sanitizedInput }],
  });

  return response;
}
```

### Content Moderation
```javascript
// lib/moderation.js
export async function moderateContent(text) {
  const response = await openai.moderations.create({
    input: text,
  });

  const [result] = response.results;

  return {
    flagged: result.flagged,
    categories: result.categories,
    categoryScores: result.category_scores,
  };
}

// Usage with content filtering
export async function generateSafeResponse(prompt) {
  const response = await openai.chat.completions.create({
    model: 'gpt-3.5-turbo',
    messages: [{ role: 'user', content: prompt }],
  });

  const content = response.choices[0].message.content;
  const moderationResult = await moderateContent(content);

  if (moderationResult.flagged) {
    return "I can't provide that information as it may violate our content policy.";
  }

  return content;
}
```