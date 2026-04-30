# Message Reliability Patterns

## Overview

This document covers patterns and best practices for ensuring message reliability in the Kafka-based event streaming system. Reliability encompasses message delivery guarantees, error handling, and recovery mechanisms.

## Delivery Guarantees

### At-Least-Once Delivery

```python
from kafka import KafkaConsumer, KafkaProducer
import json
import logging
from typing import Dict, Any, Callable

class AtLeastOnceConsumer:
    """
    Consumer that implements at-least-once delivery semantics.
    Messages are processed before offsets are committed.
    """

    def __init__(self, consumer: KafkaConsumer, logger: logging.Logger):
        self.consumer = consumer
        self.logger = logger

    def process_with_manual_commit(self, processor_func: Callable[[Dict[str, Any]], bool]):
        """
        Process messages with manual offset commitment for at-least-once semantics.

        Args:
            processor_func: Function that processes a message and returns success status

        Returns:
            True if message was processed successfully, False otherwise
        """
        for message in self.consumer:
            try:
                # Process the message
                success = processor_func(message.value)

                if success:
                    # Only commit offset after successful processing
                    self.consumer.commit()
                    self.logger.info(
                        f'Successfully processed and committed offset for '
                        f'{message.topic}[{message.partition}] at {message.offset}'
                    )
                    return True
                else:
                    self.logger.warning(
                        f'Processing failed for {message.topic}[{message.partition}] '
                        f'at {message.offset}, not committing offset'
                    )
                    return False

            except Exception as e:
                self.logger.error(
                    f'Error processing message {message.topic}[{message.partition}] '
                    f'at {message.offset}: {e}'
                )
                # Don't commit offset on error to ensure redelivery
                return False
```

### Exactly-Once Semantics with Transactions

```python
from kafka import KafkaProducer, KafkaConsumer
import json
import uuid

class ExactlyOnceProcessor:
    """
    Processor that implements exactly-once semantics using Kafka transactions.
    Ensures atomic operations across multiple topics.
    """

    def __init__(self, bootstrap_servers: str):
        # Producer with idempotence enabled for exactly-once semantics
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',
            retries=2147483647,
            max_in_flight_requests_per_connection=5,
            enable_idempotence=True,  # Critical for exactly-once
        )

        # Unique transactional ID per instance
        self.transactional_id = f"exactly_once_processor_{uuid.uuid4()}"

    def process_with_transaction(self,
                               input_message: Dict[str, Any],
                               output_topics: Dict[str, Dict[str, Any]]) -> bool:
        """
        Process a message and produce to multiple topics atomically.

        Args:
            input_message: The input message to process
            output_topics: Dictionary mapping topic names to message payloads

        Returns:
            True if transaction completed successfully, False otherwise
        """
        try:
            # Initialize transaction with unique ID
            self.producer.init_transactions()

            # Begin transaction
            self.producer.begin_transaction()

            # Process and send messages to multiple topics
            sent_messages = []
            for topic, message in output_topics.items():
                future = self.producer.send(topic, value=message)
                record_metadata = future.get(timeout=10)
                sent_messages.append((topic, record_metadata))

            # Commit transaction - all messages are sent atomically
            self.producer.commit_transaction()

            print(f'Transaction completed successfully: {sent_messages}')
            return True

        except Exception as e:
            print(f'Transaction failed, aborting: {e}')
            try:
                # Abort transaction on error
                self.producer.abort_transaction()
            except Exception as abort_error:
                print(f'Error aborting transaction: {abort_error}')
            return False
```

### Deduplication with Producer IDs

```python
class DeduplicatingProducer:
    """
    Producer that prevents duplicate messages using producer IDs and sequence numbers.
    """

    def __init__(self, bootstrap_servers: str):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            enable_idempotence=True,  # Enables deduplication
        )

        # Track message sequence per partition key
        self.sequence_tracker = {}

    def send_with_deduplication(self, topic: str, message: Dict[str, Any],
                              key: str = None) -> bool:
        """
        Send a message with deduplication based on key and sequence.

        Args:
            topic: Destination topic
            message: Message payload
            key: Partition key for deduplication

        Returns:
            True if message was sent successfully
        """
        try:
            # Add sequence number to message if key is provided
            if key:
                seq_num = self.sequence_tracker.get(key, 0) + 1
                self.sequence_tracker[key] = seq_num
                message['sequence_number'] = seq_num

            future = self.producer.send(topic, value=message, key=key)
            record_metadata = future.get(timeout=10)

            print(f'Message sent to {topic}[{record_metadata.partition}] '
                  f'at offset {record_metadata.offset}')
            return True

        except Exception as e:
            print(f'Error sending message: {e}')
            return False
```

