#!/usr/bin/env python3
"""
Security Sandbox Controls - Environment-based safety controls

Implements DRY_RUN mode, rate limits, credential isolation, and permission boundaries
"""

import asyncio
import enum
import hashlib
import json
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Lock, RLock
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

import redis
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()


class OperationType(Enum):
    """Types of operations that can be controlled"""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    NETWORK_REQUEST = "network_request"
    SYSTEM_COMMAND = "system_command"
    CREDENTIAL_ACCESS = "credential_access"
    DATABASE_QUERY = "database_query"
    PROCESS_EXECUTION = "process_execution"


class SafetyMode(Enum):
    """Safety modes for operation execution"""
    DRY_RUN = "DRY_RUN"           # Simulate operations without executing
    DEVELOPMENT = "DEVELOPMENT"   # Less restrictive with more logging
    STAGING = "STAGING"          # Moderate restrictions
    PRODUCTION = "PRODUCTION"    # Strictest controls


class RateLimitExceededError(Exception):
    """Raised when rate limits are exceeded"""
    def __init__(self, operation: str, retry_after: float, message: str = None):
        self.operation = operation
        self.retry_after = retry_after
        if message is None:
            message = f"Rate limit exceeded for {operation}. Retry after {retry_after} seconds."
        super().__init__(message)


class PermissionDeniedError(Exception):
    """Raised when permission is denied for an operation"""
    pass


class SecurityViolationError(Exception):
    """Raised when a security violation occurs"""
    pass


@dataclass
class OperationResult:
    """Result of an operation"""
    success: bool
    operation: OperationType
    params: Dict[str, Any]
    mode: SafetyMode
    simulation: bool = False
    simulation_report: Optional[str] = None
    execution_time: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    max_operations: int
    window_seconds: int
    burst_allowance: int = 0
    per_user: bool = False
    per_resource: bool = False


@dataclass
class SafetyConfig:
    """Configuration for safety controls"""
    mode: SafetyMode = SafetyMode.DEVELOPMENT
    dry_run_enabled: bool = False
    rate_limits: Dict[str, RateLimitRule] = field(default_factory=dict)
    credentials_isolated: bool = True
    permission_enforcement: bool = True
    dangerous_operations_allowed: bool = False
    log_level: str = "INFO"
    audit_logging: bool = True
    environment: str = "development"

    def __post_init__(self):
        # Set default rate limits if not provided
        if not self.rate_limits:
            self.rate_limits = {
                "file_operations": RateLimitRule(max_operations=100, window_seconds=60),
                "network_requests": RateLimitRule(max_operations=50, window_seconds=60),
                "system_commands": RateLimitRule(max_operations=20, window_seconds=60),
                "credential_access": RateLimitRule(max_operations=10, window_seconds=60),
            }


