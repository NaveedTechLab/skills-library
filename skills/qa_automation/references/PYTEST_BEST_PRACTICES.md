# Pytest Best Practices for QA Automation

## Overview

This document provides comprehensive best practices for implementing pytest-based test suites. It covers test organization, fixture usage, configuration, and advanced testing techniques.

## Pytest Configuration and Setup

### 1. Pytest Configuration File

```ini
# pytest.ini
[tool:pytest]
# Test discovery and execution
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    # Verbose output and traceback format
    -v
    --tb=short
    # Strict markers and configuration
    --strict-markers
    --strict-config
    # Coverage configuration
    --cov=myapp
    --cov-report=html
    --cov-report=term-missing
    --cov-report=xml
    # JUnit XML for CI/CD
    --junitxml=reports/junit.xml
    # Performance and timeout settings
    --timeout=30
    # Parallel execution (if pytest-xdist is installed)
    # -n auto

# Custom markers for categorization
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    performance: marks tests as performance tests
    edge_case: marks tests as edge case tests
    smoke: marks tests as smoke tests
    regression: marks tests as regression tests
    critical: marks tests as critical functionality

# Filter warnings
filterwarnings =
    error
    ignore::DeprecationWarning
    ignore::UserWarning
    ignore::ResourceWarning

# Timeout settings
timeout = 30
timeout_method = thread
```

### 2. Advanced Pytest Configuration

```python
# pytest_configure.py or conftest.py
import pytest
import os
from pathlib import Path

def pytest_configure(config):
    """Configure pytest with custom settings"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "critical: marks tests as critical functionality"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test items during collection"""
    # Add markers based on test file location
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "slow" in item.keywords:
            item.add_marker(pytest.mark.skipif(
                config.getoption("-x"),
                reason="Skipping slow tests when using -x flag"
            ))

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    """Hook to add custom behavior during test execution"""
    # Custom setup before test
    print(f"Starting test: {item.nodeid}")

    # Yield control back to pytest
    outcome = yield

    # Custom teardown after test
    print(f"Completed test: {item.nodeid}")

    return outcome
```

## Test Organization and Structure

### 1. Directory Structure

```
tests/
├── unit/
│   ├── test_models/
│   │   ├── test_customer.py
│   │   ├── test_ticket.py
│   │   └── test_user.py
│   ├── test_services/
│   │   ├── test_customer_service.py
│   │   └── test_ticket_service.py
│   └── test_utils/
│       ├── test_validators.py
│       └── test_helpers.py
├── integration/
│   ├── test_api/
│   │   ├── test_customer_endpoints.py
│   │   └── test_ticket_endpoints.py
│   ├── test_database/
│   │   ├── test_customer_repository.py
│   │   └── test_ticket_repository.py
│   └── test_external/
│       ├── test_email_service.py
│       └── test_sms_service.py
├── e2e/
│   ├── test_web_ui/
│   │   ├── test_customer_flow.py
│   │   └── test_ticket_flow.py
│   └── test_mobile_app/
│       └── test_authentication.py
├── performance/
│   ├── test_load.py
│   ├── test_stress.py
│   └── test_scalability.py
├── edge_cases/
│   ├── test_boundary_conditions.py
│   ├── test_error_scenarios.py
│   └── test_fuzzy_inputs.py
├── conftest.py
├── fixtures/
│   ├── __init__.py
│   ├── database_fixtures.py
│   ├── api_fixtures.py
│   └── mock_fixtures.py
└── utils/
    ├── __init__.py
    ├── test_helpers.py
    └── data_generators.py
```

### 2. Test File Structure

