# Edge Case Validation for QA Automation

## Overview

This document provides comprehensive guidance on implementing edge case validation in a pytest-based test suite. It covers boundary condition testing, error scenario testing, and exceptional input handling.

## Edge Case Categories

### 1. Boundary Condition Testing

Testing inputs at the limits of acceptable values:

```python
# tests/edge_cases/test_boundary_conditions.py
import pytest
import string
import random

class TestBoundaryConditions:
    """Test boundary conditions for various inputs"""

    @pytest.mark.parametrize("input_value,expected_result", [
        ("", False),  # Empty string
        ("a", True),  # Single character
        ("a" * 1, True),  # Minimum valid length
        ("a" * 255, True),  # Maximum valid length
        ("a" * 256, False),  # Just over maximum
        ("a" * 1000, False),  # Far over maximum
    ])
    def test_name_length_boundaries(self, input_value, expected_result):
        """Test name validation at length boundaries"""
        from myapp.utils.validators import validate_name

        if expected_result:
            assert validate_name(input_value) is True
        else:
            with pytest.raises(ValueError):
                validate_name(input_value)

    @pytest.mark.parametrize("email,expected_validity", [
        # Boundary cases for email lengths
        ("a@b.co", True),  # Very short but valid
        ("a" * 64 + "@domain.com", True),  # Maximum local part length
        ("a" * 65 + "@domain.com", False),  # Over local part limit
        ("user@" + "d" * 243 + ".com", True),  # Near domain length limit
        ("user@" + "d" * 244 + ".com", False),  # Over domain limit
    ])
    def test_email_boundary_conditions(self, email, expected_validity):
        """Test email validation at boundary conditions"""
        from myapp.utils.validators import validate_email

        if expected_validity:
            assert validate_email(email) is True
        else:
            with pytest.raises(ValueError):
                validate_email(email)

    @pytest.mark.parametrize("number,min_val,max_val,expected", [
        # Integer boundary tests
        (0, 0, 100, True),  # Minimum value
        (100, 0, 100, True),  # Maximum value
        (-1, 0, 100, False),  # Just below minimum
        (101, 0, 100, False),  # Just above maximum
        (0, 1, 100, False),  # Zero when minimum is positive
        (-100, -50, 50, False),  # Below negative minimum
        (50, -50, 50, True),  # At positive maximum
    ])
    def test_numeric_boundary_conditions(self, number, min_val, max_val, expected):
        """Test numeric validation at boundary conditions"""
        from myapp.utils.validators import validate_range

        if expected:
            assert validate_range(number, min_val, max_val) is True
        else:
            with pytest.raises(ValueError):
                validate_range(number, min_val, max_val)

    def test_large_number_boundaries(self):
        """Test boundaries with large numbers"""
        from myapp.utils.validators import validate_large_number

        # Test near integer limits
        max_int32 = 2**31 - 1
        min_int32 = -(2**31)

        # Valid cases
        assert validate_large_number(max_int32 - 1) is True
        assert validate_large_number(min_int32 + 1) is True

        # Invalid cases
        with pytest.raises(ValueError):
            validate_large_number(max_int32 + 1)
        with pytest.raises(ValueError):
            validate_large_number(min_int32 - 1)

    def test_string_encoding_boundaries(self):
        """Test string validation with special Unicode characters"""
        from myapp.utils.validators import validate_text

        # Valid Unicode characters
        valid_unicode_cases = [
            "café",  # Latin with accents
            "北京",  # Chinese characters
            "مرحبا",  # Arabic
            "🚀",  # Emoji
            "αβγδε",  # Greek letters
        ]

        for case in valid_unicode_cases:
            assert validate_text(case) is True

        # Test very long Unicode string
        long_unicode = "🚀" * 1000  # 1000 emojis
        with pytest.raises(ValueError):
            validate_text(long_unicode)
```

### 2. Error Scenario Testing

Testing system behavior under error conditions:

