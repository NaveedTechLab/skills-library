---
name: qa-testing-specialist
description: "Expert in comprehensive testing for FastAPI backends with focus on social media API integration (LinkedIn, Twitter/X, Facebook), WhatsApp webhook reliability, and self-learning feedback loop verification. Use when: (1) Writing unit tests for backend services, models, and utilities, (2) Creating integration tests for social media API endpoints and OAuth flows, (3) Testing WhatsApp webhook verification and message processing, (4) Verifying self-learning feedback loop mechanisms, (5) Setting up test fixtures and mock data, (6) Configuring pytest with async support, (7) Generating test coverage reports, (8) Testing API rate limiting and error handling. Provides test templates, fixtures, runner scripts, and comprehensive testing best practices."
---

# QA & Testing Specialist

Expert guidance for comprehensive testing of FastAPI applications with focus on social media APIs, webhooks, and feedback loops.

## Quick Start

### Test Project Setup

```bash
# Install testing dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Create test directory structure
mkdir -p tests/{unit,integration,e2e,fixtures}

# Copy conftest.py template
cp assets/test-templates/conftest.py tests/

# Copy fixtures
cp assets/fixtures/mock_data.py tests/fixtures/
```

### Running Tests

#### Using Python Script (Cross-platform)

```bash
# Run all tests
python scripts/run_tests.py

# Run with coverage
python scripts/run_tests.py --coverage

# Run specific test type
python scripts/run_tests.py --type unit
python scripts/run_tests.py --type integration
python scripts/run_tests.py --type social
python scripts/run_tests.py --type webhook
python scripts/run_tests.py --type feedback

# Verbose output
python scripts/run_tests.py --verbose --coverage
```

#### Using Bash Script (Linux/Mac)

```bash
# Make executable
chmod +x scripts/run_tests.sh

# Run tests
./scripts/run_tests.sh --type all --coverage
```

#### Direct Pytest Commands

```bash
# All tests with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Unit tests only
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# Social media API tests
pytest -k "linkedin or twitter or facebook" -v

# WhatsApp webhook tests
pytest -k "whatsapp or webhook" -v

# Feedback loop tests
pytest -k "feedback or learning" -v
```

## Test Templates

### Social Media API Tests

For complete test templates covering LinkedIn, Twitter, and Facebook APIs, see:
- `assets/test-templates/test_social_media_apis.py`

Copy to your project:
```bash
cp assets/test-templates/test_social_media_apis.py tests/integration/
```

**Includes tests for:**
- OAuth2 authorization flows (with PKCE for Twitter)
- Token exchange and refresh
- User profile fetching
- Post creation
- Rate limit handling
- Error scenarios

### WhatsApp Webhook Tests

For WhatsApp webhook and feedback loop tests, see:
- `assets/test-templates/test_webhook_feedback.py`

Copy to your project:
```bash
cp assets/test-templates/test_webhook_feedback.py tests/integration/
```

**Includes tests for:**
- Webhook verification
- Message processing
- Status updates
- Idempotency
- Reliability and retry mechanisms
- Feedback collection and analysis
- Learning model updates

### Mock Data Fixtures

For reusable test fixtures, see:
- `assets/fixtures/mock_data.py`

Copy to your project:
```bash
cp assets/fixtures/mock_data.py tests/fixtures/
```

**Provides fixtures for:**
- Users and authentication
- Social media accounts
- Posts and metrics
- WhatsApp messages
- Agent responses
- API responses and errors

## Testing Patterns

For comprehensive testing patterns and best practices, see [testing-best-practices.md](references/testing-best-practices.md).

### Basic Async Test

```python
import pytest

@pytest.mark.asyncio
async def test_endpoint(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
```

### Mocking External APIs

```python
from unittest.mock import patch, Mock

@pytest.mark.asyncio
async def test_linkedin_post(client, auth_headers):
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {"id": "post_123"}
        )

        response = await client.post(
            "/api/v1/linkedin/posts",
            json={"content": "Test post"},
            headers=auth_headers
        )

        assert response.status_code == 201
```

### Testing with Fixtures

```python
@pytest.mark.asyncio
async def test_with_fixtures(client, mock_user, auth_headers):
    response = await client.get(
        f"/api/v1/users/{mock_user['id']}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["email"] == mock_user["email"]
```

## Social Media API Testing

### LinkedIn Tests

```python
@pytest.mark.asyncio
async def test_linkedin_oauth_flow(client):
    # Test authorization redirect
    response = await client.get("/api/v1/auth/linkedin/authorize")
    assert response.status_code == 307
    assert "linkedin.com" in response.headers["location"]

@pytest.mark.asyncio
async def test_linkedin_create_post(client, auth_headers):
    response = await client.post(
        "/api/v1/linkedin/posts",
        json={"content": "Test post"},
        headers=auth_headers
    )
    assert response.status_code == 201
```

### Twitter/X Tests

```python
@pytest.mark.asyncio
async def test_twitter_oauth_pkce(client):
    # Twitter uses OAuth2 with PKCE
    response = await client.get("/api/v1/auth/twitter/authorize")
    assert "code_challenge" in response.headers["location"]

@pytest.mark.asyncio
async def test_twitter_rate_limit(client, auth_headers):
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = Mock(status_code=429)
        response = await client.get("/api/v1/twitter/user", headers=auth_headers)
        assert response.status_code == 429
```

