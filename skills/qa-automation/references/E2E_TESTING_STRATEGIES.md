# End-to-End Testing Strategies for QA Automation

## Overview

This document provides comprehensive strategies for implementing end-to-end (E2E) tests in a pytest-based test suite. It covers UI testing, API testing, integration testing, and cross-platform testing approaches.

## E2E Testing Architecture

### 1. Test Pyramid Approach

```
UI Tests (Few, Slow, Expensive)
├── Full workflow tests
├── Cross-browser compatibility
└── User journey validation

API Tests (Some, Medium, Moderate)
├── Service integration
├── Authentication flows
└── Data validation

Unit Tests (Many, Fast, Cheap)
├── Individual components
├── Business logic
└── Utility functions
```

### 2. Page Object Model (POM)

```python
# pages/base_page.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class BasePage:
    """Base page class with common functionality"""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def find_element(self, locator):
        """Find element with explicit wait"""
        return self.wait.until(EC.presence_of_element_located(locator))

    def click_element(self, locator):
        """Click element with explicit wait"""
        element = self.wait.until(EC.element_to_be_clickable(locator))
        element.click()

    def enter_text(self, locator, text):
        """Enter text with explicit wait"""
        element = self.wait.until(EC.element_to_be_clickable(locator))
        element.clear()
        element.send_keys(text)

    def is_element_present(self, locator):
        """Check if element is present"""
        try:
            self.find_element(locator)
            return True
        except TimeoutException:
            return False


# pages/login_page.py
from .base_page import BasePage
from selenium.webdriver.common.by import By

class LoginPage(BasePage):
    """Login page object"""

    USERNAME_INPUT = (By.ID, "username")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.ID, "login-button")
    ERROR_MESSAGE = (By.CLASS_NAME, "error-message")

    def enter_username(self, username):
        """Enter username"""
        self.enter_text(self.USERNAME_INPUT, username)

    def enter_password(self, password):
        """Enter password"""
        self.enter_text(self.PASSWORD_INPUT, password)

    def click_login(self):
        """Click login button"""
        self.click_element(self.LOGIN_BUTTON)

    def login(self, username, password):
        """Complete login process"""
        self.enter_username(username)
        self.enter_password(password)
        self.click_login()

    def get_error_message(self):
        """Get error message text"""
        if self.is_element_present(self.ERROR_MESSAGE):
            return self.find_element(self.ERROR_MESSAGE).text
        return None


# pages/dashboard_page.py
from .base_page import BasePage
from selenium.webdriver.common.by import By

class DashboardPage(BasePage):
    """Dashboard page object"""

    WELCOME_MESSAGE = (By.CLASS_NAME, "welcome-message")
    CUSTOMER_MENU = (By.ID, "menu-customers")
    TICKET_MENU = (By.ID, "menu-tickets")
    LOGOUT_BUTTON = (By.ID, "logout")

    def is_logged_in(self):
        """Verify user is logged in"""
        return self.is_element_present(self.WELCOME_MESSAGE)

    def click_customers_menu(self):
        """Navigate to customers page"""
        self.click_element(self.CUSTOMER_MENU)

    def click_tickets_menu(self):
        """Navigate to tickets page"""
        self.click_element(self.TICKET_MENU)

    def logout(self):
        """Logout from application"""
        self.click_element(self.LOGOUT_BUTTON)
```

### 3. E2E Test Implementation

```python
# tests/e2e/test_customer_journey.py
import pytest
from pages.login_page import LoginPage
from pages.dashboard_page import DashboardPage
from pages.customer_page import CustomerPage
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

@pytest.fixture
def browser():
    """Setup browser for E2E testing"""
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

@pytest.fixture
def login_page(browser):
    """Create login page instance"""
    browser.get("https://test.myapp.com/login")
    return LoginPage(browser)

@pytest.fixture
def authenticated_session(login_page):
    """Create authenticated session"""
    login_page.login("test@example.com", "password123")

    # Verify login was successful
    dashboard = DashboardPage(login_page.driver)
    assert dashboard.is_logged_in(), "Login failed"

    return dashboard

def test_full_customer_support_journey(authenticated_session):
    """Test complete customer support journey"""
    dashboard = authenticated_session

    # Navigate to customer creation
    dashboard.click_customers_menu()
    customer_page = CustomerPage(dashboard.driver)

    # Create a new customer
    customer_data = {
        'name': 'John Doe',
        'email': 'john@example.com',
        'phone': '+1234567890'
    }
    customer_page.create_customer(customer_data)

    # Verify customer was created
    assert customer_page.is_customer_created(), "Customer creation failed"

    # Create a support ticket for the customer
    ticket_data = {
        'subject': 'Technical Support Request',
        'description': 'Customer needs help with setup',
        'priority': 'medium'
    }
    customer_page.create_ticket(ticket_data)

    # Verify ticket was created
    assert customer_page.is_ticket_created(), "Ticket creation failed"

    # Logout
    dashboard.logout()
    assert login_page.is_element_present(login_page.USERNAME_INPUT), "Logout failed"

def test_login_failure_scenario(login_page):
    """Test login failure scenario"""
    login_page.login("invalid@example.com", "wrongpassword")

    error_message = login_page.get_error_message()
    assert error_message is not None, "Expected error message not displayed"
    assert "Invalid credentials" in error_message.lower(), f"Unexpected error: {error_message}"
```

