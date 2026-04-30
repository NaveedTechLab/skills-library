---
name: qa_automation
description: Builds the pytest-based test suite for the transition from prototype to production. Implements E2E tests, edge-case validation, and performance metric tracking (latency, accuracy, escalation rates). Use when Claude needs to create or modify pytest-based test suites, implement E2E tests, validate edge cases, or track performance metrics like latency, accuracy, and escalation rates.
---

# QA Automation Skill

## Overview

This skill provides comprehensive guidance for building a pytest-based test suite for transitioning from prototype to production. It covers end-to-end (E2E) tests, edge-case validation, and performance metric tracking including latency, accuracy, and escalation rates.

## Core Components

### Test Architecture

The QA automation system implements a multi-layered testing approach:

1. **Unit Tests**: Component-level validation
2. **Integration Tests**: Module interaction validation
3. **End-to-End Tests**: Full workflow validation
4. **Performance Tests**: Latency, throughput, and scalability validation
5. **Edge Case Tests**: Boundary condition and error scenario validation
6. **Regression Tests**: Ensuring existing functionality remains intact

### Testing Framework

- Primary framework: pytest
- Test organization: fixture-based with parametrization
- Reporting: Allure/JUnit XML for CI/CD integration
- Mocking: pytest-mock for dependency isolation
- Coverage: pytest-cov for measurement

## Test Categories

### 1. Unit Tests

Unit tests focus on individual functions, methods, and classes in isolation.

```python
import pytest
from unittest.mock import Mock, patch
from myapp.services.customer_service import CustomerService

def test_create_customer_success():
    """Test successful customer creation"""
    service = CustomerService()
    customer_data = {
        'name': 'John Doe',
        'email': 'john@example.com',
        'phone': '+1234567890'
    }

    result = service.create_customer(customer_data)

    assert result.success == True
    assert result.customer.id is not None
    assert result.customer.name == 'John Doe'

def test_create_customer_invalid_email():
    """Test customer creation with invalid email"""
    service = CustomerService()
    customer_data = {
        'name': 'John Doe',
        'email': 'invalid-email',
        'phone': '+1234567890'
    }

    with pytest.raises(ValueError, match="Invalid email format"):
        service.create_customer(customer_data)
```

### 2. Integration Tests

Integration tests validate the interaction between multiple components.

```python
import pytest
from myapp.database import Database
from myapp.services.customer_service import CustomerService
from myapp.services.ticket_service import TicketService

@pytest.fixture
def database():
    """Create a test database instance"""
    db = Database(test_mode=True)
    yield db
    db.cleanup()

@pytest.fixture
def customer_service(database):
    """Create a customer service with test database"""
    return CustomerService(database=database)

@pytest.fixture
def ticket_service(database):
    """Create a ticket service with test database"""
    return TicketService(database=database)

def test_customer_ticket_integration(customer_service, ticket_service):
    """Test creating a customer and associating a ticket"""
    # Create customer
    customer_data = {
        'name': 'Jane Smith',
        'email': 'jane@example.com',
        'phone': '+0987654321'
    }
    customer_result = customer_service.create_customer(customer_data)

    # Create ticket for customer
    ticket_data = {
        'customer_id': customer_result.customer.id,
        'subject': 'Support Request',
        'priority': 'medium'
    }
    ticket_result = ticket_service.create_ticket(ticket_data)

    # Verify relationship
    assert ticket_result.ticket.customer_id == customer_result.customer.id
    assert customer_result.customer.id is not None
    assert ticket_result.ticket.id is not None
```

### 3. End-to-End Tests

E2E tests simulate complete user workflows from start to finish.

```python
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture
def browser():
    """Setup browser for E2E testing"""
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

def test_customer_support_workflow(browser):
    """Full customer support workflow test"""
    browser.get("https://myapp.test/")

    # Navigate to contact form
    contact_button = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.ID, "contact-support"))
    )
    contact_button.click()

    # Fill out form
    name_field = browser.find_element(By.NAME, "customer_name")
    name_field.send_keys("Test User")

    email_field = browser.find_element(By.NAME, "customer_email")
    email_field.send_keys("test@example.com")

    message_field = browser.find_element(By.NAME, "message")
    message_field.send_keys("This is a test support request.")

    submit_button = browser.find_element(By.ID, "submit-ticket")
    submit_button.click()

    # Verify success message
    success_message = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
    )
    assert "Ticket created successfully" in success_message.text
```