```python
# tests/unit/test_customer_service.py
"""
Customer Service Unit Tests

Tests for the CustomerService class functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from myapp.services.customer_service import CustomerService
from myapp.models.customer import Customer
from myapp.exceptions import CustomerValidationError, DuplicateCustomerError


class TestCustomerService:
    """Test suite for CustomerService class"""

    @pytest.fixture
    def customer_service(self):
        """Fixture for CustomerService instance"""
        return CustomerService()

    @pytest.fixture
    def valid_customer_data(self):
        """Fixture for valid customer data"""
        return {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '+1234567890',
            'address': '123 Main St'
        }

    def test_create_customer_success(self, customer_service, valid_customer_data):
        """Test successful customer creation"""
        result = customer_service.create_customer(valid_customer_data)

        assert result.success is True
        assert result.customer is not None
        assert result.customer.name == 'John Doe'
        assert result.customer.email == 'john@example.com'

    @pytest.mark.parametrize("invalid_field,invalid_value,error_message", [
        ("name", "", "Name cannot be empty"),
        ("email", "invalid-email", "Invalid email format"),
        ("phone", "invalid-phone", "Invalid phone format"),
    ])
    def test_create_customer_validation_errors(
        self, customer_service, valid_customer_data,
        invalid_field, invalid_value, error_message
    ):
        """Test customer creation with various validation errors"""
        invalid_data = valid_customer_data.copy()
        invalid_data[invalid_field] = invalid_value

        with pytest.raises(CustomerValidationError, match=error_message):
            customer_service.create_customer(invalid_data)

    @pytest.mark.integration
    def test_create_customer_database_integration(self, customer_service, valid_customer_data):
        """Integration test for customer creation with database"""
        # This test requires database connection
        result = customer_service.create_customer(valid_customer_data)

        assert result.success is True
        assert result.customer.id is not None

        # Verify customer exists in database
        retrieved = customer_service.get_customer(result.customer.id)
        assert retrieved is not None
        assert retrieved.name == valid_customer_data['name']

    @pytest.mark.performance
    def test_customer_creation_performance(self, benchmark, customer_service, valid_customer_data):
        """Performance test for customer creation"""
        def create_customer():
            return customer_service.create_customer(valid_customer_data)

        result = benchmark(create_customer)
        assert result.success is True

        # Assert performance requirements
        assert benchmark.stats['mean'] < 0.1  # Less than 100ms average


class TestCustomerServiceEdgeCases:
    """Edge case tests for CustomerService"""

    @pytest.mark.edge_case
    @pytest.mark.parametrize("name,expected_validity", [
        ("", False),
        ("A", True),
        ("A" * 255, True),
        ("A" * 256, False),
        ("Special!@#$%^&*()", True),
        ("Tab\tCharacter", True),
        ("New\nLine", True),
    ])
    def test_name_boundary_conditions(self, name, expected_validity):
        """Test name validation at boundary conditions"""
        from myapp.utils.validators import validate_name

        if expected_validity:
            assert validate_name(name) is True
        else:
            with pytest.raises(ValueError):
                validate_name(name)
```

## Advanced Fixture Patterns

### 1. Session-Scoped Fixtures

```python
# conftest.py
import pytest
import tempfile
import shutil
from myapp.database import Database
from myapp.config import Config
from myapp.services.cache_service import CacheService

@pytest.fixture(scope="session")
def test_config():
    """Configuration for testing environment"""
    config = Config()
    config.DATABASE_URL = "sqlite:///test.db"
    config.CACHE_URL = "redis://localhost:6379/9"  # Test DB 9
    config.TESTING = True
    config.DEBUG = False
    return config

@pytest.fixture(scope="session")
def temp_dir():
    """Temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture(scope="session")
def test_database(test_config):
    """Shared test database instance"""
    db = Database(config=test_config)
    db.create_tables()
    yield db
    db.drop_tables()
    db.close()

@pytest.fixture(scope="session")
def test_cache():
    """Shared test cache instance"""
    cache = CacheService(url="redis://localhost:6379/9")
    yield cache
    cache.flush_all()

@pytest.fixture(scope="session")
def api_client(test_config):
    """API client for integration tests"""
    from myapp.api import create_app
    from flask.testing import FlaskClient

    app = create_app(test_config)

    with app.test_client() as client:
        yield client
```

### 2. Factory Fixtures