class TokenBucket:
    """Token bucket implementation for rate limiting"""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.time()
        self.lock = Lock()

    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens from the bucket"""
        with self.lock:
            now = time.time()
            # Refill tokens based on time elapsed
            time_elapsed = now - self.last_refill
            new_tokens = time_elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def get_wait_time(self) -> float:
        """Get the time to wait before next token is available"""
        with self.lock:
            if self.tokens >= 1:
                return 0.0
            return (1.0 - self.tokens) / self.refill_rate


class RateLimiter:
    """Rate limiting manager"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.local_buckets: Dict[str, TokenBucket] = {}
        self.lock = RLock()

    def _get_bucket_key(self, operation: str, user: str = None, resource: str = None) -> str:
        """Generate a unique key for a rate limiting bucket"""
        parts = [operation]
        if user:
            parts.append(user)
        if resource:
            parts.append(resource)
        return ":".join(parts)

    def _get_local_bucket(self, key: str, capacity: int, refill_rate: float) -> TokenBucket:
        """Get or create a local token bucket"""
        with self.lock:
            if key not in self.local_buckets:
                self.local_buckets[key] = TokenBucket(capacity, refill_rate)
            return self.local_buckets[key]

    def check_rate_limit(
        self,
        operation: str,
        user: str = None,
        resource: str = None,
        rule: RateLimitRule = None
    ) -> Tuple[bool, float]:
        """
        Check if operation is allowed based on rate limits

        Returns: (allowed: bool, retry_after: float)
        """
        if rule is None:
            # Default to 100 operations per minute
            rule = RateLimitRule(max_operations=100, window_seconds=60)

        key = self._get_bucket_key(operation, user, resource)

        if self.redis_client:
            # Use Redis for distributed rate limiting
            return self._check_redis_rate_limit(key, rule)
        else:
            # Use local rate limiting
            return self._check_local_rate_limit(key, rule)

    def _check_redis_rate_limit(self, key: str, rule: RateLimitRule) -> Tuple[bool, float]:
        """Check rate limit using Redis"""
        # Implementation would use Redis for distributed rate limiting
        # For now, fall back to local implementation
        return self._check_local_rate_limit(key, rule)

    def _check_local_rate_limit(self, key: str, rule: RateLimitRule) -> Tuple[bool, float]:
        """Check rate limit using local token buckets"""
        # Calculate refill rate: max_operations per window_seconds
        refill_rate = rule.max_operations / rule.window_seconds
        capacity = rule.max_operations + rule.burst_allowance

        bucket = self._get_local_bucket(key, capacity, refill_rate)

        if bucket.consume():
            return True, 0.0
        else:
            wait_time = bucket.get_wait_time()
            return False, wait_time


class CredentialManager:
    """Secure credential management with isolation"""

    def __init__(self, encryption_key: Optional[bytes] = None):
        if encryption_key is None:
            encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(encryption_key)
        self.credentials_store: Dict[str, bytes] = {}
        self.access_log: List[Dict] = []
        self.lock = RLock()

    def store_credential(self, key: str, credential: str, encrypt: bool = True) -> bool:
        """Store a credential securely"""
        try:
            if encrypt:
                encrypted_credential = self.cipher_suite.encrypt(credential.encode())
                self.credentials_store[key] = encrypted_credential
            else:
                self.credentials_store[key] = credential.encode()

            logger.info("Credential stored", credential_key=key)
            return True
        except Exception as e:
            logger.error("Failed to store credential", credential_key=key, error=str(e))
            return False

    def get_credential(self, key: str, user: str = None) -> Optional[str]:
        """Retrieve a credential securely"""
        try:
            if key not in self.credentials_store:
                logger.warning("Credential not found", credential_key=key)
                return None

            encrypted_data = self.credentials_store[key]

            # Log access
            self.access_log.append({
                "timestamp": datetime.now().isoformat(),
                "credential_key": key,
                "user": user,
                "action": "retrieve"
            })

            # Decrypt if it was encrypted
            try:
                decrypted_data = self.cipher_suite.decrypt(encrypted_data)
                return decrypted_data.decode()
            except:
                # If decryption fails, assume it wasn't encrypted
                return encrypted_data.decode()

        except Exception as e:
            logger.error("Failed to retrieve credential", credential_key=key, error=str(e))
            return None

    def rotate_credential(self, key: str, new_credential: str) -> bool:
        """Rotate a credential"""
        try:
            old_credential = self.get_credential(key)
            success = self.store_credential(key, new_credential)

            if success:
                logger.info("Credential rotated", credential_key=key)
                return True
            return False
        except Exception as e:
            logger.error("Failed to rotate credential", credential_key=key, error=str(e))
            return False

    def get_access_log(self) -> List[Dict]:
        """Get credential access log"""
        return self.access_log.copy()