## Dead Letter Queue (DLQ) Patterns

### Basic DLQ Handler

```python
import datetime
from typing import Optional

class DeadLetterQueueHandler:
    """
    Handler for messages that repeatedly fail processing and need to be moved to DLQ.
    """

    def __init__(self, dlq_topic: str, producer: KafkaProducer,
                 max_retries: int = 3, retry_delay: int = 60):
        self.dlq_topic = dlq_topic
        self.producer = producer
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # In production, use Redis or database to track retry counts
        self.retry_counts = {}

    def send_to_dlq(self, original_message: Dict[str, Any],
                   error: Exception, original_topic: str,
                   original_partition: int, original_offset: int) -> bool:
        """
        Send a failed message to the dead letter queue.

        Args:
            original_message: The message that failed to process
            error: The error that occurred during processing
            original_topic: Original topic of the message
            original_partition: Original partition of the message
            original_offset: Original offset of the message

        Returns:
            True if message was successfully sent to DLQ
        """
        # Create DLQ message with original message and error context
        dlq_message = {
            'original_message': original_message,
            'error': str(error),
            'original_topic': original_topic,
            'original_partition': original_partition,
            'original_offset': original_offset,
            'failed_at': datetime.datetime.utcnow().isoformat(),
            'retry_count': self._get_retry_count(original_message),
            'max_retries_exceeded': self._get_retry_count(original_message) >= self.max_retries
        }

        try:
            future = self.producer.send(self.dlq_topic, value=dlq_message)
            record_metadata = future.get(timeout=10)

            print(f'Message sent to DLQ {self.dlq_topic}[{record_metadata.partition}] '
                  f'at offset {record_metadata.offset}')

            # Remove from retry tracker if max retries exceeded
            if dlq_message['max_retries_exceeded']:
                self._remove_retry_count(original_message)

            return True

        except Exception as e:
            print(f'Error sending to DLQ: {e}')
            return False

    def _get_retry_count(self, message: Dict[str, Any]) -> int:
        """Get the retry count for a message."""
        # In production, use Redis or database lookup
        # For this example, use a simple in-memory tracker
        message_key = self._generate_message_key(message)
        return self.retry_counts.get(message_key, 0)

    def _generate_message_key(self, message: Dict[str, Any]) -> str:
        """Generate a unique key for the message for tracking purposes."""
        import hashlib
        import json

        # Create a hash of the message content (excluding timestamp fields)
        content_to_hash = {
            k: v for k, v in message.items()
            if k not in ['timestamp', 'processed_at', 'correlation_id']
        }

        message_hash = hashlib.sha256(
            json.dumps(content_to_hash, sort_keys=True).encode()
        ).hexdigest()

        return message_hash

    def _remove_retry_count(self, message: Dict[str, Any]):
        """Remove retry count for a message after max retries."""
        message_key = self._generate_message_key(message)
        self.retry_counts.pop(message_key, None)
```

### Retry Topic Pattern

```python
class RetryTopicHandler:
    """
    Handler that implements retry topics with exponential backoff.
    Messages that fail processing are sent to increasingly delayed retry topics.
    """

    def __init__(self, producer: KafkaProducer, base_retry_topic: str = 'retry'):
        self.producer = producer
        self.base_retry_topic = base_retry_topic
        self.retry_intervals = [10, 30, 60, 300, 900]  # 10s, 30s, 1m, 5m, 15m

    def send_to_retry_topic(self, message: Dict[str, Any], error: Exception,
                           current_retry_count: int) -> bool:
        """
        Send a failed message to an appropriate retry topic based on retry count.

        Args:
            message: The failed message
            error: The error that occurred
            current_retry_count: Current retry attempt number

        Returns:
            True if message was sent to retry topic
        """
        # Determine which retry topic to use based on retry count
        if current_retry_count < len(self.retry_intervals):
            retry_topic = f"{self.base_retry_topic}.{self.retry_intervals[current_retry_count]}s"
        else:
            # Max retries reached, send to DLQ
            retry_topic = f"{self.base_retry_topic}.dlq"

        retry_message = {
            'original_message': message,
            'error': str(error),
            'retry_count': current_retry_count + 1,
            'scheduled_retry_at': (
                datetime.datetime.utcnow() +
                datetime.timedelta(seconds=self.retry_intervals[min(current_retry_count, len(self.retry_intervals)-1)])
            ).isoformat(),
            'retry_topic': retry_topic
        }

        try:
            future = self.producer.send(retry_topic, value=retry_message)
            record_metadata = future.get(timeout=10)

            print(f'Message sent to retry topic {retry_topic}[{record_metadata.partition}] '
                  f'at offset {record_metadata.offset}')
            return True

        except Exception as e:
            print(f'Error sending to retry topic: {e}')
            return False
```