## API E2E Testing

### 1. REST API Testing

```python
# tests/e2e/test_api_endpoints.py
import pytest
import requests
import time
from urllib.parse import urljoin

class APIClient:
    """API client for testing"""

    def __init__(self, base_url, auth_token=None):
        self.base_url = base_url
        self.session = requests.Session()

        if auth_token:
            self.session.headers.update({
                'Authorization': f'Bearer {auth_token}',
                'Content-Type': 'application/json'
            })

    def get(self, endpoint, **kwargs):
        """GET request"""
        url = urljoin(self.base_url, endpoint)
        return self.session.get(url, **kwargs)

    def post(self, endpoint, data=None, **kwargs):
        """POST request"""
        url = urljoin(self.base_url, endpoint)
        return self.session.post(url, json=data, **kwargs)

    def put(self, endpoint, data=None, **kwargs):
        """PUT request"""
        url = urljoin(self.base_url, endpoint)
        return self.session.put(url, json=data, **kwargs)

    def delete(self, endpoint, **kwargs):
        """DELETE request"""
        url = urljoin(self.base_url, endpoint)
        return self.session.delete(url, **kwargs)

@pytest.fixture
def api_client():
    """API client fixture"""
    return APIClient(base_url="https://test-api.myapp.com")

@pytest.fixture
def auth_token(api_client):
    """Authentication token fixture"""
    login_data = {
        'email': 'test@example.com',
        'password': 'password123'
    }

    response = api_client.post('/auth/login', data=login_data)
    assert response.status_code == 200

    token = response.json()['token']
    return token

def test_customer_lifecycle_api(auth_token):
    """Test complete customer lifecycle via API"""
    client = APIClient(base_url="https://test-api.myapp.com", auth_token=auth_token)

    # Create customer
    customer_data = {
        'name': 'Jane Smith',
        'email': 'jane@example.com',
        'phone': '+0987654321'
    }

    create_response = client.post('/customers', data=customer_data)
    assert create_response.status_code == 201

    customer_id = create_response.json()['id']
    assert customer_id is not None

    # Retrieve customer
    get_response = client.get(f'/customers/{customer_id}')
    assert get_response.status_code == 200

    retrieved_customer = get_response.json()
    assert retrieved_customer['name'] == customer_data['name']
    assert retrieved_customer['email'] == customer_data['email']

    # Update customer
    update_data = {
        'name': 'Jane Updated',
        'phone': '+1122334455'
    }

    update_response = client.put(f'/customers/{customer_id}', data=update_data)
    assert update_response.status_code == 200

    # Verify update
    updated_response = client.get(f'/customers/{customer_id}')
    assert updated_response.json()['name'] == 'Jane Updated'
    assert updated_response.json()['phone'] == '+1122334455'

    # Delete customer
    delete_response = client.delete(f'/customers/{customer_id}')
    assert delete_response.status_code == 204

    # Verify deletion
    deleted_response = client.get(f'/customers/{customer_id}')
    assert deleted_response.status_code == 404

def test_api_rate_limiting():
    """Test API rate limiting"""
    client = APIClient(base_url="https://test-api.myapp.com")

    # Make multiple requests rapidly
    start_time = time.time()
    responses = []

    for i in range(25):  # Assuming rate limit is 20 requests per minute
        response = client.get('/customers')
        responses.append(response.status_code)
        time.sleep(0.1)  # Small delay to avoid overwhelming server

    end_time = time.time()

    # Count rate limited responses (429)
    rate_limited_count = sum(1 for status in responses if status == 429)

    # Should have some rate limited requests
    assert rate_limited_count > 0, "Rate limiting not working properly"
    assert end_time - start_time < 2.0, "Requests took too long"
```

