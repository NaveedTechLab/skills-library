#!/usr/bin/env python3
"""
Simple test script to verify FastAPI project setup
"""

def test_imports():
    """Test that required packages can be imported"""
    try:
        import fastapi
        import sqlalchemy
        import pydantic
        import uvicorn
        print("✅ All required packages imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_fastapi_app():
    """Test basic FastAPI app creation"""
    try:
        from fastapi import FastAPI
        app = FastAPI(title="Test App")

        @app.get("/test")
        def test_endpoint():
            return {"message": "Test successful"}

        print("✅ FastAPI app created successfully")
        return True
    except Exception as e:
        print(f"❌ FastAPI app creation error: {e}")
        return False

def test_sqlalchemy_setup():
    """Test basic SQLAlchemy setup"""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import sessionmaker

        engine = create_engine("sqlite:///:memory:")
        Base = declarative_base()

        print("✅ SQLAlchemy setup successful")
        return True
    except Exception as e:
        print(f"❌ SQLAlchemy setup error: {e}")
        return False

def main():
    print("Testing FastAPI project setup...")

    results = []
    results.append(test_imports())
    results.append(test_fastapi_app())
    results.append(test_sqlalchemy_setup())

    if all(results):
        print("\n🎉 All tests passed! FastAPI project is ready.")
        return True
    else:
        print("\n💥 Some tests failed. Please check your setup.")
        return False

if __name__ == "__main__":
    main()