## Message Validation and Filtering

### Schema Validation

```python
import jsonschema
from typing import Dict, Any

class MessageValidator:
    """
    Validator for ensuring messages conform to expected schemas.
    """

    def __init__(self):
        # Define schemas for different message types
        self.schemas = {
            'email_received': {
                'type': 'object',
                'properties': {
                    'channel': {'const': 'email'},
                    'message_type': {'const': 'email_received'},
                    'payload': {
                        'type': 'object',
                        'properties': {
                            'from_email': {'type': 'string', 'format': 'email'},
                            'to_email': {'type': 'string', 'format': 'email'},
                            'subject': {'type': 'string'},
                            'body': {'type': 'string'},
                            'timestamp': {'type': 'string', 'format': 'date-time'}
                        },
                        'required': ['from_email', 'to_email', 'subject', 'body', 'timestamp']
                    }
                },
                'required': ['channel', 'message_type', 'payload']
            },
            'whatsapp_received': {
                'type': 'object',
                'properties': {
                    'channel': {'const': 'whatsapp'},
                    'message_type': {'const': 'whatsapp_received'},
                    'payload': {
                        'type': 'object',
                        'properties': {
                            'sender_id': {'type': 'string'},
                            'recipient_id': {'type': 'string'},
                            'message_text': {'type': 'string'},
                            'timestamp': {'type': 'string', 'format': 'date-time'}
                        },
                        'required': ['sender_id', 'recipient_id', 'message_text', 'timestamp']
                    }
                },
                'required': ['channel', 'message_type', 'payload']
            }
        }

    def validate_message(self, message: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a message against its schema.

        Args:
            message: The message to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        message_type = message.get('message_type')

        if not message_type or message_type not in self.schemas:
            return False, f"Unknown message type: {message_type}"

        schema = self.schemas[message_type]

        try:
            jsonschema.validate(instance=message, schema=schema)
            return True, None
        except jsonschema.ValidationError as e:
            return False, f"Validation error: {e.message}"
```

### Message Filtering

```python
class MessageFilter:
    """
    Filter for rejecting invalid or unwanted messages before processing.
    """

    def __init__(self):
        self.validator = MessageValidator()
        self.blocked_senders = set()  # In production, load from database
        self.max_message_size = 1024 * 1024  # 1MB

    def filter_message(self, topic: str, message: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Filter a message to determine if it should be processed.

        Args:
            topic: The topic the message came from
            message: The message to filter

        Returns:
            Tuple of (should_process, rejection_reason)
        """
        # Check message size
        message_size = len(json.dumps(message).encode('utf-8'))
        if message_size > self.max_message_size:
            return False, f"Message too large: {message_size} bytes"

        # Validate message structure
        is_valid, validation_error = self.validator.validate_message(message)
        if not is_valid:
            return False, f"Invalid message: {validation_error}"

        # Check for blocked senders (apply to email/WhatsApp messages)
        sender = self._extract_sender(message)
        if sender and sender in self.blocked_senders:
            return False, f"Sender blocked: {sender}"

        # Check for spam patterns
        if self._is_spam_message(message):
            return False, "Spam content detected"

        return True, None

    def _extract_sender(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract sender from message."""
        payload = message.get('payload', {})

        if message.get('channel') == 'email':
            return payload.get('from_email')
        elif message.get('channel') == 'whatsapp':
            return payload.get('sender_id')

        return None

    def _is_spam_message(self, message: Dict[str, Any]) -> bool:
        """Check if message contains spam patterns."""
        payload = message.get('payload', {})
        content = payload.get('body', '') or payload.get('message_text', '')

        spam_keywords = [
            'free money', 'click here', 'urgent action required',
            'congratulations you won', 'act now'
        ]

        content_lower = content.lower()
        return any(keyword in content_lower for keyword in spam_keywords)
```

