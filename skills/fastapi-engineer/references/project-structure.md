# FastAPI Project Structure

## Recommended Directory Structure
```
project/
├── app/
│   ├── __init__.py
│   ├── main.py              # Application factory and main routes
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection and session
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── course.py
│   │   └── quiz.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── course.py
│   │   └── quiz.py
│   ├── routers/             # API route definitions
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── courses.py
│   │   ├── content.py
│   │   └── quizzes.py
│   └── utils/               # Utility functions
│       ├── __init__.py
│       ├── auth.py
│       ├── validators.py
│       └── file_handlers.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Test fixtures
│   ├── test_auth.py
│   ├── test_courses.py
│   └── test_quizzes.py
├── requirements.txt
├── alembic/
│   └── versions/            # Migration files
└── alembic.ini
```

## Configuration Settings (config.py)
```python
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    UPLOAD_FOLDER: str = "uploads/"
    MAX_CONTENT_LENGTH: int = 100 * 1024 * 1024  # 100MB max file size

    class Config:
        env_file = ".env"

settings = Settings()
```

## Database Setup (database.py)
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Main Application File (main.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, courses, content, quizzes
from .config import settings

app = FastAPI(
    title="Course Companion API",
    description="FastAPI backend for course content delivery and quiz grading",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(courses.router, prefix="/api/courses", tags=["courses"])
app.include_router(content.router, prefix="/api/content", tags=["content"])
app.include_router(quizzes.router, prefix="/api/quizzes", tags=["quizzes"])

@app.get("/")
def read_root():
    return {"message": "Course Companion API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```