class PermissionManager:
    """Permission boundary management"""

    def __init__(self):
        self.roles: Dict[str, Set[str]] = {
            "admin": {"all_operations"},
            "standard_user": {
                "file_read", "file_write",
                "network_request", "basic_commands"
            },
            "restricted_user": {"file_read", "limited_network"}
        }
        self.user_roles: Dict[str, List[str]] = {}
        self.permissions_cache: Dict[Tuple[str, str], bool] = {}
        self.lock = RLock()

    def assign_role(self, user: str, role: str) -> bool:
        """Assign a role to a user"""
        if role not in self.roles:
            return False

        with self.lock:
            if user not in self.user_roles:
                self.user_roles[user] = []
            if role not in self.user_roles[user]:
                self.user_roles[user].append(role)

        # Clear cache for this user
        keys_to_remove = [k for k in self.permissions_cache.keys() if k[0] == user]
        for key in keys_to_remove:
            del self.permissions_cache[key]

        return True

    def check_permission(self, user: str, operation: str) -> bool:
        """Check if user has permission for operation"""
        cache_key = (user, operation)

        # Check cache first
        with self.lock:
            if cache_key in self.permissions_cache:
                return self.permissions_cache[cache_key]

        # Determine permissions
        has_permission = False
        user_roles = self.user_roles.get(user, [])

        for role in user_roles:
            role_permissions = self.roles.get(role, set())
            if "all_operations" in role_permissions or operation in role_permissions:
                has_permission = True
                break

        # Cache result
        with self.lock:
            self.permissions_cache[cache_key] = has_permission

        return has_permission

    def get_user_permissions(self, user: str) -> Set[str]:
        """Get all permissions for a user"""
        permissions = set()
        user_roles = self.user_roles.get(user, [])

        for role in user_roles:
            role_permissions = self.roles.get(role, set())
            permissions.update(role_permissions)

        return permissions


class SafetyControls:
    """Main safety controls class"""

    def __init__(self, config: SafetyConfig = None, redis_client: Optional[redis.Redis] = None):
        self.config = config or SafetyConfig()
        self.rate_limiter = RateLimiter(redis_client)
        self.credential_manager = CredentialManager()
        self.permission_manager = PermissionManager()
        self.audit_log: List[Dict] = []
        self.lock = RLock()

    def execute_operation(
        self,
        operation_type: OperationType,
        user: str = "anonymous",
        simulate: bool = False,
        **params
    ) -> OperationResult:
        """Execute an operation with safety controls"""
        start_time = time.time()

        # Check if operation is dangerous and allowed
        if self._is_dangerous_operation(operation_type) and not self.config.dangerous_operations_allowed:
            raise SecurityViolationError(f"Dangerous operation {operation_type.value} not allowed")

        # Check permissions
        if self.config.permission_enforcement:
            if not self.permission_manager.check_permission(user, operation_type.value):
                raise PermissionDeniedError(f"User {user} does not have permission for {operation_type.value}")

        # Check rate limits
        rate_limit_key = operation_type.value
        rule = self.config.rate_limits.get(rate_limit_key,
                                         RateLimitRule(max_operations=100, window_seconds=60))

        allowed, retry_after = self.rate_limiter.check_rate_limit(
            operation_type.value,
            user=user if rule.per_user else None,
            resource=params.get('resource') if rule.per_resource else None,
            rule=rule
        )

        if not allowed:
            raise RateLimitExceededError(operation_type.value, retry_after)

        # Determine if we should simulate based on mode and dry_run setting
        should_simulate = simulate or (
            self.config.mode == SafetyMode.DRY_RUN or
            (self.config.dry_run_enabled and self.config.mode != SafetyMode.PRODUCTION)
        )

        try:
            # Execute or simulate the operation
            if should_simulate:
                result = self._simulate_operation(operation_type, params)
                result.simulation = True
            else:
                result = self._execute_operation(operation_type, params)

            result.success = True
            result.execution_time = time.time() - start_time
            result.mode = self.config.mode

        except Exception as e:
            result = OperationResult(
                success=False,
                operation=operation_type,
                params=params,
                mode=self.config.mode,
                error=str(e),
                execution_time=time.time() - start_time
            )

        # Log the operation
        self._log_operation(result, user)

        return result

    def _is_dangerous_operation(self, operation_type: OperationType) -> bool:
        """Check if an operation is considered dangerous"""
        dangerous_ops = {
            OperationType.FILE_DELETE,
            OperationType.SYSTEM_COMMAND,
            OperationType.PROCESS_EXECUTION
        }
        return operation_type in dangerous_ops

    def _simulate_operation(self, operation_type: OperationType, params: Dict[str, Any]) -> OperationResult:
        """Simulate an operation without executing it"""
        simulation_report = f"SIMULATION: Would execute {operation_type.value} with params: {params}"

        return OperationResult(
            success=True,
            operation=operation_type,
            params=params,
            mode=self.config.mode,
            simulation=True,
            simulation_report=simulation_report
        )

    def _execute_operation(self, operation_type: OperationType, params: Dict[str, Any]) -> OperationResult:
        """Actually execute an operation"""
        # In a real implementation, this would execute the actual operation
        # For now, we'll just return a successful result
        return OperationResult(
            success=True,
            operation=operation_type,
            params=params,
            mode=self.config.mode
        )

    def _log_operation(self, result: OperationResult, user: str):
        """Log the operation for audit purposes"""
        if self.config.audit_logging:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "user": user,
                "operation": result.operation.value,
                "params": result.params,
                "mode": result.mode.value,
                "success": result.success,
                "simulation": result.simulation,
                "execution_time": result.execution_time,
                "error": result.error,
                "environment": self.config.environment
            }
            self.audit_log.append(log_entry)

    def get_audit_log(self) -> List[Dict]:
        """Get the audit log"""
        return self.audit_log.copy()

    def set_credential(self, key: str, value: str, encrypt: bool = True) -> bool:
        """Store a credential securely"""
        return self.credential_manager.store_credential(key, value, encrypt)

    def get_credential(self, key: str, user: str = None) -> Optional[str]:
        """Retrieve a credential securely"""
        return self.credential_manager.get_credential(key, user)

    def check_permission(self, user: str, operation: str) -> bool:
        """Check if user has permission for operation"""
        return self.permission_manager.check_permission(user, operation)

    def assign_role(self, user: str, role: str) -> bool:
        """Assign a role to a user"""
        return self.permission_manager.assign_role(user, role)

    def get_user_permissions(self, user: str) -> Set[str]:
        """Get all permissions for a user"""
        return self.permission_manager.get_user_permissions(user)