```python
# tests/edge_cases/test_error_scenarios.py
import pytest
from unittest.mock import Mock, patch, MagicMock
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError

class TestErrorScenarios:
    """Test error scenarios and exception handling"""

    def test_database_connection_failure(self):
        """Test behavior when database is unavailable"""
        from myapp.database import Database
        from myapp.services.customer_service import CustomerService

        with patch.object(Database, 'connect') as mock_connect:
            mock_connect.side_effect = ConnectionError("Database unavailable")

            service = CustomerService()

            with pytest.raises(ConnectionError, match="Database unavailable"):
                service.create_customer({
                    'name': 'Test User',
                    'email': 'test@example.com',
                    'phone': '+1234567890'
                })

    def test_external_api_timeout(self):
        """Test behavior when external API times out"""
        from myapp.services.notification_service import NotificationService

        service = NotificationService()

        # Mock an API call that times out
        with patch.object(service.email_client, 'send', side_effect=TimeoutError("API timeout")):
            result = service.send_notification(
                customer_id=1,
                message="Test message",
                channels=['email']
            )

            # Should handle timeout gracefully
            assert result.success is False
            assert result.partial_failure is True
            assert "email" in result.failed_channels

    def test_concurrent_access_conflicts(self):
        """Test concurrent access leading to conflicts"""
        from myapp.services.customer_service import CustomerService

        service = CustomerService()

        def create_same_customer():
            """Function to create the same customer"""
            return service.create_customer({
                'name': 'Duplicate User',
                'email': 'duplicate@example.com',
                'phone': '+1234567890'
            })

        # Create a pool of threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit multiple concurrent requests
            futures = [executor.submit(create_same_customer) for _ in range(5)]

            results = []
            exceptions = []

            for future in futures:
                try:
                    result = future.result(timeout=5.0)
                    results.append(result)
                except Exception as e:
                    exceptions.append(e)

        # Verify that some operations failed due to conflicts
        successful_creations = sum(1 for r in results if r.success)
        failed_due_to_conflict = len(exceptions)

        # At least one should succeed, others should fail
        assert successful_creations >= 1
        assert failed_due_to_conflict >= 1

    def test_resource_exhaustion(self):
        """Test behavior when system resources are exhausted"""
        import psutil
        import os

        # Get current process
        process = psutil.Process(os.getpid())

        # This is a simulation - in real tests, you'd use a mock
        # to simulate resource exhaustion
        from myapp.services.resource_manager import ResourceManager

        manager = ResourceManager()

        # Mock memory allocation that would fail
        with patch.object(manager, 'allocate_resource') as mock_allocate:
            mock_allocate.side_effect = MemoryError("Insufficient memory")

            with pytest.raises(MemoryError, match="Insufficient memory"):
                manager.allocate_resource(size=1024*1024*1024)  # 1GB request

    def test_network_partition_simulation(self):
        """Test behavior during network partition"""
        from myapp.services.sync_service import SyncService

        service = SyncService()

        # Simulate network partition by making all requests fail
        with patch.object(service, 'sync_with_remote', side_effect=ConnectionError("Network partition")):
            result = service.sync_customer_data()

            # Should handle network partition gracefully
            assert result.success is False
            assert result.retry_scheduled is True

    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies"""
        from myapp.utils.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()

        # Create a circular dependency
        dependencies = {
            'A': ['B'],
            'B': ['C'],
            'C': ['A']  # Circular: A -> B -> C -> A
        }

        with pytest.raises(ValueError, match="Circular dependency detected"):
            resolver.resolve_dependencies(dependencies)

    def test_infinite_loop_protection(self):
        """Test protection against infinite loops"""
        from myapp.utils.recursion_limiter import RecursiveProcessor

        processor = RecursiveProcessor(max_depth=5)

        # This would normally cause an infinite loop
        def problematic_recursion(n):
            if n <= 0:
                return 0
            return n + problematic_recursion(n)  # Bug: not decrementing n!

        with pytest.raises(RuntimeError, match="Maximum recursion depth exceeded"):
            processor.process(problematic_recursion, 5)

    def test_null_byte_injection(self):
        """Test protection against null byte injection"""
        from myapp.utils.input_sanitizer import sanitize_filename

        malicious_inputs = [
            "file\x00.txt",  # Null byte injection
            "path/to/\x00malicious",  # Path traversal with null byte
            "normal\x00\x00.txt",  # Multiple null bytes
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(ValueError, match="Null byte detected"):
                sanitize_filename(malicious_input)

    def test_sql_injection_attempts(self):
        """Test protection against SQL injection"""
        from myapp.repositories.customer_repository import CustomerRepository

        repo = CustomerRepository()

        sql_injection_attempts = [
            "'; DROP TABLE customers; --",
            "' OR '1'='1",
            "'; DELETE FROM customers; --",
            "admin'; UPDATE users SET admin=1; --"
        ]

        for injection in sql_injection_attempts:
            # Should either raise an exception or handle safely
            with pytest.raises(Exception):  # Could be various exception types
                repo.find_by_name(injection)
```

