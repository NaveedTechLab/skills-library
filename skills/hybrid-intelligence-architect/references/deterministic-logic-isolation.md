# Deterministic Logic Isolation Guide

## Core Principles

### Separation of Concerns
Maintaining strict isolation between deterministic business logic and AI-enhanced features is crucial for system reliability:

```
Core Business Logic (Deterministic)
├── User authentication and authorization
├── Financial transactions and calculations
├── Data validation and integrity checks
├── Audit logging and compliance
└── Core CRUD operations

AI-Enhanced Features (Non-Deterministic)
├── Content personalization
├── Adaptive learning paths
├── AI-graded assessments
├── Intelligent tutoring
└── Predictive analytics
```

### Architecture Pattern
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

class DeterministicService(ABC):
    """
    Abstract base class for deterministic services
    These services must maintain 100% reliability and predictability
    """

    @abstractmethod
    def execute_core_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute deterministic business logic
        This method must always return consistent results for the same input
        """
        pass

class AIFeatureService(ABC):
    """
    Abstract base class for AI-enhanced features
    These services can fail gracefully without affecting core functionality
    """

    @abstractmethod
    def enhance_with_ai(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Enhance functionality with AI
        This method can return None or fallback results if AI is unavailable
        """
        pass

class HybridService:
    """
    Orchestrator that combines deterministic and AI-enhanced services
    """
    def __init__(self, deterministic_service: DeterministicService, ai_service: Optional[AIFeatureService] = None):
        self.deterministic_service = deterministic_service
        self.ai_service = ai_service
        self.logger = logging.getLogger(__name__)

    def execute_with_fallback(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute core logic and optionally enhance with AI
        Always falls back to deterministic behavior if AI is unavailable
        """
        # Execute core deterministic logic first
        result = self.deterministic_service.execute_core_logic(data)

        # Optionally enhance with AI if available
        if self.ai_service:
            try:
                ai_enhancement = self.ai_service.enhance_with_ai(data)
                if ai_enhancement:
                    result.update(ai_enhancement)
                    result['enhancement_applied'] = True
            except Exception as e:
                # Log the failure but don't let it break core functionality
                self.logger.warning(f"AI enhancement failed: {e}")
                result['enhancement_applied'] = False
                result['fallback_used'] = True

        return result
```

## Implementation Patterns

### 1. Circuit Breaker Pattern for AI Services
```python
import time
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service temporarily unavailable
    HALF_OPEN = "half_open" # Testing if service is restored

class AICircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.logger = logging.getLogger(__name__)

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call AI function with circuit breaker protection
        """
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (time.time() - self.last_failure_time > self.timeout):
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit breaker transitioning to HALF_OPEN state")
            else:
                self.logger.warning("Circuit breaker is OPEN - AI service unavailable")
                raise AICircuitBreakerOpenError("AI service is temporarily unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """
        Called when AI call succeeds
        """
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        if self.state == CircuitState.HALF_OPEN:
            self.logger.info("AI service restored - circuit breaker closed")

    def _on_failure(self):
        """
        Called when AI call fails
        """
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.error(f"Circuit breaker OPENED after {self.failure_threshold} failures")

    def force_close(self):
        """
        Force circuit breaker to closed state
        """
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.logger.info("Circuit breaker forced to CLOSED state")

class AICircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and AI service is unavailable"""
    pass
```

### 2. Fallback Strategy Pattern
```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

@runtime_checkable
class AIEnhancementProtocol(Protocol):
    def enhance(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ...

class FallbackStrategy(ABC):
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the fallback strategy
        """
        pass

class KeywordMatchingFallback(FallbackStrategy):
    """
    Fallback strategy using keyword matching for content recommendation
    """
    def __init__(self, content_repository):
        self.content_repository = content_repository

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommend content based on keyword matching
        """
        user_interests = input_data.get('interests', [])
        user_skills = input_data.get('skills', [])

        # Combine interests and skills for matching
        keywords = user_interests + user_skills

        recommended_content = []
        for content in self.content_repository.get_all_content():
            content_score = self._calculate_keyword_match_score(content, keywords)
            if content_score > 0.3:  # Threshold for relevance
                recommended_content.append({
                    'id': content['id'],
                    'title': content['title'],
                    'relevance_score': content_score,
                    'type': content.get('type', 'unknown')
                })

        # Sort by relevance score
        recommended_content.sort(key=lambda x: x['relevance_score'], reverse=True)

        return {
            'recommended_content': recommended_content[:5],  # Top 5 recommendations
            'recommendation_method': 'keyword_matching',
            'fallback_reason': 'AI service unavailable'
        }

    def _calculate_keyword_match_score(self, content: Dict[str, Any], keywords: list) -> float:
        """
        Calculate match score based on keyword occurrence
        """
        content_text = (content.get('title', '') + ' ' + content.get('description', '')).lower()
        content_words = set(content_text.split())

        matching_words = content_words.intersection(set([word.lower() for word in keywords]))
        if not content_words:
            return 0.0

        return len(matching_words) / len(content_words)

class PopularityBasedFallback(FallbackStrategy):
    """
    Fallback strategy using popularity metrics
    """
    def __init__(self, content_repository, analytics_service):
        self.content_repository = content_repository
        self.analytics_service = analytics_service

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommend content based on popularity and engagement
        """
        user_level = input_data.get('level', 'beginner')
        category = input_data.get('category', 'all')

        # Get popular content for user's level and category
        popular_content = self.analytics_service.get_popular_content(
            level=user_level,
            category=category,
            limit=10
        )

        return {
            'recommended_content': popular_content,
            'recommendation_method': 'popularity_based',
            'fallback_reason': 'AI service unavailable'
        }

class DeterministicRecommendationService:
    """
    Service that provides recommendations with guaranteed fallbacks
    """
    def __init__(self, ai_enhancer: Optional[AIEnhancementProtocol], fallback_strategies: list):
        self.ai_enhancer = ai_enhancer
        self.fallback_strategies = fallback_strategies
        self.circuit_breaker = AICircuitBreaker()

    def get_recommendations(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get recommendations with fallback chain
        """
        # Try AI enhancement first
        if self.ai_enhancer:
            try:
                ai_result = self.circuit_breaker.call(
                    self.ai_enhancer.enhance, input_data
                )
                if ai_result:
                    return {
                        **ai_result,
                        'enhancement_method': 'ai_generated',
                        'fallback_used': False
                    }
            except AICircuitBreakerOpenError:
                # Circuit breaker is open, use fallbacks
                pass
            except Exception as e:
                # AI service failed, use fallbacks
                logging.warning(f"AI enhancement failed: {e}")

        # Use fallback strategies in sequence
        for fallback_strategy in self.fallback_strategies:
            try:
                result = fallback_strategy.execute(input_data)
                result['fallback_used'] = True
                return result
            except Exception as e:
                logging.warning(f"Fallback strategy {type(fallback_strategy).__name__} failed: {e}")
                continue

        # If all fallbacks fail, return basic default recommendations
        return {
            'recommended_content': [],
            'recommendation_method': 'default',
            'fallback_used': True,
            'fallback_reason': 'all_enhancement_methods_failed'
        }
```

## Data Integrity and Validation

### 3. Validation Isolation
```python
from typing import Union
import re
from dataclasses import dataclass

@dataclass
class ValidationResult:
    is_valid: bool
    errors: list
    warnings: list

class CoreDataValidator:
    """
    Core validation that must always work - no external dependencies
    """
    @staticmethod
    def validate_email(email: str) -> ValidationResult:
        """
        Validate email format using regex (deterministic)
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_valid = bool(re.match(pattern, email))

        return ValidationResult(
            is_valid=is_valid,
            errors=[] if is_valid else [f"Invalid email format: {email}"],
            warnings=[]
        )

    @staticmethod
    def validate_user_data(data: Dict[str, Any]) -> ValidationResult:
        """
        Validate user registration data
        """
        errors = []
        warnings = []

        # Required fields
        required_fields = ['email', 'password', 'name']
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Required field '{field}' is missing or empty")

        # Email validation
        if 'email' in data:
            email_validation = CoreDataValidator.validate_email(data['email'])
            if not email_validation.is_valid:
                errors.extend(email_validation.errors)

        # Password strength (deterministic rules)
        if 'password' in data:
            password_validation = CoreDataValidator.validate_password_strength(data['password'])
            if not password_validation.is_valid:
                errors.extend(password_validation.errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    @staticmethod
    def validate_password_strength(password: str) -> ValidationResult:
        """
        Validate password strength using deterministic rules
        """
        errors = []

        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")

        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")

        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")

        if not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=[]
        )

class EnhancedDataValidator(CoreDataValidator):
    """
    Enhanced validator that adds AI-powered validation as optional enhancement
    """
    def __init__(self, ai_validator: Optional[AIEnhancementProtocol] = None):
        self.ai_validator = ai_validator
        self.core_validator = CoreDataValidator()
        self.circuit_breaker = AICircuitBreaker()

    def validate_user_data_enhanced(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate user data with optional AI-enhanced checks
        """
        # Always perform core validation
        core_result = self.core_validator.validate_user_data(data)

        # Optionally enhance with AI validation
        if self.ai_validator:
            try:
                ai_validation_result = self.circuit_breaker.call(
                    self.ai_validator.enhance,
                    {'validation_data': data, 'core_result': core_result}
                )

                if ai_validation_result and 'enhanced_validation' in ai_validation_result:
                    # Merge AI validation results with core results
                    core_result.warnings.extend(
                        ai_validation_result['enhanced_validation'].get('warnings', [])
                    )

            except Exception as e:
                # AI validation failed, but core validation still stands
                logging.warning(f"AI validation failed: {e}")
                # Continue with core validation results only

        return core_result
```

## Error Handling and Graceful Degradation

### 4. Error Isolation Pattern
```python
from contextlib import contextmanager
from typing import Generator, TypeVar, Type
import traceback

T = TypeVar('T')

class AIErrors:
    """
    Custom exceptions for AI-related failures
    """
    class AIAvailabilityError(Exception):
        """Raised when AI service is unavailable"""
        pass

    class AIProcessingError(Exception):
        """Raised when AI processing fails"""
        pass

    class AIResponseValidationError(Exception):
        """Raised when AI response doesn't meet validation criteria"""
        pass

class ErrorIsolator:
    """
    Isolate AI-related errors from core application logic
    """
    @staticmethod
    @contextmanager
    def isolate_ai_errors(
        fallback_value: T,
        logger: logging.Logger,
        error_types: tuple = (Exception,)
    ) -> Generator[T, None, None]:
        """
        Context manager to isolate AI errors and return fallback value
        """
        try:
            yield fallback_value
        except error_types as e:
            logger.warning(f"AI service error isolated: {e}")
            logger.debug(traceback.format_exc())
            # Return the fallback value that was yielded
            return

    @staticmethod
    def safe_ai_call(
        ai_function: Callable,
        fallback_function: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Safely call AI function with fallback
        """
        try:
            return ai_function(*args, **kwargs)
        except AIErrors.AIAvailabilityError:
            logging.warning("AI service unavailable, using fallback")
            return fallback_function(*args, **kwargs)
        except AIErrors.AIProcessingError as e:
            logging.warning(f"AI processing failed: {e}, using fallback")
            return fallback_function(*args, **kwargs)
        except AIErrors.AIResponseValidationError as e:
            logging.warning(f"AI response invalid: {e}, using fallback")
            return fallback_function(*args, **kwargs)
        except Exception as e:
            logging.error(f"Unexpected AI error: {e}, using fallback")
            return fallback_function(*args, **kwargs)

class GracefulDegradationService:
    """
    Service that degrades gracefully when AI services fail
    """
    def __init__(self, ai_enhancer: Optional[AIEnhancementProtocol] = None):
        self.ai_enhancer = ai_enhancer
        self.logger = logging.getLogger(__name__)

    def process_with_degradation(
        self,
        input_data: Dict[str, Any],
        processing_steps: list
    ) -> Dict[str, Any]:
        """
        Process data with graceful degradation
        Each step can fail independently without breaking the whole process
        """
        result = {}

        for step_name, step_function in processing_steps:
            try:
                step_result = step_function(input_data)
                result[step_name] = {
                    'success': True,
                    'data': step_result,
                    'degraded': False
                }
            except Exception as e:
                self.logger.warning(f"Step {step_name} failed: {e}")

                # Provide default result for failed step
                result[step_name] = {
                    'success': False,
                    'data': self._get_default_step_result(step_name),
                    'degraded': True,
                    'error': str(e)
                }

                # Continue with other steps
                continue

        # Mark overall result as degraded if any step failed
        result['overall_degraded'] = any(
            not step_result['success']
            for step_name, step_result in result.items()
            if step_name != 'overall_degraded'
        )

        return result

    def _get_default_step_result(self, step_name: str) -> Any:
        """
        Get default result for failed step
        """
        defaults = {
            'recommendation': [],
            'analysis': {'summary': 'Processing unavailable'},
            'grading': {'score': 0, 'feedback': 'Service temporarily unavailable'},
            'personalization': {'theme': 'default', 'layout': 'standard'}
        }
        return defaults.get(step_name, {})
```

## Transaction Safety and Auditing

### 5. Transaction Isolation
```python
from contextlib import contextmanager
import sqlite3
from typing import Optional

class TransactionManager:
    """
    Manage database transactions with AI service isolation
    Core operations must succeed regardless of AI service availability
    """
    def __init__(self, db_connection):
        self.db = db_connection
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def transaction(self, ai_operations_allowed: bool = True):
        """
        Context manager for database transactions
        AI operations are isolated and won't affect core transaction
        """
        original_isolation_level = self.db.isolation_level
        self.db.isolation_level = None  # Begin transaction
        cursor = self.db.cursor()

        try:
            # Execute core operations that must succeed
            yield cursor

            # If AI operations are allowed and we have them, execute separately
            if ai_operations_allowed:
                self._execute_ai_operations_separately()

            self.db.commit()
            self.logger.info("Transaction committed successfully")

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            self.db.isolation_level = original_isolation_level

    def _execute_ai_operations_separately(self):
        """
        Execute AI-related operations in separate, non-critical transactions
        These operations don't affect core business logic
        """
        try:
            # AI operations that can fail without affecting core transaction
            # For example: updating recommendation models, logging AI interactions
            ai_cursor = self.db.cursor()

            # Execute AI-specific operations
            ai_cursor.execute("UPDATE ai_models SET last_trained = ? WHERE active = 1",
                             (datetime.utcnow(),))

            ai_cursor.close()
            self.logger.info("AI operations completed")
        except Exception as e:
            # AI operations failed, but core transaction is unaffected
            self.logger.warning(f"AI operations failed: {e}")
            # Don't re-raise - core transaction should still commit

class AuditTrailManager:
    """
    Maintain audit trails that work regardless of AI service availability
    """
    def __init__(self, db_connection):
        self.db = db_connection
        self.logger = logging.getLogger(__name__)

    def log_action(self, action: str, user_id: str, details: Dict[str, Any], ai_influenced: bool = False):
        """
        Log user action to audit trail
        This must always work, regardless of AI service status
        """
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO audit_log (action, user_id, details, ai_influenced, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (action, user_id, json.dumps(details), ai_influenced, datetime.utcnow()))

            self.db.commit()
            self.logger.info(f"Audit log entry created for action: {action}")

        except Exception as e:
            # Critical - audit logging must work
            self.logger.error(f"Audit logging failed: {e}")
            # In a real system, you might want to raise this as it's critical
            raise

    def log_ai_interaction(self, user_id: str, ai_request: Dict[str, Any], ai_response: Dict[str, Any]):
        """
        Log AI interaction - this can fail without affecting core operations
        """
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO ai_interactions (user_id, request, response, timestamp)
                VALUES (?, ?, ?, ?)
            """, (user_id, json.dumps(ai_request), json.dumps(ai_response), datetime.utcnow()))

            self.db.commit()
            self.logger.info("AI interaction logged")

        except Exception as e:
            # Non-critical - AI logging can fail without affecting core functionality
            self.logger.warning(f"AI interaction logging failed: {e}")
            # Don't re-raise - core operations continue
```

## Configuration and Feature Flags

### 6. Feature Flag Isolation
```python
import json
from typing import Any, Dict

class FeatureFlagManager:
    """
    Manage feature flags that control AI service usage
    Allow disabling AI features without changing code
    """
    def __init__(self, config_source: str = "database"):
        self.config_source = config_source
        self._feature_flags_cache = {}
        self.logger = logging.getLogger(__name__)

    def is_feature_enabled(self, feature_name: str, user_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if a feature is enabled
        This method must always return a value, even if config source is unavailable
        """
        try:
            # Try to get from cache first
            if feature_name in self._feature_flags_cache:
                return self._feature_flags_cache[feature_name]

            # Load from config source
            if self.config_source == "database":
                flag_value = self._get_flag_from_database(feature_name)
            elif self.config_source == "file":
                flag_value = self._get_flag_from_file(feature_name)
            else:
                flag_value = self._get_flag_from_database(feature_name)  # fallback

            # Apply user context if provided (for gradual rollouts)
            if user_context:
                flag_value = self._apply_user_context(flag_value, user_context, feature_name)

            # Cache the result
            self._feature_flags_cache[feature_name] = flag_value
            return flag_value

        except Exception as e:
            self.logger.warning(f"Feature flag lookup failed for {feature_name}: {e}")
            # Default to False for AI features as a safety measure
            default_value = feature_name not in ['ai_tutoring', 'ai_assessment', 'ai_personalization']
            return default_value

    def _get_flag_from_database(self, feature_name: str) -> bool:
        """
        Get feature flag from database
        """
        cursor = self.db.cursor()
        result = cursor.execute(
            "SELECT enabled FROM feature_flags WHERE name = ?",
            (feature_name,)
        ).fetchone()

        return result[0] if result else False

    def _get_flag_from_file(self, feature_name: str) -> bool:
        """
        Get feature flag from configuration file
        """
        try:
            with open('config/features.json', 'r') as f:
                config = json.load(f)
            return config.get(feature_name, False)
        except FileNotFoundError:
            return False

    def _apply_user_context(self, flag_value: bool, user_context: Dict[str, Any], feature_name: str) -> bool:
        """
        Apply user-specific context to feature flag (for gradual rollouts)
        """
        if not flag_value:
            return False  # If globally disabled, remain disabled

        # Example: enable for premium users only
        user_tier = user_context.get('tier', 'free')
        if feature_name.startswith('ai_') and user_tier not in ['premium', 'enterprise']:
            return False

        return flag_value

class IsolatedFeatureService:
    """
    Service that isolates AI features behind feature flags
    """
    def __init__(self, feature_flags: FeatureFlagManager, ai_services: Dict[str, Any]):
        self.feature_flags = feature_flags
        self.ai_services = ai_services
        self.logger = logging.getLogger(__name__)

    def get_enhanced_features(self, user_id: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get all enhanced features, respecting feature flags
        """
        result = {}

        # Check each AI feature individually
        ai_features = [
            ('ai_recommendations', 'recommendations'),
            ('ai_assessment', 'assessment'),
            ('ai_tutoring', 'tutoring'),
            ('ai_personalization', 'personalization')
        ]

        for flag_name, service_name in ai_features:
            if self.feature_flags.is_feature_enabled(flag_name, user_context):
                try:
                    if service_name in self.ai_services:
                        service = self.ai_services[service_name]
                        result[service_name] = service.process(user_id, user_context)
                    else:
                        result[service_name] = {'enabled': True, 'data': {}}
                except Exception as e:
                    self.logger.warning(f"AI feature {service_name} failed: {e}")
                    # Continue with other features
            else:
                result[service_name] = {'enabled': False, 'fallback': True}

        return result
```

This guide provides comprehensive patterns for maintaining strict isolation between deterministic business logic and AI-enhanced features, ensuring system reliability while leveraging AI capabilities.