---
name: implementation-specialist
description: "Expert in Next.js 14, FastAPI, and OAuth2 integration for building production-ready web applications and multi-agent systems. Use when implementing: (1) Next.js 14 applications with App Router and TypeScript, (2) FastAPI backend services with proper structure and async patterns, (3) OAuth2 authentication flows for social media platforms (Twitter, LinkedIn), (4) Multi-agent reasoning systems with orchestrator and specialist patterns, (5) Full-stack integrations between Next.js frontend and FastAPI backend. Provides boilerplate templates, reference implementations, and setup automation."
---

# Implementation Specialist

Expert guidance for implementing Next.js 14, FastAPI, OAuth2, and multi-agent systems with production-ready code patterns.

## Quick Start

### Next.js 14 Project Setup

Use the Next.js template for new projects:

```bash
# Copy template to new project
cp -r assets/nextjs-template/* ./frontend/

# Install dependencies
cd frontend
npm install

# Start development server
npm run dev
```

Template includes:
- App Router with TypeScript
- Tailwind CSS configured
- Proper tsconfig.json
- Basic layout and page structure

### FastAPI Project Setup

Use the FastAPI template for new backend services:

```bash
# Copy template to new project
cp -r assets/fastapi-template/* ./backend/

# Create virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: . venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start development server
python main.py
```

Template includes:
- Proper project structure with core/api separation
- CORS middleware configured
- Settings management with pydantic-settings
- Health check endpoint
- API versioning (v1)

## OAuth2 Integration

For platform-specific OAuth2 implementations, see [oauth2-platforms.md](references/oauth2-platforms.md).

### Supported Platforms
- **Twitter/X**: Authorization code flow with PKCE
- **LinkedIn**: Standard OAuth2 flow

### Implementation Steps

1. **Configure environment variables** in `.env`
2. **Copy reference implementation** from oauth2-platforms.md
3. **Customize redirect URIs** for your domain
4. **Implement token storage** (database, not in-memory for production)
5. **Add refresh token logic** for long-lived sessions

### Security Checklist
- ✓ Validate state parameter (CSRF protection)
- ✓ Use HTTPS in production
- ✓ Store tokens encrypted
- ✓ Implement token refresh
- ✓ Request minimal scopes
- ✓ Add rate limiting

## Multi-Agent Systems

For complete architecture patterns and implementation details, see [multi-agent-patterns.md](references/multi-agent-patterns.md).

### Core Components

1. **Agent Base Class**: Abstract base for all agents
2. **Orchestrator Agent**: Coordinates specialist agents
3. **Specialist Agents**: Domain-specific processing
4. **State Management**: Shared context between agents

### Quick Implementation

```python
from references.multi_agent_patterns import Agent, OrchestratorAgent

# Define specialist
class ContentAgent(Agent):
    async def process(self, input_data):
        # Your logic here
        return {"content": "generated content"}

# Create orchestrator
content_agent = ContentAgent()
orchestrator = OrchestratorAgent([content_agent])

# Execute
result = await orchestrator.process({"task": "create post"})
```

### Communication Patterns
- **Sequential**: Agents process in order
- **Parallel**: Independent simultaneous execution
- **Hierarchical**: Nested delegation
- **Consensus**: Multi-agent voting

## FastAPI Best Practices

### Project Structure
```
backend/
├── main.py              # Application entry point
├── app/
│   ├── core/
│   │   └── config.py    # Settings and configuration
│   ├── api/
│   │   └── v1/
│   │       ├── router.py      # Main API router
│   │       └── endpoints/     # Route handlers
│   ├── models/          # Pydantic models
│   ├── services/        # Business logic
│   └── db/              # Database models and connection
└── requirements.txt
```

### Endpoint Pattern
```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter()

class ItemCreate(BaseModel):
    name: str
    description: str

@router.post("/items")
async def create_item(item: ItemCreate):
    # Validate input (automatic with Pydantic)
    # Process business logic
    # Return response
    return {"id": 1, **item.dict()}
```

### Async Best Practices
- Use `async def` for I/O-bound operations (database, HTTP calls)
- Use regular `def` for CPU-bound operations
- Use `httpx.AsyncClient` for external API calls
- Implement proper connection pooling

## Next.js 14 Best Practices

### App Router Structure
```
app/
├── layout.tsx           # Root layout
├── page.tsx             # Home page
├── globals.css          # Global styles
├── api/                 # API routes
│   └── route.ts
└── [feature]/           # Feature-based routing
    ├── page.tsx
    └── layout.tsx
```

### Server vs Client Components
- **Server Components** (default): Data fetching, backend logic
- **Client Components** (`'use client'`): Interactivity, hooks, browser APIs

### Data Fetching Pattern
```typescript
// Server Component (default)
async function getData() {
  const res = await fetch('http://localhost:8000/api/v1/items');
  return res.json();
}

export default async function Page() {
  const data = await getData();
  return <div>{/* Render data */}</div>;
}
```

### API Route Pattern
```typescript
// app/api/items/route.ts
export async function GET() {
  const data = await fetch('http://localhost:8000/api/v1/items');
  return Response.json(await data.json());
}

export async function POST(request: Request) {
  const body = await request.json();
  // Process and return
  return Response.json({ success: true });
}
```

## Integration Patterns

### Next.js → FastAPI
```typescript
// app/api/backend/route.ts
export async function GET() {
  const response = await fetch('http://localhost:8000/api/v1/endpoint');
  return Response.json(await response.json());
}
```

### FastAPI → Next.js (SSR)
Configure CORS in FastAPI to allow Next.js origin:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Common Workflows

### Adding a New FastAPI Endpoint

1. Create endpoint file in `app/api/v1/endpoints/`
2. Define Pydantic models for request/response
3. Implement route handler with proper async
4. Add router to `app/api/v1/router.py`
5. Test with `/docs` (automatic OpenAPI)

### Adding a New Next.js Page

1. Create `page.tsx` in appropriate directory
2. Implement as Server Component by default
3. Add `'use client'` only if needed for interactivity
4. Use proper TypeScript types
5. Style with Tailwind classes

### Implementing OAuth2 Flow

1. Choose platform from oauth2-platforms.md
2. Copy reference implementation
3. Configure environment variables
4. Add routes to FastAPI router
5. Create Next.js API route to trigger flow
6. Implement token storage and refresh

## Troubleshooting

### FastAPI Issues
- **CORS errors**: Check `ALLOWED_ORIGINS` in config
- **Import errors**: Verify virtual environment is activated
- **Async warnings**: Ensure using `async def` with `await`

### Next.js Issues
- **Hydration errors**: Check server/client component boundaries
- **Build errors**: Verify TypeScript types are correct
- **API route 404**: Ensure file is named `route.ts` not `route.tsx`

### OAuth2 Issues
- **State validation fails**: Check state storage mechanism
- **Token exchange fails**: Verify client credentials and redirect URI
- **Scope errors**: Request only supported scopes for platform