## Edge Case Validation

### Boundary Conditions

Testing inputs at the limits of acceptable values:

```python
import pytest

@pytest.mark.parametrize("input_value,expected_error", [
    ("", "Name cannot be empty"),
    ("A" * 256, "Name too long"),
    ("Special!@#$%", "Invalid characters in name"),
    (None, "Name is required")
])
def test_customer_name_validation(input_value, expected_error):
    """Test customer name validation with boundary conditions"""
    service = CustomerService()
    customer_data = {
        'name': input_value,
        'email': 'test@example.com',
        'phone': '+1234567890'
    }

    with pytest.raises(ValueError, match=expected_error):
        service.create_customer(customer_data)

def test_edge_case_phone_numbers():
    """Test phone number validation with edge cases"""
    service = CustomerService()

    # Test invalid formats
    invalid_cases = [
        "123",  # Too short
        "12345678901234567890",  # Too long
        "abc-def-ghij",  # Invalid characters
        "+",  # Incomplete
    ]

    for invalid_phone in invalid_cases:
        with pytest.raises(ValueError):
            service.create_customer({
                'name': 'Test User',
                'email': 'test@example.com',
                'phone': invalid_phone
            })
```

### Error Scenarios

Testing system behavior under error conditions:

```python
import pytest
from unittest.mock import Mock, patch, MagicMock

def test_database_connection_failure():
    """Test behavior when database is unavailable"""
    with patch('myapp.database.Database.connect') as mock_connect:
        mock_connect.side_effect = ConnectionError("Database unavailable")

        service = CustomerService()

        with pytest.raises(ConnectionError):
            service.create_customer({
                'name': 'Test User',
                'email': 'test@example.com',
                'phone': '+1234567890'
            })

def test_concurrent_customer_creation():
    """Test handling of concurrent customer creation attempts"""
    import threading
    import time

    service = CustomerService()
    results = []
    errors = []

    def create_customer_thread(email_suffix):
        try:
            result = service.create_customer({
                'name': 'Concurrent User',
                'email': f'user{email_suffix}@example.com',
                'phone': f'+123456789{email_suffix}'
            })
            results.append(result)
        except Exception as e:
            errors.append(e)

    # Create multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=create_customer_thread, args=[i])
        threads.append(thread)

    # Start all threads
    start_time = time.time()
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    end_time = time.time()

    # Verify all operations completed
    assert len(results) + len(errors) == 5
    # Verify response time is acceptable
    assert (end_time - start_time) < 10.0  # Should complete within 10 seconds
```

## Performance Metric Tracking

### Latency Measurement

Tracking response times for various operations:

