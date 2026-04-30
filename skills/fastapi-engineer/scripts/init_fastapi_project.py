#!/usr/bin/env python3
"""
Script to initialize a new FastAPI project with the recommended structure
for course companion applications.
"""

import os
import sys
from pathlib import Path

def create_directory_structure(base_path):
    """Create the recommended directory structure"""
    directories = [
        "app/models",
        "app/schemas",
        "app/routers",
        "app/utils",
        "tests",
        "alembic/versions"
    ]

    for directory in directories:
        path = Path(base_path) / directory
        path.mkdir(parents=True, exist_ok=True)
        # Create __init__.py files
        init_file = path / "__init__.py"
        if not init_file.exists():
            init_file.touch()

def create_main_app(base_path):
    """Create the main application file"""
    main_content = '''from fastapi import FastAPI
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
'''

    main_file = Path(base_path) / "app" / "main.py"
    with open(main_file, 'w') as f:
        f.write(main_content)

def create_config_file(base_path):
    """Create configuration file"""
    config_content = '''import os
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
'''

    config_file = Path(base_path) / "app" / "config.py"
    with open(config_file, 'w') as f:
        f.write(config_content)

def create_database_file(base_path):
    """Create database setup file"""
    db_content = '''from sqlalchemy import create_engine
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
'''

    db_file = Path(base_path) / "app" / "database.py"
    with open(db_file, 'w') as f:
        f.write(db_content)

def create_requirements_file(base_path):
    """Create requirements file"""
    requirements_content = '''fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
pydantic-settings==2.1.0
psycopg2-binary==2.9.9  # For PostgreSQL
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
alembic==1.13.1
pytest==7.4.3
httpx==0.25.2
'''

    req_file = Path(base_path) / "requirements.txt"
    with open(req_file, 'w') as f:
        f.write(requirements_content)

def create_env_file(base_path):
    """Create .env file"""
    env_content = '''DATABASE_URL=sqlite:///./course_companion.db
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
UPLOAD_FOLDER=uploads/
MAX_CONTENT_LENGTH=104857600
'''

    env_file = Path(base_path) / ".env"
    with open(env_file, 'w') as f:
        f.write(env_content)

def create_readme(base_path):
    """Create README file"""
    readme_content = '''# Course Companion API

This is a FastAPI backend for course content delivery and quiz grading systems.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables in `.env` file

3. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Project Structure

- `app/` - Main application code
  - `main.py` - Application factory and main routes
  - `config.py` - Configuration settings
  - `database.py` - Database connection and session
  - `models/` - SQLAlchemy models
  - `schemas/` - Pydantic schemas
  - `routers/` - API route definitions
  - `utils/` - Utility functions
- `tests/` - Test files
- `alembic/` - Migration files

## API Endpoints

- Authentication: `/api/auth/`
- Courses: `/api/courses/`
- Content: `/api/content/`
- Quizzes: `/api/quizzes/`
'''

    readme_file = Path(base_path) / "README.md"
    with open(readme_file, 'w') as f:
        f.write(readme_content)

def main():
    if len(sys.argv) != 2:
        print("Usage: python init_fastapi_project.py <project_directory>")
        sys.exit(1)

    project_dir = Path(sys.argv[1])

    if project_dir.exists():
        print(f"Error: Directory {project_dir} already exists!")
        sys.exit(1)

    print(f"Creating FastAPI project structure in {project_dir}...")

    # Create directory structure
    create_directory_structure(project_dir)

    # Create files
    create_main_app(project_dir)
    create_config_file(project_dir)
    create_database_file(project_dir)
    create_requirements_file(project_dir)
    create_env_file(project_dir)
    create_readme(project_dir)

    print(f"✅ FastAPI project created successfully in {project_dir}")
    print("\nNext steps:")
    print("1. cd into the project directory")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Set up your environment variables in .env")
    print("4. Run the application: uvicorn app.main:app --reload")

if __name__ == "__main__":
    main()