## Cross-Platform Testing

### 1. Mobile Testing

```python
# tests/e2e/test_mobile_app.py
import pytest
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture
def mobile_driver():
    """Setup mobile app driver"""
    capabilities = {
        'platformName': 'Android',
        'deviceName': 'emulator-5554',
        'appPackage': 'com.myapp.crm',
        'appActivity': 'com.myapp.crm.MainActivity',
        'automationName': 'UiAutomator2'
    }

    driver = webdriver.Remote('http://localhost:4723', options=capabilities)
    yield driver
    driver.quit()

class MobileLoginPage:
    """Mobile app login page"""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def login(self, username, password):
        """Perform login on mobile app"""
        username_field = self.wait.until(
            EC.presence_of_element_located((AppiumBy.ID, "username_input"))
        )
        username_field.send_keys(username)

        password_field = self.driver.find_element(AppiumBy.ID, "password_input")
        password_field.send_keys(password)

        login_button = self.driver.find_element(AppiumBy.ID, "login_button")
        login_button.click()

def test_mobile_login_flow(mobile_driver):
    """Test login flow on mobile app"""
    login_page = MobileLoginPage(mobile_driver)
    login_page.login("test@example.com", "password123")

    # Wait for dashboard to load
    dashboard_element = WebDriverWait(mobile_driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "dashboard_title"))
    )

    assert dashboard_element.is_displayed()
    assert "Dashboard" in dashboard_element.text
```

### 2. Cross-Browser Testing

```python
# tests/e2e/test_cross_browser.py
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

@pytest.fixture(params=['chrome', 'firefox', 'edge'])
def browser(request):
    """Cross-browser fixture"""
    browser_name = request.param

    if browser_name == 'chrome':
        options = ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
    elif browser_name == 'firefox':
        options = FirefoxOptions()
        options.add_argument('-headless')
        driver = webdriver.Firefox(options=options)
    elif browser_name == 'edge':
        options = EdgeOptions()
        options.add_argument('--headless')
        driver = webdriver.Edge(options=options)
    else:
        raise ValueError(f"Unsupported browser: {browser_name}")

    yield driver
    driver.quit()

def test_login_across_browsers(browser):
    """Test login functionality across different browsers"""
    browser.get("https://test.myapp.com/login")

    # Find login elements
    username_input = browser.find_element("id", "username")
    password_input = browser.find_element("id", "password")
    login_button = browser.find_element("id", "login-button")

    # Perform login
    username_input.send_keys("test@example.com")
    password_input.send_keys("password123")
    login_button.click()

    # Wait for dashboard and verify
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    dashboard_title = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located(("class name", "dashboard-title"))
    )

    assert "Dashboard" in dashboard_title.text
    assert browser.current_url.endswith("/dashboard")
```

## Parallel Execution Strategies

### 1. Test Parallelization

```python
# pytest.ini
[tool:pytest]
addopts =
    -n auto
    --dist=loadfile
    --maxfail=1
    --tb=short
testpaths = tests/e2e
markers =
    serial: marks tests that must run serially
    parallel: marks tests that can run in parallel
    ui: marks UI tests
    api: marks API tests
    mobile: marks mobile tests
```

```python
# tests/e2e/conftest.py
import pytest
import threading
from concurrent.futures import ThreadPoolExecutor

# Thread-local storage for test data
thread_local = threading.local()

@pytest.fixture(scope="function")
def test_data():
    """Thread-safe test data fixture"""
    if not hasattr(thread_local, 'data'):
        thread_local.data = {}
    return thread_local.data

@pytest.fixture(scope="session")
def shared_resources():
    """Shared resources for parallel tests"""
    resources = {
        'api_client': APIClient(base_url="https://test-api.myapp.com"),
        'db_connection': create_test_database()
    }
    yield resources
    cleanup_shared_resources(resources)

@pytest.mark.parallel
def test_customer_creation_parallel(shared_resources, test_data):
    """Test that can run in parallel"""
    client = shared_resources['api_client']

    customer_data = {
        'name': f'Test User {threading.current_thread().ident}',
        'email': f'test{threading.current_thread().ident}@example.com',
        'phone': f'+123456789{threading.current_thread().ident % 100:02d}'
    }

    response = client.post('/customers', data=customer_data)
    assert response.status_code == 201

    # Store test-specific data
    test_data['customer_id'] = response.json()['id']

@pytest.mark.serial
def test_data_cleanup(shared_resources):
    """Test that must run serially"""
    # Cleanup test data
    pass
```