### 3. Exceptional Input Handling

Testing with unusual or unexpected inputs:

```python
# tests/edge_cases/test_exceptional_inputs.py
import pytest
import math
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta

class TestExceptionalInputs:
    """Test handling of exceptional inputs"""

    def test_extreme_numeric_values(self):
        """Test with extreme numeric values"""
        from myapp.utils.calculator import Calculator

        calc = Calculator()

        # Test with very large numbers
        large_num = float('1e308')
        result = calc.multiply(large_num, 2)
        assert math.isinf(result)  # Should handle overflow

        # Test with very small numbers
        tiny_num = float('1e-308')
        result = calc.multiply(tiny_num, tiny_num)
        assert result == 0.0  # May underflow to zero

        # Test with infinity
        inf_result = calc.divide(10, 0)
        assert math.isinf(inf_result)

        # Test with NaN
        nan_result = calc.divide(0, 0)
        assert math.isnan(nan_result)

    @pytest.mark.parametrize("malformed_input", [
        # Various malformed JSON inputs
        '{',
        '[',
        'null',
        'true',
        'false',
        '"just a string"',
        '123',
        '{"unclosed": "brace"',
        '["unclosed": "bracket"',
        '{"extra": "comma",}',
        '{"duplicate": "key", "duplicate": "value"}',
    ])
    def test_json_parsing_edge_cases(self, malformed_input):
        """Test JSON parsing with malformed inputs"""
        from myapp.utils.json_parser import safe_parse_json

        # Should handle safely without crashing
        result = safe_parse_json(malformed_input)
        assert result is not None  # Should return some default/error representation

    def test_timezone_edge_cases(self):
        """Test timezone handling at boundaries"""
        from myapp.utils.date_converter import convert_timezone

        # Test at the beginning of Unix epoch
        epoch_start = datetime(1970, 1, 1)
        converted = convert_timezone(epoch_start, 'UTC', 'US/Eastern')
        assert converted is not None

        # Test at the end of representable dates
        far_future = datetime(2038, 1, 19, 3, 14, 7)  # Before Year 2038 problem
        converted = convert_timezone(far_future, 'UTC', 'Asia/Tokyo')
        assert converted is not None

        # Test with invalid timezone
        with pytest.raises(ValueError):
            convert_timezone(datetime.now(), 'UTC', 'Invalid/Timezone')

    def test_encoding_edge_cases(self):
        """Test string encoding/decoding edge cases"""
        from myapp.utils.encoding_helper import safe_decode

        # Test with invalid UTF-8 bytes
        invalid_utf8 = b'\xff\xfe\xfd'
        decoded = safe_decode(invalid_utf8)
        assert decoded is not None  # Should handle gracefully

        # Test with mixed encodings
        mixed_bytes = "café".encode('utf-8') + b'\xff\xfe'
        decoded = safe_decode(mixed_bytes)
        assert decoded is not None

    def test_regular_expression_edge_cases(self):
        """Test regex with pathological patterns"""
        import re

        # Test catastrophic backtracking prevention
        # This pattern can cause exponential backtracking
        pathological_pattern = r"(a+)+b"
        test_string = "a" * 30  # Long string of 'a's

        # Use timeout to prevent hanging
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Regex took too long")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(2)  # 2 second timeout

        try:
            # This should be handled safely
            result = re.search(pathological_pattern, test_string)
        except TimeoutError:
            # Expected behavior - regex timed out safely
            pass
        finally:
            signal.alarm(0)  # Cancel alarm

    def test_file_path_edge_cases(self):
        """Test file path validation with edge cases"""
        from myapp.utils.path_validator import validate_path

        edge_cases = [
            "",  # Empty path
            "/",  # Root directory
            "../" * 100,  # Deep relative path
            "normal/file.txt",
            "~/.config",  # Home directory reference
            "/../",  # Path with parent reference
            "//double/slash",  # Double slash
            "file with spaces.txt",
            "file\nwith\tnewlines.txt",  # Control characters
        ]

        for path in edge_cases:
            # Should handle safely without crashing
            try:
                result = validate_path(path)
                # If it returns a value, it should be reasonable
                if result is not None:
                    assert isinstance(result, (bool, str))
            except ValueError:
                # Some cases should legitimately raise ValueError
                pass

    def test_buffer_overflow_simulation(self):
        """Test protection against buffer overflow attempts"""
        from myapp.utils.buffer_manager import BufferManager

        manager = BufferManager(buffer_size=1024)  # 1KB buffer

        # Try to write much more than buffer size
        large_input = "A" * 10000  # 10KB input for 1KB buffer

        with pytest.raises(BufferError, match="Buffer overflow prevented"):
            manager.write_safe(large_input)

    def test_recursive_data_structures(self):
        """Test handling of recursive data structures"""
        from myapp.utils.serializer import safe_serialize

        # Create a recursive structure
        data = {"key": "value"}
        data["self_ref"] = data  # Self-reference

        # Should handle without infinite recursion
        serialized = safe_serialize(data)
        assert serialized is not None
        assert "self_ref" in serialized

        # Test with multiple levels of recursion
        outer = {"level1": {}}
        outer["level1"]["level2"] = {}
        outer["level1"]["level2"]["level3"] = outer  # Circular reference

        serialized = safe_serialize(outer)
        assert serialized is not None

    def test_extremely_long_inputs(self):
        """Test with extremely long inputs"""
        from myapp.utils.text_processor import TextProcessor

        processor = TextProcessor(max_length=10000)

        # Test with input much longer than limit
        extremely_long = "A" * 100000  # 100KB of text

        with pytest.raises(ValueError, match="Input exceeds maximum length"):
            processor.process_text(extremely_long)

        # Test with valid but long input
        valid_long = "A" * 9999  # Just under limit
        result = processor.process_text(valid_long)
        assert len(result) == 9999

    def test_special_character_combinations(self):
        """Test inputs with special character combinations"""
        from myapp.utils.input_validator import validate_input

        special_inputs = [
            "\x00",  # Null byte
            "\n\r\t\b\f",  # All control characters
            "\"'&<>",  # HTML-sensitive characters
            "%s%d%x",  # Format string characters
            "..//..//..//etc/passwd",  # Path traversal attempt
            "javascript:alert('xss')",  # Potential XSS
            "file:///etc/passwd",  # Local file access attempt
            "C:\\Windows\\System32\\cmd.exe",  # Windows path
        ]

        for special_input in special_inputs:
            # Should either reject or sanitize safely
            try:
                result = validate_input(special_input)
                # If accepted, should be sanitized
                assert result != special_input or result is None
            except ValueError:
                # Some inputs should legitimately be rejected
                pass
```