## Duplicate Detection

### Redis-Based Duplicate Detection

```python
import redis
import hashlib
import time
from typing import Optional

class DuplicateDetector:
    """
    Detector for identifying and preventing duplicate messages.
    Uses Redis to store message fingerprints with TTL.
    """

    def __init__(self, redis_client: redis.Redis, window_minutes: int = 1440):
        """
        Initialize duplicate detector.

        Args:
            redis_client: Redis client instance
            window_minutes: Time window in minutes to check for duplicates
        """
        self.redis = redis_client
        self.window_seconds = window_minutes * 60

    def is_duplicate(self, message: Dict[str, Any]) -> bool:
        """
        Check if a message is a duplicate.

        Args:
            message: The message to check for duplication

        Returns:
            True if message is a duplicate, False otherwise
        """
        # Create a hash of the message content (excluding volatile fields)
        fingerprint = self._create_fingerprint(message)
        key = f"duplicate_check:{fingerprint}"

        # Check if fingerprint exists in Redis
        if self.redis.exists(key):
            return True

        # Store fingerprint with TTL to prevent future duplicates
        self.redis.setex(key, self.window_seconds, "1")
        return False

    def _create_fingerprint(self, message: Dict[str, Any]) -> str:
        """Create a unique fingerprint for the message."""
        # Exclude fields that vary but shouldn't affect duplication logic
        content_to_hash = {
            k: v for k, v in message.items()
            if k not in ['timestamp', 'processed_at', 'correlation_id', 'sequence_number']
        }

        # For nested payload, include only stable parts
        if 'payload' in content_to_hash:
            payload = content_to_hash['payload']
            if isinstance(payload, dict):
                content_to_hash['payload'] = {
                    k: v for k, v in payload.items()
                    if k not in ['timestamp', 'received_at']
                }

        # Create SHA-256 hash of the normalized message
        message_str = json.dumps(content_to_hash, sort_keys=True, default=str)
        return hashlib.sha256(message_str.encode()).hexdigest()
```

### Database-Based Duplicate Detection

```python
import sqlite3
import hashlib
from typing import Optional

class DatabaseDuplicateDetector:
    """
    Database-based duplicate detector for persistent storage.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS message_fingerprints (
                    fingerprint TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            ''')

            # Create index for faster lookups
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON message_fingerprints(expires_at)
            ''')

    def is_duplicate(self, message: Dict[str, Any], ttl_hours: int = 24) -> bool:
        """
        Check if a message is a duplicate using database storage.

        Args:
            message: The message to check
            ttl_hours: Time-to-live for the fingerprint in hours

        Returns:
            True if duplicate, False otherwise
        """
        fingerprint = self._create_fingerprint(message)
        expires_at = f"Datetime('now', '+{ttl_hours} hours')"

        with sqlite3.connect(self.db_path) as conn:
            try:
                # Try to insert the fingerprint
                conn.execute('''
                    INSERT INTO message_fingerprints (fingerprint, expires_at)
                    VALUES (?, Datetime('now', ?))
                ''', (fingerprint, f'+{ttl_hours} hours'))

                conn.commit()
                return False  # Not a duplicate, successfully inserted

            except sqlite3.IntegrityError:
                # Fingerprint already exists - it's a duplicate
                return True

    def _create_fingerprint(self, message: Dict[str, Any]) -> str:
        """Create a unique fingerprint for the message."""
        # Create a hash of the message content (excluding volatile fields)
        content_to_hash = {
            k: v for k, v in message.items()
            if k not in ['timestamp', 'processed_at', 'correlation_id', 'sequence_number']
        }

        message_str = json.dumps(content_to_hash, sort_keys=True, default=str)
        return hashlib.sha256(message_str.encode()).hexdigest()

    def cleanup_expired_fingerprints(self):
        """Remove expired fingerprints from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                DELETE FROM message_fingerprints
                WHERE expires_at < Datetime('now')
            ''')

            deleted_count = cursor.rowcount
            conn.commit()

            print(f"Cleaned up {deleted_count} expired fingerprints")
            return deleted_count
```