```python
# fixtures/factories.py
import pytest
import factory
from myapp.models.customer import Customer
from myapp.models.ticket import Ticket
from myapp.models.user import User
from faker import Faker

fake = Faker()

class CustomerFactory(factory.Factory):
    class Meta:
        model = Customer

    id = factory.Sequence(lambda n: n)
    name = factory.LazyAttribute(lambda _: fake.name())
    email = factory.LazyAttribute(lambda _: fake.email())
    phone = factory.LazyAttribute(lambda _: fake.phone_number())
    address = factory.LazyAttribute(lambda _: fake.address())
    created_at = factory.LazyAttribute(lambda _: fake.date_time_between(start_date='-1y'))

class TicketFactory(factory.Factory):
    class Meta:
        model = Ticket

    id = factory.Sequence(lambda n: n)
    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=4))
    description = factory.LazyAttribute(lambda _: fake.paragraph())
    priority = factory.LazyAttribute(lambda _: fake.random_element(elements=['low', 'medium', 'high']))
    status = factory.LazyAttribute(lambda _: 'open')
    customer_id = factory.Sequence(lambda n: n)

class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Sequence(lambda n: n)
    username = factory.LazyAttribute(lambda _: fake.user_name())
    email = factory.LazyAttribute(lambda _: fake.email())
    is_active = True
    created_at = factory.LazyAttribute(lambda _: fake.date_time_between(start_date='-6M'))

@pytest.fixture
def customer_factory():
    """Customer factory fixture"""
    return CustomerFactory

@pytest.fixture
def ticket_factory():
    """Ticket factory fixture"""
    return TicketFactory

@pytest.fixture
def user_factory():
    """User factory fixture"""
    return UserFactory

# Usage example
def test_customer_with_factory(customer_factory):
    """Test using customer factory"""
    customer = customer_factory.create(name="Test User", email="test@example.com")

    assert customer.name == "Test User"
    assert customer.email == "test@example.com"
    assert customer.id is not None
```

### 3. Dependency Injection Fixtures

```python
# fixtures/mocks.py
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from myapp.services.email_service import EmailService
from myapp.services.sms_service import SMSService
from myapp.services.payment_service import PaymentService

@pytest.fixture
def mock_email_service():
    """Mock email service for testing"""
    mock = Mock(spec=EmailService)
    mock.send_email.return_value = True
    mock.send_bulk_emails.return_value = {"sent": 10, "failed": 0}
    return mock

@pytest.fixture
def mock_sms_service():
    """Mock SMS service for testing"""
    mock = Mock(spec=SMSService)
    mock.send_sms.return_value = True
    mock.send_bulk_sms.return_value = {"sent": 5, "failed": 0}
    return mock

@pytest.fixture
def mock_payment_service():
    """Mock payment service for testing"""
    mock = Mock(spec=PaymentService)
    mock.process_payment.return_value = {"status": "success", "transaction_id": "txn_123"}
    mock.refund_payment.return_value = {"status": "success", "refund_id": "ref_456"}
    return mock

@pytest.fixture
def customer_service_with_mocks(mock_email_service, mock_sms_service):
    """Customer service with mocked dependencies"""
    from myapp.services.customer_service import CustomerService

    service = CustomerService(
        email_service=mock_email_service,
        sms_service=mock_sms_service
    )
    return service

# Advanced mock fixture with behavior
@pytest.fixture
def configurable_mock_service():
    """Configurable mock service with dynamic behavior"""
    def _create_mock(**config):
        mock = Mock()

        # Configure behavior based on config
        if 'send_success' in config:
            mock.send.return_value = config['send_success']
        else:
            mock.send.return_value = True

        if 'raise_exception' in config:
            mock.send.side_effect = config['raise_exception']

        if 'call_count' in config:
            original_send = mock.send
            call_count = 0

            def counting_send(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count > config['call_count']:
                    raise Exception("Too many calls")
                return original_send(*args, **kwargs)

            mock.send = counting_send

        return mock

    return _create_mock
```

## Parametrization and Data-Driven Testing

### 1. Simple Parametrization