## Fuzzy Testing

### 1. Random Input Generation

```python
# tests/edge_cases/test_fuzzy_inputs.py
import pytest
from hypothesis import given, strategies as st
import string
import random

class TestFuzzyInputs:
    """Test with randomly generated inputs"""

    @given(
        name=st.text(alphabet=st.characters(blacklist_characters=['\x00']), min_size=1, max_size=255),
        age=st.integers(min_value=0, max_value=150),
        email=st.emails()
    )
    def test_customer_creation_with_fuzzed_data(self, name, age, email):
        """Test customer creation with fuzzed inputs"""
        from myapp.services.customer_service import CustomerService

        service = CustomerService()

        # Generate customer data with fuzzed values
        customer_data = {
            'name': name,
            'age': age,
            'email': email,
            'phone': f"+1{random.randint(1000000000, 9999999999)}"  # Random phone
        }

        # Should either succeed or fail gracefully
        try:
            result = service.create_customer(customer_data)
            # If successful, verify the data was processed correctly
            if result.success:
                assert result.customer.name == name
                assert result.customer.email == email
        except ValueError:
            # Acceptable - validation should catch bad inputs
            pass
        except Exception as e:
            # Other exceptions might indicate bugs
            pytest.fail(f"Unexpected exception: {e}")

    @given(
        text=st.text(min_size=0, max_size=1000),
        number=st.floats(allow_nan=False, allow_infinity=False),
        boolean_val=st.booleans(),
        list_items=st.lists(st.text(), max_size=100)
    )
    def test_api_endpoint_with_fuzzed_data(self, text, number, boolean_val, list_items):
        """Test API endpoint with fuzzed data"""
        import requests
        import json

        # Prepare fuzzed payload
        payload = {
            'text_field': text,
            'number_field': number,
            'boolean_field': boolean_val,
            'list_field': list_items
        }

        # Send to API (in real test, this would hit a test endpoint)
        # For safety, we'll just validate the data instead
        from myapp.utils.api_validator import validate_api_payload

        try:
            is_valid = validate_api_payload(payload)
            # If validation passes, the data should be safe to process
            if is_valid:
                # Process the payload safely
                processed = self.safe_process_payload(payload)
                assert processed is not None
        except Exception as e:
            # Should handle gracefully
            assert isinstance(e, (ValueError, TypeError))

    def safe_process_payload(self, payload):
        """Safely process a payload without side effects"""
        # This would be the actual processing logic in a real application
        # For testing, we just validate that the payload structure is safe
        if not isinstance(payload, dict):
            raise TypeError("Payload must be a dictionary")

        # Validate each field type
        for key, value in payload.items():
            if isinstance(value, str):
                # Check for dangerous content
                if '\x00' in value:
                    raise ValueError("Null byte detected in string")
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and '\x00' in item:
                        raise ValueError("Null byte detected in list item")

        return {"processed": True, "fields": len(payload)}

    @given(
        first_name=st.text(alphabet=string.ascii_letters + "-' ", min_size=1, max_size=50),
        last_name=st.text(alphabet=string.ascii_letters + "-' ", min_size=1, max_size=50),
        country_code=st.from_regex(r'^\+[1-9]\d{0,3}$'),  # Phone country code pattern
        national_number=st.from_regex(r'^\d{4,14}$')  # National phone number
    )
    def test_phone_validation_with_fuzzed_inputs(self, first_name, last_name, country_code, national_number):
        """Test phone number validation with fuzzed inputs"""
        from myapp.utils.phone_validator import validate_phone_number

        full_phone = f"{country_code}{national_number}"

        try:
            is_valid = validate_phone_number(full_phone)
            # If valid, it should follow international format standards
            if is_valid:
                assert full_phone.startswith('+')
                assert len(full_phone) >= 7  # Minimum international format
        except Exception as e:
            # Should handle gracefully
            assert isinstance(e, ValueError)
```

