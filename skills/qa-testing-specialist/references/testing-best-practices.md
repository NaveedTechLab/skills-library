# Testing Best Practices

## Overview

Comprehensive testing guide for FastAPI backend and Next.js frontend applications with focus on social media API integration, webhook reliability, and feedback loop verification.

## Test Structure

### Pytest Organization

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/             # Integration tests
│   ├── test_api_endpoints.py
│   ├── test_social_media.py
│   └── test_database.py
├── e2e/                     # End-to-end tests
│   └── test_workflows.py
└── fixtures/                # Test data
    └── mock_data.py
```

### conftest.py Setup

```python
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.config import settings
from app.db.base import Base

# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Test database
@pytest.fixture(scope="session")
async def test_db_engine():
    engine = create_async_engine(
        settings.test_database_url,
        echo=False,
        future=True
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

# Test database session
@pytest.fixture
async def db_session(test_db_engine):
    async_session = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()

# Test client
@pytest.fixture
async def client(db_session):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# Authentication fixtures
@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test_token"}

@pytest.fixture
async def authenticated_user(db_session):
    from app.models.user import User
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
```

## Async Testing Patterns

### Basic Async Test

```python
import pytest

@pytest.mark.asyncio
async def test_async_endpoint(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
```

### Testing Async Services

```python
@pytest.mark.asyncio
async def test_async_service(db_session):
    from app.services.user import UserService

    service = UserService(db_session)
    user = await service.create_user(
        email="test@example.com",
        username="testuser"
    )

    assert user.id is not None
    assert user.email == "test@example.com"
```

### Testing with Async Context Managers

```python
@pytest.mark.asyncio
async def test_with_context_manager():
    async with AsyncClient() as client:
        response = await client.get("https://api.example.com")
        assert response.status_code == 200
```

## Mocking Strategies

### Mocking External API Calls

```python
from unittest.mock import patch, Mock

@pytest.mark.asyncio
async def test_linkedin_api_call(client):
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"id": "post_123"}
        )

        response = await client.post(
            "/api/v1/linkedin/posts",
            json={"content": "Test post"}
        )

        assert response.status_code == 201
        mock_post.assert_called_once()
```

### Mocking Async Functions

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_with_async_mock():
    mock_service = AsyncMock()
    mock_service.get_data.return_value = {"data": "test"}

    result = await mock_service.get_data()
    assert result["data"] == "test"
```

### Mocking Database Queries

```python
@pytest.mark.asyncio
async def test_database_query(db_session):
    from unittest.mock import AsyncMock
    from app.models.user import User

    # Mock the query result
    mock_user = User(id=1, email="test@example.com")
    db_session.execute = AsyncMock(return_value=Mock(
        scalars=lambda: Mock(first=lambda: mock_user)
    ))

    # Test your service
    from app.services.user import UserService
    service = UserService(db_session)
    user = await service.get_user_by_id(1)

    assert user.email == "test@example.com"
```

## Testing Social Media APIs

### LinkedIn API Testing

```python
@pytest.mark.asyncio
async def test_linkedin_oauth_flow(client):
    # Test authorization
    response = await client.get("/api/v1/auth/linkedin/authorize")
    assert response.status_code == 307
    assert "linkedin.com" in response.headers["location"]

@pytest.mark.asyncio
async def test_linkedin_post_creation(client, auth_headers):
    with patch("app.services.linkedin.LinkedInService.create_post") as mock_create:
        mock_create.return_value = {"id": "post_123"}

        response = await client.post(
            "/api/v1/linkedin/posts",
            json={"content": "Test post"},
            headers=auth_headers
        )

        assert response.status_code == 201
```

### Twitter API Testing

```python
@pytest.mark.asyncio
async def test_twitter_rate_limit(client, auth_headers):
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = Mock(
            status_code=429,
            headers={"x-rate-limit-reset": "1234567890"}
        )

        response = await client.get(
            "/api/v1/twitter/user",
            headers=auth_headers
        )

        assert response.status_code == 429
```

### Facebook API Testing

```python
@pytest.mark.asyncio
async def test_facebook_token_validation(client):
    with patch("app.services.facebook.FacebookService.validate_token") as mock_validate:
        mock_validate.return_value = {"is_valid": True}

        response = await client.post(
            "/api/v1/facebook/validate",
            json={"access_token": "test_token"}
        )

        assert response.status_code == 200
```

## Testing WhatsApp Webhooks

### Webhook Verification

```python
@pytest.mark.asyncio
async def test_webhook_verification(client):
    response = await client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "correct_token",
            "hub.challenge": "challenge_string"
        }
    )

    assert response.status_code == 200
    assert response.text == "challenge_string"
```

### Webhook Message Processing

```python
@pytest.mark.asyncio
async def test_webhook_message_processing(client, whatsapp_webhook_payload):
    with patch("app.services.whatsapp.WhatsAppService.process_message") as mock_process:
        mock_process.return_value = {"status": "processed"}

        response = await client.post(
            "/api/v1/webhooks/whatsapp",
            json=whatsapp_webhook_payload
        )

        assert response.status_code == 200
        mock_process.assert_called_once()
```

### Webhook Reliability Testing