### Facebook Tests

```python
@pytest.mark.asyncio
async def test_facebook_oauth_flow(client):
    response = await client.get("/api/v1/auth/facebook/authorize")
    assert "facebook.com" in response.headers["location"]
```

## WhatsApp Webhook Testing

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

### Message Processing

```python
@pytest.mark.asyncio
async def test_webhook_message(client, whatsapp_webhook_payload):
    response = await client.post(
        "/api/v1/webhooks/whatsapp",
        json=whatsapp_webhook_payload
    )
    assert response.status_code == 200
```

### Reliability Testing

```python
@pytest.mark.asyncio
async def test_webhook_idempotency(client, whatsapp_webhook_payload):
    # Send same message twice
    response1 = await client.post("/api/v1/webhooks/whatsapp", json=whatsapp_webhook_payload)
    response2 = await client.post("/api/v1/webhooks/whatsapp", json=whatsapp_webhook_payload)

    # Both succeed but only process once
    assert response1.status_code == 200
    assert response2.status_code == 200
```

## Feedback Loop Testing

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
async def test_learning_update(client, auth_headers):
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
        json={"content": "Test"},
        headers=auth_headers
    )
    post_id = post_response.json()["id"]

    # 2. Collect feedback
    feedback_response = await client.post(
        "/api/v1/feedback/collect",
        json={"post_id": post_id, "metrics": {"likes": 100}},
        headers=auth_headers
    )
    assert feedback_response.status_code == 201

    # 3. Verify learning update triggered
    # Add assertions for learning model update
```

## Test Configuration

### pytest.ini

```ini
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
    social: Social media API tests
    webhook: Webhook tests
    feedback: Feedback loop tests
```

### conftest.py Essentials

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test_token"}
```

## Coverage Reporting

### Generate Coverage Report

```bash
# HTML report
pytest --cov=app --cov-report=html

# Terminal report
pytest --cov=app --cov-report=term

# XML report (for CI/CD)
pytest --cov=app --cov-report=xml
```

### View Coverage

```bash
# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Test Markers

```python
# Mark tests by category
@pytest.mark.unit
def test_unit():
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration():
    pass

@pytest.mark.social
@pytest.mark.asyncio
async def test_linkedin():
    pass

# Run specific markers
# pytest -m unit
# pytest -m "integration and social"
# pytest -m "not slow"
```

## Parametrized Testing

```python
@pytest.mark.parametrize("platform,endpoint", [
    ("linkedin", "/api/v1/linkedin/posts"),
    ("twitter", "/api/v1/twitter/tweets"),
    ("facebook", "/api/v1/facebook/posts"),
])
@pytest.mark.asyncio
async def test_all_platforms(client, platform, endpoint):
    response = await client.post(endpoint, json={"content": "Test"})
    assert response.status_code in [200, 201]
```

## Troubleshooting

### Async Tests Not Running

Ensure `pytest-asyncio` is installed and configured:
```bash
pip install pytest-asyncio
```

Add to pytest.ini:
```ini
[tool:pytest]
asyncio_mode = auto
```

### Import Errors

Add project root to PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database Connection Issues

Use test database URL in conftest.py:
```python
@pytest.fixture(scope="session")
def test_db_url():
    return "postgresql://test:test@localhost/test_db"
```

### Mock Not Working

Ensure correct import path:
```python
# Mock where it's used, not where it's defined
with patch("app.services.linkedin.httpx.AsyncClient.post"):
    # Test code
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run tests
  run: |
    pip install pytest pytest-asyncio pytest-cov
    pytest --cov=app --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Mocking**: Mock external APIs and services
3. **Fixtures**: Use fixtures for reusable test data
4. **Async**: Always use `@pytest.mark.asyncio` for async tests
5. **Coverage**: Aim for >80% code coverage
6. **Fast**: Keep unit tests fast (<1s each)
7. **Clear Names**: Use descriptive test function names
8. **AAA Pattern**: Arrange, Act, Assert
9. **Parametrize**: Test multiple scenarios efficiently
10. **CI/CD**: Run tests on every commit

## Reference Documentation

- **[testing-best-practices.md](references/testing-best-practices.md)** - Comprehensive testing patterns, async testing, mocking strategies, and CI/CD integration

## When NOT to Use This Skill

- **Prototype-phase code** — investing in a full test suite for throwaway prototypes wastes time; wait until the design is stable
- **Trivial getter/setter functions** — 100% test coverage of trivial code inflates the test suite without adding meaningful coverage of real behaviors
- **Test environments without access to real dependencies** — tests that mock everything don't catch integration failures; ensure your test environment can access actual services for integration tests

## Common Mistakes

- Writing tests that test the implementation rather than the behavior — tests that break every time an internal refactoring happens have no value; test observable outputs, not internal mechanics
- Not running tests in CI/CD — tests that only run locally miss regressions that happen in integration; every PR should trigger the full test suite
- Skipping negative test cases — testing only the happy path misses error handling bugs; always test invalid inputs, boundary conditions, and failure scenarios

## Related Skills

- [`qa-auditor`](../qa-auditor/SKILL.md) — Audit the codebase to find areas that need testing
- [`qa-automation`](../qa-automation/SKILL.md) — Automate the test execution pipeline
- [`webapp-testing`](../webapp-testing/SKILL.md) — End-to-end web application testing