## Circuit Breaker Pattern

```python
import time
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Tripped, not allowing requests
    HALF_OPEN = "half_open"  # Testing if failure condition is resolved

class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures in message processing.
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60,
                 success_threshold: int = 3):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time in seconds to wait before testing half-open state
            success_threshold: Number of successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call a function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Result of function call

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.timeout:
                # Timeout elapsed, try to close circuit
                self.state = CircuitState.HALF_OPEN
                print("Circuit breaker transitioning to HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN - not allowing requests")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._close_circuit()
        else:
            # Reset counters in normal operation
            self.failure_count = 0
            self.success_count = 0
            if self.state != CircuitState.CLOSED:
                self._close_circuit()

    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0  # Reset success count on failure

        if self.failure_count >= self.failure_threshold and self.state != CircuitState.OPEN:
            self._open_circuit()

    def _open_circuit(self):
        """Open the circuit."""
        self.state = CircuitState.OPEN
        print(f"Circuit breaker OPENED after {self.failure_count} failures")

    def _close_circuit(self):
        """Close the circuit."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        print("Circuit breaker CLOSED")
```

## Comprehensive Reliability Handler

```python
class ReliableMessageProcessor:
    """
    Comprehensive message processor that combines all reliability patterns.
    """

    def __init__(self, consumer: KafkaConsumer, producer: KafkaProducer,
                 dlq_handler: DeadLetterQueueHandler,
                 duplicate_detector: DuplicateDetector,
                 message_validator: MessageValidator,
                 circuit_breaker: CircuitBreaker):
        self.consumer = consumer
        self.producer = producer
        self.dlq_handler = dlq_handler
        self.duplicate_detector = duplicate_detector
        self.message_validator = message_validator
        self.circuit_breaker = circuit_breaker
        self.logger = logging.getLogger(__name__)

        # Statistics
        self.processed_count = 0
        self.failed_count = 0
        self.duplicate_count = 0

    def process_messages(self, business_logic_handler: Callable[[Dict[str, Any]], bool]):
        """
        Process messages with all reliability patterns applied.

        Args:
            business_logic_handler: Function that implements business logic
        """
        for message in self.consumer:
            try:
                # Apply circuit breaker
                result = self.circuit_breaker.call(
                    self._process_single_message,
                    message, business_logic_handler
                )

                if result:
                    # Commit offset after successful processing
                    self.consumer.commit()
                    self.processed_count += 1
                else:
                    self.failed_count += 1
                    self.logger.warning(
                        f"Business logic failed for message {message.topic}[{message.partition}] "
                        f"at {message.offset}"
                    )

            except Exception as e:
                self.failed_count += 1
                self.logger.error(
                    f"Circuit breaker or processing error for message "
                    f"{message.topic}[{message.partition}] at {message.offset}: {e}"
                )

                # Send to DLQ
                self.dlq_handler.send_to_dlq(
                    message.value, e, message.topic, message.partition, message.offset
                )

    def _process_single_message(self, message, business_logic_handler: Callable) -> bool:
        """
        Process a single message with all reliability checks.

        Args:
            message: The Kafka message to process
            business_logic_handler: Business logic function

        Returns:
            True if processed successfully, False otherwise
        """
        # 1. Validate message structure
        is_valid, validation_error = self.message_validator.validate_message(message.value)
        if not is_valid:
            self.logger.error(f"Message validation failed: {validation_error}")
            return False

        # 2. Check for duplicates
        if self.duplicate_detector.is_duplicate(message.value):
            self.logger.warning(f"Duplicate message detected: {message.value.get('correlation_id')}")
            self.duplicate_count += 1
            return True  # Acknowledge duplicate but don't process

        # 3. Apply business logic
        try:
            success = business_logic_handler(message.value)
            return success
        except Exception as e:
            self.logger.error(f"Business logic error: {e}")
            return False

    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        return {
            'processed': self.processed_count,
            'failed': self.failed_count,
            'duplicates': self.duplicate_count,
            'success_rate': (
                self.processed_count / (self.processed_count + self.failed_count)
                if (self.processed_count + self.failed_count) > 0 else 0
            )
        }
```

This comprehensive reliability guide provides all the patterns needed to ensure message reliability in the Kafka-based event streaming system.