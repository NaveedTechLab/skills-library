#!/usr/bin/env python3
"""
Database initialization script for Neon PostgreSQL
Creates tables and runs initial setup
"""

import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def init_db():
    """Initialize database with tables"""

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Convert to async URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    print(f"Connecting to database...")

    # Create engine
    engine = create_async_engine(
        database_url,
        echo=True,  # Log SQL queries
    )

    try:
        # Import all models to ensure they're registered
        # Adjust this import based on your project structure
        try:
            from app.db.base import Base
            from app import models  # Import all models
        except ImportError:
            print("Warning: Could not import models. Make sure your project structure is correct.")
            print("Expected: app/db/base.py with Base class and app/models.py with model definitions")
            return

        # Create all tables
        print("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✓ Database initialized successfully")

        # Verify tables were created
        async with engine.connect() as conn:
            result = await conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            tables = [row[0] for row in result]
            print(f"\nCreated tables: {', '.join(tables)}")

    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

async def seed_db():
    """Seed database with initial data"""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Add your seed data here
            # Example:
            # from app.models import User
            # admin_user = User(
            #     email="admin@example.com",
            #     username="admin",
            #     is_active=True
            # )
            # session.add(admin_user)
            # await session.commit()

            print("✓ Database seeded successfully")

    except Exception as e:
        print(f"Error seeding database: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

async def reset_db():
    """Drop all tables and recreate them"""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    # Confirm reset
    response = input("⚠️  This will DELETE ALL DATA. Are you sure? (yes/no): ")
    if response.lower() != "yes":
        print("Reset cancelled")
        return

    engine = create_async_engine(database_url, echo=True)

    try:
        from app.db.base import Base
        from app import models

        print("Dropping all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        print("Creating all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✓ Database reset successfully")

    except Exception as e:
        print(f"Error resetting database: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

def main():
    """Main entry point"""

    if len(sys.argv) < 2:
        print("Usage: python init_db.py {init|seed|reset}")
        print("\nCommands:")
        print("  init  - Create all database tables")
        print("  seed  - Populate database with initial data")
        print("  reset - Drop and recreate all tables (DESTRUCTIVE)")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        asyncio.run(init_db())
    elif command == "seed":
        asyncio.run(seed_db())
    elif command == "reset":
        asyncio.run(reset_db())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