```python
import pytest
import time
from statistics import mean, median, stdev
from collections import defaultdict

class PerformanceTracker:
    def __init__(self):
        self.metrics = defaultdict(list)

    def record_latency(self, operation, duration):
        """Record latency for an operation"""
        self.metrics[operation].append(duration)

    def get_statistics(self, operation):
        """Get statistical measures for an operation"""
        durations = self.metrics[operation]
        if not durations:
            return {}

        return {
            'count': len(durations),
            'mean': mean(durations),
            'median': median(durations),
            'std_dev': stdev(durations) if len(durations) > 1 else 0,
            'min': min(durations),
            'max': max(durations),
            'p95': sorted(durations)[int(0.95 * len(durations))] if len(durations) > 0 else 0,
            'p99': sorted(durations)[int(0.99 * len(durations))] if len(durations) > 0 else 0
        }

PERFORMANCE_TRACKER = PerformanceTracker()

def measure_operation_latency(operation_name):
    """Decorator to measure operation latency"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                duration = end_time - start_time
                PERFORMANCE_TRACKER.record_latency(operation_name, duration)
        return wrapper
    return decorator

@measure_operation_latency("customer_creation")
def test_customer_creation_performance(benchmark_db):
    """Benchmark customer creation performance"""
    service = CustomerService(database=benchmark_db)

    # Measure creation of multiple customers
    for i in range(100):
        customer_data = {
            'name': f'Test User {i}',
            'email': f'test{i}@example.com',
            'phone': f'+123456789{i:02d}'
        }
        service.create_customer(customer_data)

    # Verify statistics meet requirements
    stats = PERFORMANCE_TRACKER.get_statistics("customer_creation")

    # Assert performance requirements
    assert stats['mean'] < 0.1  # Mean creation time < 100ms
    assert stats['p95'] < 0.2   # 95% of operations < 200ms
    assert stats['p99'] < 0.5   # 99% of operations < 500ms

def test_concurrent_request_handling():
    """Test system performance under concurrent load"""
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

    async def run_concurrent_test():
        url = "http://localhost:8000/api/customers"
        payload = {
            'name': 'Load Test User',
            'email': 'load@test.com',
            'phone': '+1234567890'
        }

        async with aiohttp.ClientSession() as session:
            tasks = [make_request(session, url, payload) for _ in range(50)]
            results = await asyncio.gather(*tasks)

        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        response_times = [r['response_time'] for r in results]

        # Performance assertions
        assert len(successful_requests) >= len(results) * 0.95  # 95% success rate
        assert mean(response_times) < 0.5  # Mean response time < 500ms
        assert max(response_times) < 2.0   # Max response time < 2s

        return {
            'total_requests': len(results),
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'success_rate': len(successful_requests) / len(results),
            'mean_response_time': mean(response_times),
            'median_response_time': median(response_times),
            'p95_response_time': sorted(response_times)[int(0.95 * len(response_times))]
        }

    # Run the test
    result = asyncio.run(run_concurrent_test())

    # Log performance metrics
    print(f"Performance Test Results:")
    print(f"  Total Requests: {result['total_requests']}")
    print(f"  Successful: {result['successful_requests']}")
    print(f"  Success Rate: {result['success_rate']:.2%}")
    print(f"  Mean Response Time: {result['mean_response_time']:.3f}s")
    print(f"  Median Response Time: {result['median_response_time']:.3f}s")
    print(f"  P95 Response Time: {result['p95_response_time']:.3f}s")
```

### Accuracy and Escalation Rate Tracking

Monitoring system accuracy and escalation metrics:

```python
import pytest
from collections import Counter
import pandas as pd

class QualityMetricsTracker:
    def __init__(self):
        self.interactions = []
        self.escalations = []
        self.resolutions = []

    def record_interaction(self, interaction_data):
        """Record a customer interaction"""
        self.interactions.append(interaction_data)

    def record_escalation(self, escalation_data):
        """Record an escalation event"""
        self.escalations.append(escalation_data)

    def record_resolution(self, resolution_data):
        """Record a resolution event"""
        self.resolutions.append(resolution_data)

    def calculate_accuracy_rate(self):
        """Calculate overall accuracy rate"""
        if not self.interactions:
            return 0.0

        successful_interactions = sum(1 for interaction in self.interactions
                                   if interaction.get('resolved', False))
        return successful_interactions / len(self.interactions)

    def calculate_escalation_rate(self):
        """Calculate escalation rate"""
        if not self.interactions:
            return 0.0

        return len(self.escalations) / len(self.interactions)

    def calculate_first_contact_resolution_rate(self):
        """Calculate first contact resolution rate"""
        if not self.interactions:
            return 0.0

        first_contact_resolved = sum(1 for interaction in self.interactions
                                  if interaction.get('first_contact_resolved', False))
        return first_contact_resolved / len(self.interactions)

QUALITY_TRACKER = QualityMetricsTracker()

def test_automated_resolution_accuracy():
    """Test accuracy of automated resolution system"""
    # Simulate multiple interactions
    test_cases = [
        {
            'query': 'How do I reset my password?',
            'expected_category': 'account',
            'expected_resolution': 'password_reset_instructions_sent',
            'actual_resolution': 'password_reset_instructions_sent',
            'resolved': True,
            'first_contact_resolved': True
        },
        {
            'query': 'My account is locked',
            'expected_category': 'account',
            'expected_resolution': 'account_unlocked',
            'actual_resolution': 'human_agent_required',
            'resolved': False,
            'first_contact_resolved': False
        },
        # Add more test cases...
    ]

    for case in test_cases:
        QUALITY_TRACKER.record_interaction(case)
        if not case['resolved']:
            QUALITY_TRACKER.record_escalation({
                'original_query': case['query'],
                'resolution_attempt': case['actual_resolution'],
                'escalation_reason': 'automated_resolution_failed'
            })
        else:
            QUALITY_TRACKER.record_resolution({
                'original_query': case['query'],
                'resolution_method': case['actual_resolution'],
                'resolution_time': 0.5  # seconds
            })

    # Calculate metrics
    accuracy_rate = QUALITY_TRACKER.calculate_accuracy_rate()
    escalation_rate = QUALITY_TRACKER.calculate_escalation_rate()
    fcr_rate = QUALITY_TRACKER.calculate_first_contact_resolution_rate()

    # Assertions based on quality requirements
    assert accuracy_rate >= 0.85  # 85% accuracy requirement
    assert escalation_rate <= 0.20  # 20% escalation rate maximum
    assert fcr_rate >= 0.70  # 70% first contact resolution rate

    print(f"Quality Metrics:")
    print(f"  Accuracy Rate: {accuracy_rate:.2%}")
    print(f"  Escalation Rate: {escalation_rate:.2%}")
    print(f"  FCR Rate: {fcr_rate:.2%}")

def test_classification_accuracy():
    """Test accuracy of query classification system"""
    from sklearn.metrics import accuracy_score, classification_report

    # Sample test data
    test_queries = [
        ("How do I reset my password?", "account"),
        ("I can't log in to my account", "account"),
        ("What are your business hours?", "general"),
        ("I want to cancel my subscription", "billing"),
        ("My invoice is incorrect", "billing"),
        ("The app is crashing", "technical"),
        # Add more test cases...
    ]

    # Simulate classification results
    predicted_categories = []
    actual_categories = []

    classifier = MockClassifier()  # Replace with actual classifier

    for query, actual_category in test_queries:
        predicted_category = classifier.classify(query)
        predicted_categories.append(predicted_category)
        actual_categories.append(actual_category)

    # Calculate accuracy
    accuracy = accuracy_score(actual_categories, predicted_categories)

    # Generate detailed report
    report = classification_report(actual_categories, predicted_categories, output_dict=True)

    # Assertions
    assert accuracy >= 0.90  # 90% classification accuracy requirement

    print(f"Classification Accuracy: {accuracy:.2%}")
    print(f"Per-category scores:")
    for category, metrics in report.items():
        if isinstance(metrics, dict) and 'precision' in metrics:
            print(f"  {category}: Precision={metrics['precision']:.2f}, Recall={metrics['recall']:.2f}")
```

