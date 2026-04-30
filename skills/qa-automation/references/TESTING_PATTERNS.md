# Testing Patterns for QA Automation

## Overview

This document provides comprehensive testing patterns and best practices for implementing a pytest-based test suite. It covers test organization, fixture patterns, parametrization strategies, and advanced testing techniques.

## Test Organization Patterns

### 1. Test Directory Structure

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

### 2. Test Class Organization

```python
# test_customer_service.py
import pytest
from myapp.services.customer_service import CustomerService
from myapp.models.customer import Customer

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
            'phone': '+1234567890'
        }

    def test_create_customer_success(self, customer_service, valid_customer_data):
        """Test successful customer creation"""
        result = customer_service.create_customer(valid_customer_data)

        assert result.success is True
        assert result.customer.name == 'John Doe'
        assert result.customer.email == 'john@example.com'

    def test_create_customer_duplicate_email(self, customer_service, valid_customer_data):
        """Test customer creation with duplicate email"""
        # First creation should succeed
        customer_service.create_customer(valid_customer_data)

        # Second creation with same email should fail
        with pytest.raises(ValueError, match="Email already exists"):
            customer_service.create_customer(valid_customer_data)

    @pytest.mark.parametrize("invalid_email", [
        "invalid",
        "@invalid",
        "invalid@",
        "invalid@.com",
        "",
        None
    ])
    def test_create_customer_invalid_email(self, customer_service, valid_customer_data, invalid_email):
        """Test customer creation with invalid email formats"""
        invalid_data = valid_customer_data.copy()
        invalid_data['email'] = invalid_email

        with pytest.raises(ValueError, match="Invalid email format"):
            customer_service.create_customer(invalid_data)
```

## Fixture Patterns

### 1. Session-Scoped Fixtures

```python
# conftest.py
import pytest
import tempfile
import shutil
from myapp.database import Database
from myapp.config import Config

@pytest.fixture(scope="session")
def test_config():
    """Configuration for testing environment"""
    config = Config()
    config.DATABASE_URL = "sqlite:///test.db"
    config.TESTING = True
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
    db.close()
```

### 2. Factory Fixtures

```python
# fixtures/customer_factory.py
import pytest
import factory
from myapp.models.customer import Customer
from myapp.models.ticket import Ticket

class CustomerFactory(factory.Factory):
    class Meta:
        model = Customer

    name = factory.Faker('name')
    email = factory.Faker('email')
    phone = factory.Faker('phone_number')

class TicketFactory(factory.Factory):
    class Meta:
        model = Ticket

    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('paragraph')
    priority = factory.Iterator(['low', 'medium', 'high'])

@pytest.fixture
def customer_factory():
    """Factory fixture for creating customers"""
    return CustomerFactory

@pytest.fixture
def ticket_factory():
    """Factory fixture for creating tickets"""
    return TicketFactory

# Usage in tests
def test_customer_with_factory(customer_factory):
    """Test using customer factory"""
    customer = customer_factory.create(name="Test User", email="test@example.com")

    assert customer.name == "Test User"
    assert customer.email == "test@example.com"
```

### 3. Dependency Injection Fixtures

```python
# fixtures/mock_services.py
import pytest
from unittest.mock import Mock, AsyncMock
from myapp.services.email_service import EmailService
from myapp.services.sms_service import SMSService

@pytest.fixture
def mock_email_service():
    """Mock email service for testing"""
    mock = Mock(spec=EmailService)
    mock.send_email.return_value = True
    return mock

@pytest.fixture
def mock_sms_service():
    """Mock SMS service for testing"""
    mock = Mock(spec=SMSService)
    mock.send_sms.return_value = True
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
```

## Parametrization Patterns

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
        assert validate_email(email) is False
```

### 2. Complex Parametrization with Ids

```python
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
    service = CustomerService()

    with pytest.raises(ValueError, match=expected_error):
        service.create_customer(customer_data)
```

### 3. Indirect Parametrization

```python
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
    indirect=["customer_data"]
)
def test_multiple_customers_creation(customer_data):
    """Test creating multiple customers with different data"""
    service = CustomerService()
    result = service.create_customer(customer_data)

    assert result.success is True
    assert result.customer.name == customer_data["name"]
    assert result.customer.email == customer_data["email"]
```

## Advanced Testing Patterns

### 1. Property-Based Testing

```python
import pytest
from hypothesis import given, strategies as st

@given(
    name=st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), min_size=1, max_size=100),
    email=st.emails(),
    phone=st.from_regex(r'^\+[1-9]\d{1,14}$')
)
def test_customer_creation_with_random_valid_data(name, email, phone):
    """Property-based test for customer creation with random valid data"""
    service = CustomerService()
    customer_data = {
        'name': name,
        'email': email,
        'phone': phone
    }

    result = service.create_customer(customer_data)

    assert result.success is True
    assert result.customer.name == name
    assert result.customer.email == email
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

