---
name: fastapi-engineer
description: Expert in developing deterministic FastAPI backends for content delivery, navigation, and rule-based quiz grading. Knowledgeable in Zero-Backend-LLM principles, ensuring no LLM calls are made in the core API routes.
---

# FastAPI Engineer

Expert in developing deterministic FastAPI backends for content delivery, navigation, and rule-based quiz grading. Knowledgeable in Zero-Backend-LLM principles, ensuring no LLM calls are made in the core API routes.

## When to Use This Skill

Use this skill when developing FastAPI applications that require:
- Content delivery systems for course materials
- Navigation features for course progression
- Rule-based quiz grading systems
- Deterministic backend operations without LLM dependencies
- RESTful API development with proper authentication and authorization

## Core Principles

### Zero-Backend-LLM Architecture
- No LLM calls in core API routes
- Deterministic processing using rule-based logic
- Fast, predictable response times
- Reliable offline functionality

### Content Delivery Best Practices
- Efficient file serving with proper caching headers
- Media type handling for various content formats
- Streaming large files to prevent memory issues
- CDN-ready architecture patterns

### Quiz Grading Systems
- Rule-based validation and scoring
- Support for multiple question types (MCQ, fill-in-blank, etc.)
- Immediate feedback mechanisms
- Progress tracking and persistence

## Standard FastAPI Patterns

### Route Structure
```
# Content delivery routes
GET /api/content/{course_id}/materials
GET /api/content/{course_id}/material/{material_id}
POST /api/content/upload

# Navigation routes
GET /api/navigation/{course_id}/path
GET /api/navigation/{course_id}/progress
PUT /api/navigation/{course_id}/progress

# Quiz routes
GET /api/quizzes/{quiz_id}
POST /api/quizzes/{quiz_id}/submit
GET /api/quizzes/{quiz_id}/results
```

### Dependency Injection Pattern
```python
from fastapi import Depends, HTTPException
from typing import Optional

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    # Validate and return user data
    pass

@app.get("/protected/route")
async def protected_route(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}
```

### Response Models
```python
from pydantic import BaseModel

class MaterialResponse(BaseModel):
    id: str
    title: str
    content_type: str
    url: str
    created_at: str

    class Config:
        from_attributes = True
```

## Error Handling Standards

- Use appropriate HTTP status codes (400, 401, 403, 404, 500)
- Consistent error response format
- Proper logging without exposing sensitive information

## Security Considerations

- Input validation and sanitization
- Rate limiting for API endpoints
- Secure authentication with JWT or OAuth2
- CORS configuration for frontend integration
- File upload validation and security
## When NOT to Use This Skill

- **Microservices with Dapr integration** — use `fastapi-dapr-agent` which includes sidecar configurations
- **Prototype/throwaway scripts** — FastAPI's full structure (routers, models, middleware) is overkill for a quick script; use Flask or a plain Python function
- **GraphQL APIs** — FastAPI supports GraphQL via Strawberry, but this skill generates REST APIs by default; specify GraphQL explicitly if that's the requirement

## Common Mistakes

- Not using `async def` for I/O-bound route handlers — synchronous route handlers block the event loop and drastically reduce throughput under concurrent load
- Not validating environment variables at startup — missing `DATABASE_URL` or API keys cause cryptic runtime errors; use Pydantic `Settings` to validate config at import time
- Returning `dict` objects directly instead of Pydantic response models — raw dicts bypass validation and expose internal field names; always define response schemas

## Related Skills

- [`fastapi-backend-builder`](../fastapi-backend-builder/SKILL.md) — Full-featured FastAPI app with auth, DB migrations, and testing
- [`backend-rest-api`](../backend-rest-api/SKILL.md) — Framework-agnostic REST API design principles
- [`database-postgresql-design`](../database-postgresql-design/SKILL.md) — Design the PostgreSQL schema the FastAPI app will use