# Convenience functions for common operations
def dry_run_execute(
    operation_type: OperationType,
    safety_controls: SafetyControls,
    user: str = "anonymous",
    **params
) -> OperationResult:
    """Execute an operation in DRY_RUN mode"""
    return safety_controls.execute_operation(operation_type, user, simulate=True, **params)


def check_rate_limit(
    operation: str,
    safety_controls: SafetyControls,
    user: str = None,
    resource: str = None
) -> Tuple[bool, float]:
    """Check rate limit for an operation"""
    rule = safety_controls.config.rate_limits.get(operation)
    return safety_controls.rate_limiter.check_rate_limit(operation, user, resource, rule)


def initialize_safety_controls(
    mode: SafetyMode = SafetyMode.DEVELOPMENT,
    environment: str = "development"
) -> SafetyControls:
    """Initialize safety controls with default configuration"""
    config = SafetyConfig(
        mode=mode,
        dry_run_enabled=(mode == SafetyMode.DRY_RUN),
        environment=environment
    )
    return SafetyControls(config=config)


if __name__ == "__main__":
    # Example usage
    print("Security Sandbox Controls - Example Usage")

    # Initialize safety controls
    controls = initialize_safety_controls(SafetyMode.DRY_RUN, "development")

    # Assign a role to a user
    controls.assign_role("developer", "standard_user")

    # Store a credential
    controls.set_credential("api_key", "my_secret_key")

    # Execute operations in DRY_RUN mode
    try:
        result = controls.execute_operation(
            OperationType.FILE_WRITE,
            user="developer",
            path="/tmp/test.txt",
            content="test content"
        )
        print(f"Operation result: {result.simulation_report}")
    except Exception as e:
        print(f"Operation failed: {e}")

    # Try to access credential
    api_key = controls.get_credential("api_key", user="developer")
    print(f"Retrieved credential: {'***' if api_key else 'None'}")

    # Show audit log
    audit_log = controls.get_audit_log()
    print(f"Audit log entries: {len(audit_log)}")