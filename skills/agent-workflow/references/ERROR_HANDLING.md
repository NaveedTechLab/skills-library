# Error Handling and Recovery Patterns Reference

## Error Classification

### Types of Errors

Categorize errors to handle them appropriately:

```python
from enum import Enum
from typing import Dict, Any, Optional
import logging

class ErrorType(Enum):
    # Client-side errors
    INVALID_INPUT = "invalid_input"
    AUTHENTICATION_FAILED = "authentication_failed"
    PERMISSION_DENIED = "permission_denied"
    VALIDATION_ERROR = "validation_error"

    # Server-side errors
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Tool-specific errors
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_CONFIGURATION_ERROR = "tool_configuration_error"

    # State management errors
    STATE_LOAD_FAILED = "state_load_failed"
    STATE_SAVE_FAILED = "state_save_failed"
    CONCURRENT_ACCESS_ERROR = "concurrent_access_error"

    # External service errors
    EXTERNAL_API_ERROR = "external_api_error"
    NETWORK_ERROR = "network_error"
    DATA_INTEGRITY_ERROR = "data_integrity_error"

class ErrorContext:
    def __init__(
        self,
        error_type: ErrorType,
        message: str,
        customer_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        tool_name: Optional[str] = None
    ):
        self.error_type = error_type
        self.message = message
        self.customer_id = customer_id
        self.conversation_id = conversation_id
        self.tool_name = tool_name
        self.timestamp = datetime.now()
        self.retry_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "customer_id": self.customer_id,
            "conversation_id": self.conversation_id,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count
        }
```

## Error Handling Strategies

### 1. Fail-Fast Strategy

For critical errors that shouldn't be retried:

```python
def handle_critical_error(error_context: ErrorContext) -> str:
    """Handle critical errors that should not be retried."""
    logger.error(f"Critical error: {error_context.message}")

    # Log the error with full context
    log_error(error_context)

    # Return appropriate user-facing message
    if error_context.error_type == ErrorType.AUTHENTICATION_FAILED:
        return "I'm sorry, but I'm unable to authenticate with the required services. Please try again later."
    elif error_context.error_type == ErrorType.PERMISSION_DENIED:
        return "I don't have the necessary permissions to perform this action. Please contact support."
    else:
        return "I'm experiencing technical difficulties and cannot proceed. Please try again later."
```

### 2. Retry Strategy

For transient errors that might succeed on retry:

```python
import asyncio
import random
from typing import Callable, TypeVar, Awaitable

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> T:
    """Retry a function with exponential backoff and jitter."""
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries:
                # Last attempt, re-raise the exception
                raise e

            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** attempt), max_delay)

            # Add jitter to prevent thundering herd
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)

            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.2f}s...")
            await asyncio.sleep(delay)

    # This should never be reached
    raise Exception("Retry logic error")
```

### 3. Circuit Breaker Strategy