```python
@pytest.mark.asyncio
async def test_webhook_idempotency(client, whatsapp_webhook_payload):
    # Send same webhook twice
    response1 = await client.post(
        "/api/v1/webhooks/whatsapp",
        json=whatsapp_webhook_payload
    )
    response2 = await client.post(
        "/api/v1/webhooks/whatsapp",
        json=whatsapp_webhook_payload
    )

    # Both should succeed but only process once
    assert response1.status_code == 200
    assert response2.status_code == 200
```

## Testing Feedback Loop

### Feedback Collection

```python
@pytest.mark.asyncio
async def test_feedback_collection(client, auth_headers, mock_post_metrics):
    response = await client.post(
        "/api/v1/feedback/collect",
        json=mock_post_metrics,
        headers=auth_headers
    )

    assert response.status_code == 201
    assert "feedback_id" in response.json()
```

### Learning Model Updates

```python
@pytest.mark.asyncio
async def test_learning_model_update(client, auth_headers):
    with patch("app.services.learning.LearningService.update_model") as mock_update:
        mock_update.return_value = {"model_version": "v1.2.0"}

        response = await client.post(
            "/api/v1/learning/update",
            json={"feedback_id": "feedback_123"},
            headers=auth_headers
        )

        assert response.status_code == 200
```

### End-to-End Feedback Loop

```python
@pytest.mark.asyncio
async def test_complete_feedback_loop(client, auth_headers):
    # 1. Create post
    post_response = await client.post(
        "/api/v1/posts",
        json={"content": "Test post"},
        headers=auth_headers
    )
    post_id = post_response.json()["id"]

    # 2. Collect feedback
    feedback_response = await client.post(
        "/api/v1/feedback/collect",
        json={"post_id": post_id, "metrics": {"likes": 100}},
        headers=auth_headers
    )

    # 3. Verify learning update
    assert feedback_response.status_code == 201
```

## Parametrized Testing

### Testing Multiple Platforms

```python
@pytest.mark.parametrize("platform,endpoint", [
    ("linkedin", "/api/v1/linkedin/posts"),
    ("twitter", "/api/v1/twitter/tweets"),
    ("facebook", "/api/v1/facebook/posts"),
])
@pytest.mark.asyncio
async def test_post_creation_all_platforms(client, auth_headers, platform, endpoint):
    response = await client.post(
        endpoint,
        json={"content": f"Test post for {platform}"},
        headers=auth_headers
    )

    assert response.status_code in [200, 201]
```

### Testing Multiple Scenarios

```python
@pytest.mark.parametrize("status_code,expected_result", [
    (200, "success"),
    (401, "unauthorized"),
    (429, "rate_limited"),
    (500, "error"),
])
@pytest.mark.asyncio
async def test_api_responses(client, status_code, expected_result):
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = Mock(status_code=status_code)

        response = await client.get("/api/v1/test")
        # Assert based on expected_result
```

## Coverage and Reporting

### Running Tests with Coverage

```bash
# Run all tests with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/integration/test_social_media.py -v

# Run tests matching pattern
pytest -k "linkedin" -v

# Run with markers
pytest -m "integration" -v
```

### Coverage Configuration

```ini
# pytest.ini or setup.cfg
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests

[coverage:run]
source = app
omit =
    */tests/*
    */migrations/*
    */__pycache__/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

## Test Markers

```python
import pytest

@pytest.mark.unit
def test_unit():
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration():
    pass

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_e2e():
    pass

# Run only unit tests
# pytest -m unit

# Run integration and e2e tests
# pytest -m "integration or e2e"

# Skip slow tests
# pytest -m "not slow"
```

## Error Handling Tests

### Testing Exception Handling

```python
@pytest.mark.asyncio
async def test_error_handling(client):
    with patch("app.services.user.UserService.get_user") as mock_get:
        mock_get.side_effect = Exception("Database error")

        response = await client.get("/api/v1/users/123")
        assert response.status_code == 500
```

### Testing Validation Errors

```python
@pytest.mark.asyncio
async def test_validation_error(client):
    response = await client.post(
        "/api/v1/posts",
        json={"invalid": "data"}
    )

    assert response.status_code == 422
    assert "detail" in response.json()
```

## Performance Testing

### Testing Response Times

```python
import time

@pytest.mark.asyncio
async def test_response_time(client):
    start = time.time()
    response = await client.get("/api/v1/posts")
    duration = time.time() - start

    assert response.status_code == 200
    assert duration < 1.0  # Should respond within 1 second
```

### Load Testing Pattern

```python
@pytest.mark.asyncio
async def test_concurrent_requests(client):
    import asyncio

    async def make_request():
        return await client.get("/api/v1/health")

    # Make 100 concurrent requests
    tasks = [make_request() for _ in range(100)]
    responses = await asyncio.gather(*tasks)

    # All should succeed
    assert all(r.status_code == 200 for r in responses)
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run tests
        run: pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Best Practices Summary

1. **Isolation**: Each test should be independent
2. **Mocking**: Mock external dependencies (APIs, databases)
3. **Fixtures**: Use fixtures for reusable test data
4. **Async**: Use `@pytest.mark.asyncio` for async tests
5. **Coverage**: Aim for >80% code coverage
6. **Fast**: Keep unit tests fast (<1s each)
7. **Clear**: Use descriptive test names
8. **Arrange-Act-Assert**: Follow AAA pattern
9. **Parametrize**: Test multiple scenarios efficiently
10. **CI/CD**: Run tests automatically on every commit