```python
import pytest

@pytest.mark.parametrize("email,expected_validity", [
    ("valid@example.com", True),
    ("user@domain.co.uk", True),
    ("invalid", False),
    ("@invalid.com", False),
    ("invalid@", False),
    ("", False),
    (None, False),
])
def test_email_validation(email, expected_validity):
    """Test email validation with various inputs"""
    from myapp.utils.validators import validate_email

    if expected_validity:
        assert validate_email(email) is True
    else:
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email(email)

@pytest.mark.parametrize(
    "customer_data,expected_error",
    [
        ({"name": "", "email": "test@example.com"}, "Name cannot be empty"),
        ({"name": "Valid Name", "email": "invalid"}, "Invalid email format"),
        ({"name": "Valid Name", "email": "", "phone": "+1234567890"}, "Email cannot be empty"),
        ({"name": "Valid Name", "email": "test@example.com", "phone": "invalid"}, "Invalid phone format"),
    ],
    ids=[
        "empty_name",
        "invalid_email",
        "empty_email",
        "invalid_phone"
    ]
)
def test_customer_creation_validation_errors(customer_data, expected_error):
    """Test customer creation with various validation errors"""
    from myapp.services.customer_service import CustomerService

    service = CustomerService()

    with pytest.raises(ValueError, match=expected_error):
        service.create_customer(customer_data)
```

### 2. Complex Parametrization

```python
# Complex parametrization with fixtures
@pytest.fixture
def customer_data(request):
    """Parameterized customer data fixture"""
    return request.param

@pytest.mark.parametrize(
    "customer_data",
    [
        {"name": "John Doe", "email": "john@example.com", "phone": "+1234567890"},
        {"name": "Jane Smith", "email": "jane@example.com", "phone": "+0987654321"},
        {"name": "Bob Johnson", "email": "bob@example.com", "phone": "+1122334455"},
    ],
    indirect=["customer_data"],
    ids=["john_doe", "jane_smith", "bob_johnson"]
)
def test_multiple_customers_creation(customer_data):
    """Test creating multiple customers with different data"""
    from myapp.services.customer_service import CustomerService

    service = CustomerService()
    result = service.create_customer(customer_data)

    assert result.success is True
    assert result.customer.name == customer_data["name"]
    assert result.customer.email == customer_data["email"]

# Parametrization with external data
import json

def load_test_data(filename):
    """Load test data from external file"""
    with open(f"tests/data/{filename}", "r") as f:
        return json.load(f)

@pytest.mark.parametrize(
    "test_case",
    load_test_data("customer_validation_cases.json"),
    ids=lambda x: x.get("id", "unnamed_case")
)
def test_customer_validation_from_file(test_case):
    """Test customer validation with data from external file"""
    from myapp.services.customer_service import CustomerService

    service = CustomerService()

    if test_case["should_pass"]:
        result = service.create_customer(test_case["input"])
        assert result.success is True
    else:
        with pytest.raises(Exception, match=test_case["expected_error"]):
            service.create_customer(test_case["input"])
```

## Advanced Testing Patterns

### 1. Property-Based Testing

```python
import pytest
from hypothesis import given, strategies as st
from hypothesis.extra.pytz import timezones
import datetime

@given(
    name=st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), min_size=1, max_size=100),
    email=st.emails(),
    phone=st.from_regex(r'^\+[1-9]\d{1,14}$'),
    timezone=st.one_of(st.none(), timezones())
)
def test_customer_creation_with_random_valid_data(name, email, phone, timezone):
    """Property-based test for customer creation with random valid data"""
    from myapp.services.customer_service import CustomerService

    service = CustomerService()
    customer_data = {
        'name': name,
        'email': email,
        'phone': phone,
        'timezone': str(timezone) if timezone else None
    }

    result = service.create_customer(customer_data)

    assert result.success is True
    assert result.customer.name == name
    assert result.customer.email == email

@given(
    invalid_email=st.text().filter(lambda x: "@" not in x or "." not in x.split("@")[-1]),
    invalid_phone=st.text().filter(lambda x: not x.startswith("+") or not x[1:].isdigit())
)
def test_customer_creation_rejects_invalid_data(invalid_email, invalid_phone):
    """Property-based test that invalid data is rejected"""
    from myapp.services.customer_service import CustomerService

    service = CustomerService()

    # Test invalid email
    with pytest.raises(ValueError):
        service.create_customer({
            'name': 'Test User',
            'email': invalid_email,
            'phone': '+1234567890'
        })

    # Test invalid phone
    with pytest.raises(ValueError):
        service.create_customer({
            'name': 'Test User',
            'email': 'valid@example.com',
            'phone': invalid_phone
        })
```