Prevent cascading failures:

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Temporarily disabled
    HALF_OPEN = "half_open" # Testing if recovered

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.last_attempt_time = None

    async def call(self, func, *args, **kwargs):
        """Call a function through the circuit breaker."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.timeout:
                # Timeout has passed, try again
                self.state = CircuitState.HALF_OPEN
                self.last_attempt_time = time.time()
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def on_success(self):
        """Called when a call succeeds."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def on_failure(self):
        """Called when a call fails."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the circuit breaker."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "is_available": self.state != CircuitState.OPEN
        }
```

## Tool Error Handling

### Tool-Specific Error Handling

Handle errors from individual tools:

```python
class ToolErrorHandler:
    def __init__(self):
        self.error_handlers = {
            "search_knowledge_base": self._handle_search_error,
            "create_ticket": self._handle_ticket_error,
            "get_customer_info": self._handle_customer_info_error,
            "send_notification": self._handle_notification_error
        }

    def handle_tool_error(self, tool_name: str, error: Exception, original_params: Dict) -> str:
        """Handle errors from specific tools."""
        handler = self.error_handlers.get(tool_name, self._handle_generic_tool_error)
        return handler(error, original_params)

    def _handle_search_error(self, error: Exception, params: Dict) -> str:
        """Handle errors from search tools."""
        if "rate limit" in str(error).lower():
            return "I'm currently experiencing high demand for search queries. Please try rephrasing your search or try again shortly."
        elif "timeout" in str(error).lower():
            return "The search service is taking too long to respond. Could you try a simpler search query?"
        else:
            return "I'm having trouble searching our knowledge base right now. Could you try rephrasing your question?"

    def _handle_ticket_error(self, error: Exception, params: Dict) -> str:
        """Handle errors from ticket creation tools."""
        error_str = str(error).lower()

        if "duplicate" in error_str:
            return "It looks like you already have a ticket with a similar issue. Let me find it for you."
        elif "validation" in error_str or "required" in error_str:
            return "I need a bit more information to create your ticket. Please provide a clear subject and description of the issue."
        elif "rate limit" in error_str:
            return "You've reached the maximum number of tickets you can create at this time. Please check your existing tickets."
        else:
            return "I'm having trouble creating your ticket right now. Would you like me to try again or connect you with a human agent?"

    def _handle_customer_info_error(self, error: Exception, params: Dict) -> str:
        """Handle errors from customer info tools."""
        if "not found" in str(error).lower():
            return "I couldn't find your account information. Please verify your details or contact support."
        elif "permission" in str(error).lower():
            return "I don't have permission to access your account information. Please contact support directly."
        else:
            return "I'm having trouble accessing your account information. Please try again later."

    def _handle_notification_error(self, error: Exception, params: Dict) -> str:
        """Handle errors from notification tools."""
        if "invalid" in str(error).lower() or "address" in str(error).lower():
            return "The notification couldn't be sent to your contact method. Please verify your contact information."
        else:
            return "I'm having trouble sending notifications right now. Is there another way I can assist you?"

    def _handle_generic_tool_error(self, error: Exception, params: Dict) -> str:
        """Generic handler for tool errors."""
        return f"I'm having trouble with the system right now: {str(error)}. Is there something else I can help you with?"
```

## State Error Recovery

### Graceful State Recovery

Handle state management errors gracefully:

```python
class StateRecoveryHandler:
    def __init__(self, primary_backend, backup_backend=None):
        self.primary_backend = primary_backend
        self.backup_backend = backup_backend
        self.logger = logging.getLogger(__name__)

    async def get_state_safe(self, customer_id: str) -> CustomerState:
        """Safely get customer state with fallbacks."""
        try:
            # Try primary backend first
            return await self.primary_backend.get_state(customer_id)
        except Exception as e:
            self.logger.warning(f"Primary state backend failed: {str(e)}")

            # Try backup backend if available
            if self.backup_backend:
                try:
                    state = await self.backup_backend.get_state(customer_id)
                    self.logger.info("Recovered state from backup backend")

                    # Try to sync back to primary
                    try:
                        await self.primary_backend.save_state(state)
                        self.logger.info("Synced state back to primary backend")
                    except Exception as sync_error:
                        self.logger.warning(f"Failed to sync state to primary: {sync_error}")

                    return state
                except Exception as backup_error:
                    self.logger.error(f"Backup state backend also failed: {backup_error}")

            # If both backends fail, create a new state
            self.logger.warning(f"Creating new state for customer {customer_id}")
            return CustomerState(customer_id)

    async def save_state_safe(self, state: CustomerState) -> bool:
        """Safely save customer state with fallbacks."""
        primary_success = False
        backup_success = False

        # Try primary backend
        try:
            await self.primary_backend.save_state(state)
            primary_success = True
        except Exception as e:
            self.logger.error(f"Failed to save state to primary backend: {str(e)}")

        # Try backup backend if primary failed or backup exists
        if not primary_success and self.backup_backend:
            try:
                await self.backup_backend.save_state(state)
                backup_success = True
                self.logger.info(f"Saved state to backup backend for customer {state.customer_id}")
            except Exception as e:
                self.logger.error(f"Failed to save state to backup backend: {str(e)}")

        # Return success status
        return primary_success or backup_success

    def handle_concurrent_access_error(self, customer_id: str) -> CustomerState:
        """Handle concurrent access errors by creating a new state."""
        self.logger.warning(f"Handling concurrent access for customer {customer_id}")

        # In case of concurrent access issues, load fresh state
        fresh_state = self.primary_backend.get_state(customer_id)

        # Clear any temporary state that might be corrupted
        fresh_state.clear_temp_state()

        return fresh_state
```

## Error Logging and Monitoring

### Structured Error Logging

Log errors with rich context for debugging:

```python
import traceback
from typing import Dict, Any

class StructuredErrorLogger:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_error(
        self,
        error_context: ErrorContext,
        extra_fields: Dict[str, Any] = None
    ):
        """Log an error with structured context."""
        error_details = {
            "error_type": error_context.error_type.value,
            "message": error_context.message,
            "timestamp": error_context.timestamp.isoformat(),
            "retry_count": error_context.retry_count,
            "customer_id": error_context.customer_id,
            "conversation_id": error_context.conversation_id,
            "tool_name": error_context.tool_name,
            "traceback": traceback.format_exc() if error_context.error_type != ErrorType.VALIDATION_ERROR else None
        }

        # Add any extra fields
        if extra_fields:
            error_details.update(extra_fields)

        # Log at appropriate level
        if error_context.error_type in [
            ErrorType.INTERNAL_ERROR,
            ErrorType.SERVICE_UNAVAILABLE,
            ErrorType.CONCURRENT_ACCESS_ERROR
        ]:
            self.logger.error("Agent Error", extra=error_details)
        else:
            self.logger.warning("Agent Warning", extra=error_details)

    def log_tool_error(
        self,
        tool_name: str,
        error: Exception,
        params: Dict[str, Any],
        customer_id: str = None
    ):
        """Log tool-specific errors."""
        error_context = ErrorContext(
            error_type=ErrorType.TOOL_EXECUTION_FAILED,
            message=str(error),
            tool_name=tool_name,
            customer_id=customer_id
        )

        extra_fields = {
            "tool_params": params,
            "error_class": error.__class__.__name__
        }

        self.log_error(error_context, extra_fields)

    def log_conversation_error(
        self,
        customer_id: str,
        conversation_id: str,
        error: Exception,
        user_input: str = None
    ):
        """Log conversation-specific errors."""
        error_context = ErrorContext(
            error_type=ErrorType.INTERNAL_ERROR,
            message=str(error),
            customer_id=customer_id,
            conversation_id=conversation_id
        )

        extra_fields = {
            "user_input": user_input,
            "error_class": error.__class__.__name__
        }

        self.log_error(error_context, extra_fields)
```

## Recovery Procedures

### Graceful Degradation

Provide fallback behaviors when errors occur:

```python
class GracefulDegradationHandler:
    def __init__(self):
        self.degraded_features = set()
        self.feature_dependencies = {
            "knowledge_search": ["search_api", "database"],
            "ticket_creation": ["ticket_system", "customer_db"],
            "notification": ["email_service", "sms_gateway"]
        }

    def check_degraded_mode(self, customer_id: str) -> Dict[str, bool]:
        """Check which features are currently degraded."""
        return {
            "knowledge_search": self.is_feature_degraded("knowledge_search"),
            "ticket_creation": self.is_feature_degraded("ticket_creation"),
            "notifications": self.is_feature_degraded("notification")
        }

    def is_feature_degraded(self, feature_name: str) -> bool:
        """Check if a specific feature is in degraded mode."""
        if feature_name in self.degraded_features:
            return True

        # Check if any dependencies are down
        dependencies = self.feature_dependencies.get(feature_name, [])
        for dep in dependencies:
            if f"{dep}_degraded" in self.degraded_features:
                return True

        return False

    def get_degraded_response(self, feature_name: str, original_request: str) -> str:
        """Provide an appropriate response when a feature is degraded."""
        if feature_name == "knowledge_search":
            return (
                "Our search system is currently experiencing issues. "
                "I can still help you by connecting you with a human agent "
                "who can access our full knowledge base. Would you like me to do that?"
            )
        elif feature_name == "ticket_creation":
            return (
                "I'm unable to create a ticket right now due to system issues. "
                "However, I can provide you with the direct contact information "
                "for our support team so you can submit your request manually."
            )
        elif feature_name == "notifications":
            return (
                "I can't send notifications right now, but I can provide you with "
                "the information you need directly in our conversation. "
                "Is there anything specific you'd like me to help you with?"
            )
        else:
            return (
                "Some of our services are temporarily unavailable. "
                "I'll do my best to help you with the available options. "
                "Is there something else I can assist you with?"
            )

    def handle_degraded_service(self, service_name: str, error: Exception):
        """Handle a service that has become degraded."""
        self.degraded_features.add(service_name)
        self.logger.warning(f"Service {service_name} is now in degraded mode")

        # Schedule a check to see if the service recovers
        asyncio.create_task(self._check_service_recovery(service_name))

    async def _check_service_recovery(self, service_name: str):
        """Periodically check if a degraded service has recovered."""
        import asyncio

        # Wait before checking (e.g., 5 minutes)
        await asyncio.sleep(300)

        # Try a simple health check
        if await self._is_service_healthy(service_name):
            self.degraded_features.discard(service_name)
            self.logger.info(f"Service {service_name} has recovered")
        else:
            # Service still down, check again later
            asyncio.create_task(self._check_service_recovery(service_name))

    async def _is_service_healthy(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        # Implementation depends on the specific service
        # This is a placeholder
        try:
            if service_name == "search_api":
                # Perform a simple search
                pass
            elif service_name == "ticket_system":
                # Check if we can access the ticket system
                pass
            elif service_name == "email_service":
                # Check if email service is responsive
                pass

            return True
        except:
            return False
```