## Test Data Management

### 1. Test Data Factories

```python
# tests/e2e/test_data_factories.py
import factory
import faker
from datetime import datetime, timedelta

fake = faker.Faker()

class CustomerDataFactory:
    """Factory for generating customer test data"""

    @staticmethod
    def create_customer_data(**overrides):
        """Create customer data with optional overrides"""
        data = {
            'name': fake.name(),
            'email': fake.email(),
            'phone': fake.phone_number(),
            'address': fake.address(),
            'company': fake.company(),
            'created_at': datetime.now().isoformat()
        }
        data.update(overrides)
        return data

    @staticmethod
    def create_customer_batch(count, **common_fields):
        """Create multiple customer records"""
        customers = []
        for _ in range(count):
            customer_data = CustomerDataFactory.create_customer_data(**common_fields)
            customers.append(customer_data)
        return customers

class TicketDataFactory:
    """Factory for generating ticket test data"""

    @staticmethod
    def create_ticket_data(**overrides):
        """Create ticket data with optional overrides"""
        priorities = ['low', 'medium', 'high', 'critical']
        statuses = ['open', 'in_progress', 'resolved', 'closed']

        data = {
            'title': fake.sentence(nb_words=6),
            'description': fake.paragraph(nb_sentences=3),
            'priority': fake.random_element(elements=priorities),
            'status': fake.random_element(elements=statuses),
            'created_at': (datetime.now() - timedelta(days=fake.random_int(0, 30))).isoformat(),
            'due_date': (datetime.now() + timedelta(days=fake.random_int(1, 14))).isoformat()
        }
        data.update(overrides)
        return data

def test_customer_creation_with_factory():
    """Test using data factory"""
    factory = CustomerDataFactory()
    customer_data = factory.create_customer_data(
        name="John Doe",
        email="john.doe@example.com"
    )

    # Use customer_data in test
    api_client = APIClient(base_url="https://test-api.myapp.com")
    response = api_client.post('/customers', data=customer_data)

    assert response.status_code == 201
    assert response.json()['name'] == "John Doe"
```

### 2. Test Data Cleanup

```python
# tests/e2e/test_data_cleanup.py
import pytest
import atexit
from contextlib import contextmanager

class TestDataCleanup:
    """Manage test data cleanup"""

    def __init__(self):
        self.created_entities = {
            'customers': [],
            'tickets': [],
            'users': []
        }

    def register_entity(self, entity_type, entity_id):
        """Register entity for cleanup"""
        self.created_entities[entity_type].append(entity_id)

    def cleanup_all(self):
        """Clean up all registered entities"""
        api_client = APIClient(base_url="https://test-api.myapp.com")

        # Clean up in reverse order to respect dependencies
        for entity_type in reversed(list(self.created_entities.keys())):
            for entity_id in self.created_entities[entity_type]:
                try:
                    api_client.delete(f'/{entity_type}/{entity_id}')
                except Exception:
                    # Log but don't fail cleanup
                    print(f"Failed to delete {entity_type}/{entity_id}")

# Global cleanup instance
cleanup_manager = TestDataCleanup()
atexit.register(cleanup_manager.cleanup_all)

@pytest.fixture
def register_cleanup():
    """Fixture to register entities for cleanup"""
    def _register(entity_type, entity_id):
        cleanup_manager.register_entity(entity_type, entity_id)
    return _register

def test_customer_with_cleanup(register_cleanup):
    """Test with automatic cleanup registration"""
    api_client = APIClient(base_url="https://test-api.myapp.com")

    customer_data = {
        'name': 'Test Customer',
        'email': 'test@example.com',
        'phone': '+1234567890'
    }

    response = api_client.post('/customers', data=customer_data)
    assert response.status_code == 201

    customer_id = response.json()['id']
    register_cleanup('customers', customer_id)  # Register for cleanup

    # Test continues...
    assert customer_id is not None
```

This comprehensive E2E testing strategies guide provides all the necessary approaches and patterns for implementing effective end-to-end tests.