### 2. State-Based Testing

```python
import pytest
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

class CustomerState(Enum):
    CREATED = "created"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"

@dataclass
class CustomerTransition:
    from_state: CustomerState
    action: str
    to_state: CustomerState
    allowed: bool

class TestCustomerStateTransitions:
    """Test customer state transitions"""

    @pytest.fixture
    def state_transitions(self):
        """Define valid state transitions"""
        return [
            CustomerTransition(CustomerState.CREATED, "activate", CustomerState.ACTIVE, True),
            CustomerTransition(CustomerState.ACTIVE, "deactivate", CustomerState.INACTIVE, True),
            CustomerTransition(CustomerState.INACTIVE, "activate", CustomerState.ACTIVE, True),
            CustomerTransition(CustomerState.ACTIVE, "delete", CustomerState.DELETED, True),
            CustomerTransition(CustomerState.CREATED, "delete", CustomerState.DELETED, True),
            # Invalid transitions
            CustomerTransition(CustomerState.CREATED, "deactivate", CustomerState.INACTIVE, False),
            CustomerTransition(CustomerState.DELETED, "activate", CustomerState.ACTIVE, False),
        ]

    @pytest.mark.parametrize("transition", [
        CustomerTransition(CustomerState.CREATED, "activate", CustomerState.ACTIVE, True),
        CustomerTransition(CustomerState.ACTIVE, "deactivate", CustomerState.INACTIVE, True),
        CustomerTransition(CustomerState.INACTIVE, "activate", CustomerState.ACTIVE, True),
        CustomerTransition(CustomerState.ACTIVE, "delete", CustomerState.DELETED, True),
        CustomerTransition(CustomerState.CREATED, "delete", CustomerState.DELETED, True),
        CustomerTransition(CustomerState.CREATED, "deactivate", CustomerState.INACTIVE, False),
        CustomerTransition(CustomerState.DELETED, "activate", CustomerState.ACTIVE, False),
    ])
    def test_customer_state_transitions(self, customer_service, transition):
        """Test customer state transitions"""
        # Create initial customer
        customer = customer_service.create_customer({
            'name': 'Test User',
            'email': 'test@example.com',
            'phone': '+1234567890'
        }).customer

        # Set initial state if needed
        if transition.from_state != CustomerState.CREATED:
            # Transition to the required state
            if transition.from_state == CustomerState.ACTIVE:
                customer.activate()
            elif transition.from_state == CustomerState.INACTIVE:
                customer.activate()
                customer.deactivate()
            elif transition.from_state == CustomerState.DELETED:
                customer.delete()

        # Perform the action
        if transition.action == "activate":
            method = customer.activate
        elif transition.action == "deactivate":
            method = customer.deactivate
        elif transition.action == "delete":
            method = customer.delete
        else:
            raise ValueError(f"Unknown action: {transition.action}")

        # Verify the result
        if transition.allowed:
            method()
            assert customer.state == transition.to_state.value
        else:
            with pytest.raises(ValueError):
                method()
```

## Performance and Profiling

### 1. Performance Testing