## Test Organization and Execution

### Pytest Configuration

Example `pytest.ini` configuration:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --tb=short
    --strict-markers
    --strict-config
    --cov=myapp
    --cov-report=html
    --cov-report=term-missing
    --junitxml=reports/junit.xml
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    performance: marks tests as performance tests
    edge_case: marks tests as edge case tests
filterwarnings =
    error
    ignore::DeprecationWarning
    ignore::UserWarning
```

### Test Execution Strategies

For different testing scenarios:

1. **Development**: Fast unit tests only
2. **CI/CD**: All tests including integration
3. **Performance**: Dedicated performance test runs
4. **Release**: Full test suite including E2E

## Best Practices

### Test Naming Conventions

- Use descriptive names: `test_customer_creation_with_valid_data`
- Follow Given-When-Then pattern: `test_{scenario}_{expected_outcome}`
- Include error conditions: `test_customer_creation_with_invalid_email`

### Test Data Management

- Use fixtures for common test data
- Parameterize tests for multiple input variations
- Clean up test data after each test run
- Use factories for complex object creation

### Performance Testing Guidelines

- Establish baseline metrics
- Test under realistic load conditions
- Monitor system resources during tests
- Track metrics over time for regression detection

For detailed implementation patterns, see:
- [TESTING_PATTERNS.md](references/TESTING_PATTERNS.md) - Test organization and patterns
- [E2E_TESTING_STRATEGIES.md](references/E2E_TESTING_STRATEGIES.md) - End-to-end testing approaches
- [PERFORMANCE_TESTING.md](references/PERFORMANCE_TESTING.md) - Performance and load testing
- [EDGE_CASE_VALIDATION.md](references/EDGE_CASE_VALIDATION.md) - Edge case testing strategies
- [METRIC_TRACKING.md](references/METRIC_TRACKING.md) - Performance and quality metrics
- [PYTEST_BEST_PRACTICES.md](references/PYTEST_BEST_PRACTICES.md) - Pytest framework best practices