## Chaos Engineering Simulation

### 1. Failure Injection Testing

```python
# tests/edge_cases/test_chaos_engineering.py
import pytest
from unittest.mock import patch, MagicMock
import time
import random
from contextlib import contextmanager

class TestChaosEngineering:
    """Test system resilience under chaotic conditions"""

    @contextmanager
    def inject_failure(self, probability=0.1, failure_type=Exception, failure_message="Simulated failure"):
        """Context manager to inject random failures"""
        if random.random() < probability:
            raise failure_type(failure_message)
        yield

    def test_resilient_customer_creation(self):
        """Test customer creation with simulated failures"""
        from myapp.services.customer_service import CustomerService

        service = CustomerService()

        # Simulate various failure points
        for attempt in range(10):
            with patch.object(service.database, 'save') as mock_save:
                # Randomly inject failures
                if attempt in [2, 5, 7]:  # Simulate failures on certain attempts
                    mock_save.side_effect = ConnectionError("Database temporarily unavailable")
                else:
                    mock_save.side_effect = None

                customer_data = {
                    'name': f'Test User {attempt}',
                    'email': f'test{attempt}@example.com',
                    'phone': f'+123456789{attempt:02d}'
                }

                try:
                    result = service.create_customer(customer_data)
                    if attempt in [2, 5, 7]:
                        # Should have retry logic or graceful degradation
                        assert result.success is True or result.retry_scheduled is True
                    else:
                        assert result.success is True
                except Exception as e:
                    # Should handle gracefully
                    assert hasattr(e, 'retry_after') or str(e).startswith("Temporary")

    def test_network_partition_tolerance(self):
        """Test tolerance to network partitions"""
        from myapp.services.sync_service import SyncService

        service = SyncService()

        # Simulate intermittent network failures
        network_states = [True, True, False, True, False, False, True, True]  # 8 states: up/down

        for i, is_up in enumerate(network_states):
            with patch.object(service, 'is_network_available', return_value=is_up):
                if not is_up:
                    # Simulate network failure
                    with patch.object(service, 'sync_with_remote', side_effect=ConnectionError("Network down")):
                        result = service.sync_customer_data()
                        # Should handle network failures gracefully
                        assert result.success is False or result.retry_scheduled is True
                else:
                    # Normal operation
                    result = service.sync_customer_data()
                    # Should succeed when network is up
                    assert result.success is True

    def test_resource_starvation_simulation(self):
        """Test behavior under resource starvation"""
        from myapp.services.resource_manager import ResourceManager

        manager = ResourceManager()

        # Simulate memory pressure
        with patch('psutil.virtual_memory') as mock_memory:
            # Mock memory as almost full
            mock_mem_info = MagicMock()
            mock_mem_info.percent = 95  # 95% memory usage
            mock_memory.return_value = mock_mem_info

            # Try to allocate resources
            with pytest.raises(ResourceWarning, match="Insufficient resources"):
                manager.allocate_resource(size=1024*1024*100)  # 100MB request

    def test_dependency_failure_cascading(self):
        """Test cascading failures when dependencies fail"""
        from myapp.services.customer_service import CustomerService

        service = CustomerService()

        # Simulate failure in secondary service (email service)
        with patch.object(service.email_service, 'send_welcome_email', side_effect=Exception("Email service down")):
            # Primary function should still work
            customer_data = {
                'name': 'Test User',
                'email': 'test@example.com',
                'phone': '+1234567890'
            }

            result = service.create_customer(customer_data)

            # Primary function should succeed
            assert result.success is True
            # But secondary function failure should be noted
            assert result.notifications_failed == ['welcome_email']

    def test_partial_failure_handling(self):
        """Test handling of partial failures"""
        from myapp.services.multi_service import MultiService

        service = MultiService()

        # Simulate partial failure scenario
        with patch.multiple(service,
                           service_a=lambda: True,  # Success
                           service_b=lambda: False,  # Failure
                           service_c=lambda: True):  # Success

            result = service.perform_multi_step_operation()

            # Should handle partial failure gracefully
            assert result.overall_success is False  # Because one failed
            assert result.partial_success is True   # Because some succeeded
            assert result.failed_steps == ['service_b']
            assert result.successful_steps == ['service_a', 'service_c']

    def test_timeout_resilience(self):
        """Test resilience to timeout scenarios"""
        from myapp.services.timeout_service import TimeoutService

        service = TimeoutService(timeout=1.0)  # 1 second timeout

        # Simulate slow external service
        with patch.object(service.external_client, 'call', side_effect=lambda: time.sleep(2.0)):  # 2 sec call
            result = service.perform_operation()

            # Should handle timeout gracefully
            assert result.timed_out is True
            assert result.fallback_used is True
            assert result.success is True  # With fallback

    def test_concurrent_load_with_failures(self):
        """Test concurrent load with simulated failures"""
        import asyncio
        import aiohttp
        from concurrent.futures import ThreadPoolExecutor

        # Simulate high load with random failures
        async def simulate_concurrent_requests():
            results = []

            async def make_request(req_id):
                # Simulate random failures
                if random.random() < 0.1:  # 10% failure rate
                    raise ConnectionError(f"Request {req_id} failed")

                # Simulate successful request
                await asyncio.sleep(random.uniform(0.01, 0.1))  # Random response time
                return {"id": req_id, "success": True}

            # Make 50 concurrent requests
            tasks = [make_request(i) for i in range(50)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            return results

        results = asyncio.run(simulate_concurrent_requests())

        successful = sum(1 for r in results if not isinstance(r, Exception) and r.get('success', False))
        failed = sum(1 for r in results if isinstance(r, Exception))

        # System should handle majority of requests even with failures
        assert successful + failed == 50
        assert successful >= 40  # At least 80% should succeed despite 10% failure rate

        print(f"Concurrent load test: {successful} successful, {failed} failed out of 50 requests")
```

This comprehensive edge case validation guide provides all the necessary techniques and patterns for implementing effective edge case testing in a pytest-based test suite.