```python
import pytest
import time
from pytest_benchmark.fixture import benchmark
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

def test_customer_creation_performance(benchmark, customer_service):
    """Test customer creation performance with pytest-benchmark"""
    def create_customer():
        return customer_service.create_customer({
            'name': 'Performance Test User',
            'email': 'perf@example.com',
            'phone': '+1234567890'
        })

    result = benchmark(create_customer)

    assert result.success is True
    # Assert performance requirements
    assert benchmark.stats['mean'] < 0.1  # Less than 100ms average

@pytest.mark.performance
def test_concurrent_customer_creation_performance(customer_service):
    """Test concurrent customer creation performance"""
    import time

    def create_multiple_customers(num_customers):
        start_time = time.time()

        for i in range(num_customers):
            customer_service.create_customer({
                'name': f'Concurrent User {i}',
                'email': f'concurrent{i}@example.com',
                'phone': f'+123456789{i:02d}'
            })

        end_time = time.time()
        return end_time - start_time

    duration = create_multiple_customers(50)  # Create 50 customers

    # Assert reasonable performance
    assert duration < 5.0  # Should complete in under 5 seconds

@pytest.mark.performance
def test_api_performance_under_load():
    """Test API performance under load"""
    import asyncio
    import aiohttp
    import time

    async def make_request(session, url, payload):
        start_time = time.perf_counter()
        try:
            async with session.post(url, json=payload) as response:
                response_time = time.perf_counter() - start_time
                return {
                    'status': response.status,
                    'response_time': response_time,
                    'success': response.status == 200
                }
        except Exception as e:
            return {
                'status': 500,
                'response_time': time.perf_counter() - start_time,
                'success': False,
                'error': str(e)
            }

    async def run_performance_test():
        url = "https://test-api.myapp.com/customers"
        payload = {
            'name': 'Load Test User',
            'email': 'load@test.com',
            'phone': '+1234567890'
        }

        async with aiohttp.ClientSession() as session:
            # Make 20 concurrent requests
            tasks = [make_request(session, url, payload) for _ in range(20)]
            results = await asyncio.gather(*tasks)

        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        response_times = [r['response_time'] for r in results]

        # Performance assertions
        assert len(successful_requests) >= len(results) * 0.95  # 95% success rate
        assert sum(response_times) / len(response_times) < 0.5  # Mean response time < 500ms
        assert max(response_times) < 2.0  # Max response time < 2s

        return {
            'total_requests': len(results),
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'success_rate': len(successful_requests) / len(results),
            'mean_response_time': sum(response_times) / len(response_times),
            'max_response_time': max(response_times)
        }

    # Run the performance test
    result = asyncio.run(run_performance_test())
    print(f"Performance Test Results: {result}")
```

### 2. Memory and Resource Usage Testing

```python
import pytest
import psutil
import os
from pytest_leaks.plugin import leaks

@leaks.leakcheck
def test_no_memory_leaks_in_customer_creation(customer_service):
    """Test that customer creation doesn't leak memory"""
    for i in range(1000):
        customer_data = {
            'name': f'Test User {i}',
            'email': f'test{i}@example.com',
            'phone': f'+123456789{i:02d}'
        }
        result = customer_service.create_customer(customer_data)
        assert result.success is True

def test_memory_usage_bounds(customer_service):
    """Test memory usage stays within bounds"""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Create many customers
    for i in range(10000):
        customer_data = {
            'name': f'Test User {i}',
            'email': f'test{i}@example.com',
            'phone': f'+123456789{i:02d}'
        }
        customer_service.create_customer(customer_data)

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    # Assert memory increase is reasonable
    assert memory_increase < 100  # Less than 100MB increase for 10k customers
```

## Test Reporting and Documentation

### 1. Custom Test Reports