### 3. Test Doubles and Mocking Patterns

```python
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from myapp.services.notification_service import NotificationService

class TestNotificationService:
    """Test notification service with various mocking patterns"""

    def test_send_notification_success(self):
        """Test successful notification sending"""
        service = NotificationService()
        mock_email_client = Mock()
        mock_sms_client = Mock()

        # Configure mocks
        mock_email_client.send.return_value = True
        mock_sms_client.send.return_value = True

        # Inject mocks
        service.email_client = mock_email_client
        service.sms_client = mock_sms_client

        result = service.send_notification(
            customer_id=1,
            message="Test message",
            channels=['email', 'sms']
        )

        assert result.success is True
        mock_email_client.send.assert_called_once()
        mock_sms_client.send.assert_called_once()

    @patch('myapp.services.notification_service.EmailClient')
    @patch('myapp.services.notification_service.SMSClient')
    def test_send_notification_with_context_manager(self, mock_sms_class, mock_email_class):
        """Test notification sending with patch decorator"""
        # Configure mock classes
        mock_email_instance = Mock()
        mock_email_instance.send.return_value = True
        mock_email_class.return_value = mock_email_instance

        mock_sms_instance = Mock()
        mock_sms_instance.send.return_value = True
        mock_sms_class.return_value = mock_sms_instance

        service = NotificationService()
        result = service.send_notification(
            customer_id=1,
            message="Test message",
            channels=['email', 'sms']
        )

        assert result.success is True
        mock_email_instance.send.assert_called_once()
        mock_sms_instance.send.assert_called_once()

    def test_send_notification_partial_failure(self):
        """Test notification sending with partial failure"""
        service = NotificationService()
        mock_email_client = Mock()
        mock_sms_client = Mock()

        # Configure one to fail
        mock_email_client.send.return_value = True
        mock_sms_client.send.side_effect = Exception("SMS service unavailable")

        service.email_client = mock_email_client
        service.sms_client = mock_sms_client

        result = service.send_notification(
            customer_id=1,
            message="Test message",
            channels=['email', 'sms']
        )

        # Should still succeed as email succeeded
        assert result.success is True
        assert result.partial_failure is True
        assert "sms" in result.failed_channels
```

## Performance Testing Patterns

### 1. Timing Assertions

```python
import pytest
import time
from pytest_benchmark.fixture import benchmark

def test_customer_creation_performance(benchmark_db):
    """Test customer creation performance with timing assertions"""
    service = CustomerService(database=benchmark_db)

    def create_customer():
        return service.create_customer({
            'name': 'Performance Test User',
            'email': 'perf@example.com',
            'phone': '+1234567890'
        })

    # Use pytest-benchmark for accurate timing
    result = benchmark(create_customer)

    # Assert performance requirements
    assert result.success is True
    assert benchmark.stats['mean'] < 0.1  # Less than 100ms average

def test_concurrent_operations_timing():
    """Test timing of concurrent operations"""
    import asyncio
    import time

    async def simulate_concurrent_requests(service, num_requests=10):
        start_time = time.time()

        async def make_request(i):
            return service.process_request({
                'request_id': i,
                'data': f'data_{i}'
            })

        tasks = [make_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        return results, total_time

    # Test concurrent request handling
    service = SomeService()
    results, total_time = asyncio.run(simulate_concurrent_requests(service, 10))

    # Assert timing requirements
    assert total_time < 5.0  # All requests should complete within 5 seconds
    assert len(results) == 10  # All requests should complete
```

### 2. Memory Usage Testing

```python
import pytest
from pytest_leaks.plugin import leaks

@leaks.leakcheck
def test_no_memory_leaks_in_customer_creation():
    """Test that customer creation doesn't leak memory"""
    service = CustomerService()

    for i in range(1000):
        customer_data = {
            'name': f'Test User {i}',
            'email': f'test{i}@example.com',
            'phone': f'+123456789{i:02d}'
        }
        result = service.create_customer(customer_data)
        assert result.success is True

def test_memory_usage_bounds():
    """Test memory usage stays within bounds"""
    import psutil
    import os

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    service = CustomerService()

    # Create many customers
    for i in range(10000):
        customer_data = {
            'name': f'Test User {i}',
            'email': f'test{i}@example.com',
            'phone': f'+123456789{i:02d}'
        }
        service.create_customer(customer_data)

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    # Assert memory increase is reasonable
    assert memory_increase < 100  # Less than 100MB increase
```

This comprehensive testing patterns guide provides all the necessary patterns and best practices for implementing effective pytest-based tests.