```python
# conftest.py
import pytest
import json
from datetime import datetime
from pathlib import Path

class TestReporter:
    """Custom test reporter"""

    def __init__(self, config):
        self.config = config
        self.results = []
        self.start_time = None

    def pytest_configure(self, config):
        self.output_file = config.getoption("--test-report", default="test_report.json")

    def pytest_sessionstart(self, session):
        self.start_time = datetime.now()

    def pytest_sessionfinish(self, session):
        duration = datetime.now() - self.start_time

        report = {
            'timestamp': datetime.now().isoformat(),
            'duration': duration.total_seconds(),
            'test_results': self.results,
            'summary': {
                'total': len(self.results),
                'passed': len([r for r in self.results if r['outcome'] == 'passed']),
                'failed': len([r for r in self.results if r['outcome'] == 'failed']),
                'skipped': len([r for r in self.results if r['outcome'] == 'skipped']),
            }
        }

        # Write report to file
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Test report written to {self.output_file}")

    def pytest_runtest_logreport(self, report):
        if report.when == 'call':  # Only log the call phase
            self.results.append({
                'nodeid': report.nodeid,
                'outcome': report.outcome,
                'duration': getattr(report, 'duration', 0),
                'failed': report.failed,
                'passed': report.passed,
                'skipped': report.skipped,
            })

def pytest_configure(config):
    """Add custom command line option"""
    config.addinivalue_line(
        "markers", "report: mark test to be included in custom report"
    )

def pytest_addoption(parser):
    """Add command line options"""
    parser.addoption(
        "--test-report",
        action="store",
        default="test_report.json",
        help="Path to output test report JSON file"
    )

@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Configure custom reporter"""
    reporter = TestReporter(config)
    config.pluginmanager.register(reporter)
```

### 2. Documentation and Test Descriptions

```python
import pytest

def test_customer_creation_with_docstring():
    """
    Test customer creation functionality.

    This test verifies that the customer service can successfully
    create a new customer with valid data. It checks that all
    required fields are properly stored and that the customer
    receives a unique identifier.

    Expected behavior:
    - Customer object is returned with success flag set to True
    - Customer has a valid ID assigned
    - All input data is preserved in the created customer

    Test data:
    - Name: "John Doe"
    - Email: "john@example.com"
    - Phone: "+1234567890"

    Success criteria:
    - result.success == True
    - result.customer.id is not None
    - result.customer.name == "John Doe"
    """
    from myapp.services.customer_service import CustomerService

    service = CustomerService()
    result = service.create_customer({
        'name': 'John Doe',
        'email': 'john@example.com',
        'phone': '+1234567890'
    })

    assert result.success is True
    assert result.customer.id is not None
    assert result.customer.name == "John Doe"

@pytest.mark.documentation
def test_api_endpoint_documentation():
    """
    API Endpoint: POST /api/customers
    Description: Create a new customer record
    Authentication: Required - Bearer token
    Rate Limit: 100 requests per minute per IP

    Request Body:
    {
        "name": "string, required, max 255 chars",
        "email": "string, required, valid email format",
        "phone": "string, required, E.164 format",
        "address": "string, optional, max 500 chars"
    }

    Response Codes:
    - 201: Created - Customer successfully created
    - 400: Bad Request - Invalid input data
    - 401: Unauthorized - Missing/invalid token
    - 409: Conflict - Email already exists
    - 429: Too Many Requests - Rate limit exceeded
    - 500: Internal Server Error - Unexpected error

    Example Request:
    POST /api/customers
    Authorization: Bearer <token>
    Content-Type: application/json

    {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890"
    }

    Example Response (201):
    {
        "id": "uuid-string",
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "created_at": "2023-01-01T00:00:00Z"
    }
    """
    # Test implementation would go here
    pass
```

## CI/CD Integration

### 1. GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run unit tests
      run: |
        pytest tests/unit --cov=myapp --cov-report=xml --junitxml=reports/unit-tests.xml

    - name: Run integration tests
      run: |
        pytest tests/integration --junitxml=reports/integration-tests.xml

    - name: Run performance tests
      run: |
        pytest tests/performance --benchmark-only --benchmark-json=reports/benchmark.json

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results-${{ matrix.python-version }}
        path: reports/
```

### 2. Test Coverage Configuration

```python
# .coveragerc
[run]
source = myapp
omit =
    */tests/*
    */venv/*
    */env/*
    */__pycache__/*
    */migrations/*
    setup.py
    conftest.py

[report]
# Regexes for lines to exclude from consideration
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:

precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov
```

This comprehensive pytest best practices guide provides all the necessary techniques and patterns for implementing effective pytest-based test suites with proper organization, advanced features, and CI/CD integration.