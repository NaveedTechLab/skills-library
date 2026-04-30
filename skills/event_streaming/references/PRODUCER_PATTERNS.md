# Kafka Producer Implementation Patterns

## Overview

This document covers best practices and implementation patterns for Kafka producers in the CRM system. Producers are responsible for publishing messages from channel intake services to Kafka topics.

## Producer Configuration

### Essential Producer Properties

```python
from kafka import KafkaProducer
import json
from typing import Dict, Any

class KafkaProducerConfig:
    """Configuration class for Kafka producers with optimal settings for CRM system."""

    def __init__(self, bootstrap_servers: str, client_id: str = None):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id or "crm-producer"

    def create_producer(self) -> KafkaProducer:
        """Create a Kafka producer with production-ready settings."""
        return KafkaProducer(
            # Basic connection settings
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id,

            # Serialization
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,

            # Reliability settings
            acks='all',  # Leader waits for all in-sync replicas to acknowledge
            retries=2147483647,  # Effectively infinite retries
            max_in_flight_requests_per_connection=5,  # Prevent message reordering

            # Performance settings
            linger_ms=5,  # Small delay to batch messages together
            batch_size=16384,  # Batch size in bytes (16KB)
            compression_type='snappy',  # Compress messages to save bandwidth

            # Buffer settings
            buffer_memory=33554432,  # 32MB total buffer memory
            max_block_ms=60000,  # Wait up to 60 seconds for metadata/buffer space
        )
```

### Environment-Specific Configurations

```python
import os
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"

def get_producer_config(environment: Environment) -> dict:
    """Get environment-specific producer configurations."""
    base_config = {
        'value_serializer': lambda v: json.dumps(v, default=str).encode('utf-8'),
        'key_serializer': lambda k: k.encode('utf-8') if k else None,
    }

    if environment == Environment.PRODUCTION:
        return {
            **base_config,
            'acks': 'all',
            'retries': 2147483647,
            'linger_ms': 5,
            'compression_type': 'snappy',
            'request_timeout_ms': 30000,
            'delivery_timeout_ms': 120000,
        }
    elif environment == Environment.STAGING:
        return {
            **base_config,
            'acks': '1',
            'retries': 5,
            'linger_ms': 10,
            'compression_type': 'gzip',
        }
    else:  # Development
        return {
            **base_config,
            'acks': '1',
            'retries': 1,
            'linger_ms': 1,
        }
```

## Message Production Patterns

### Basic Message Production

```python
import uuid
from datetime import datetime
from typing import Optional

class MessageProducer:
    def __init__(self, producer_config: KafkaProducerConfig):
        self.producer = producer_config.create_producer()
        self.config = producer_config

    def send_message(self, topic: str, message: Dict[str, Any],
                     key: Optional[str] = None,
                     headers: Optional[Dict[str, str]] = None) -> bool:
        """
        Send a message to a Kafka topic with error handling.

        Args:
            topic: Target topic name
            message: Message payload as dictionary
            key: Message key for partitioning
            headers: Additional headers for the message

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add metadata to message
            enriched_message = self._enrich_message(message)

            # Send message
            future = self.producer.send(
                topic=topic,
                value=enriched_message,
                key=key,
                headers=headers or {}
            )

            # Wait for acknowledgment (synchronous send)
            record_metadata = future.get(timeout=10)

            print(f'Message delivered to {topic}[{record_metadata.partition}] '
                  f'at offset {record_metadata.offset}')
            return True

        except Exception as e:
            print(f'Error sending message to {topic}: {str(e)}')
            return False

    def _enrich_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Add standard metadata to messages."""
        enriched = message.copy()
        enriched.update({
            'produced_at': datetime.utcnow().isoformat(),
            'producer_id': self.config.client_id,
            'correlation_id': str(uuid.uuid4()),
            'message_version': '1.0'
        })
        return enriched

    def flush(self):
        """Flush all pending messages."""
        self.producer.flush()

    def close(self):
        """Close the producer and clean up resources."""
        self.producer.close()
```

### Batch Message Production

```python
from typing import List, Tuple
import time

class BatchMessageProducer(MessageProducer):
    def send_batch(self, topic: str, messages: List[Dict[str, Any]],
                   keys: List[Optional[str]] = None) -> List[bool]:
        """
        Send a batch of messages to a Kafka topic.

        Args:
            topic: Target topic name
            messages: List of message payloads
            keys: Optional list of keys for each message

        Returns:
            List of boolean results indicating success/failure for each message
        """
        results = []

        for i, message in enumerate(messages):
            key = keys[i] if keys and i < len(keys) else None
            success = self.send_message(topic, message, key)
            results.append(success)

            # Small delay to avoid overwhelming the broker
            if i < len(messages) - 1:
                time.sleep(0.01)

        return results

    def send_batch_async(self, topic: str, messages: List[Dict[str, Any]]) -> List:
        """
        Send messages asynchronously and return futures.
        """
        futures = []

        for message in messages:
            enriched_message = self._enrich_message(message)
            future = self.producer.send(topic, value=enriched_message)
            futures.append(future)

        return futures
```

## Advanced Producer Patterns

### Idempotent Producer

```python
class IdempotentMessageProducer:
    """Producer that guarantees exactly-once semantics."""

    def __init__(self, bootstrap_servers: str):
        # Enable idempotence for exactly-once semantics
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=2147483647,
            max_in_flight_requests_per_connection=5,
            enable_idempotence=True,  # Key setting for exactly-once semantics
        )

    def send_with_transaction(self, topic: str, message: Dict[str, Any],
                             transactional_id: str) -> bool:
        """
        Send message within a transaction for atomic operations.
        """
        try:
            # Initialize transaction
            self.producer.init_transactions()

            # Begin transaction
            self.producer.begin_transaction()

            # Send message
            future = self.producer.send(topic, value=message)
            record_metadata = future.get(timeout=10)

            # Commit transaction
            self.producer.commit_transaction()

            print(f'Transactional message sent to {topic}[{record_metadata.partition}]')
            return True

        except Exception as e:
            # Abort transaction on error
            self.producer.abort_transaction()
            print(f'Transaction failed: {str(e)}')
            return False
```

### Retry and Backoff Logic

```python
import time
import random
from functools import wraps

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0,
                      max_delay: float = 60.0, jitter: bool = True):
    """Decorator for retrying producer operations with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        # Last attempt, raise the exception
                        raise e

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)

                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)

                    print(f"Attempt {attempt + 1} failed: {str(e)}. "
                          f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)

        return wrapper
    return decorator

class ReliableMessageProducer:
    def __init__(self, bootstrap_servers: str):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',
            retries=2147483647,
        )

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def send_reliable(self, topic: str, message: Dict[str, Any]) -> bool:
        """Send message with built-in retry logic."""
        future = self.producer.send(topic, value=message)
        record_metadata = future.get(timeout=30)

        print(f'Reliable message sent to {topic}[{record_metadata.partition}] '
              f'at offset {record_metadata.offset}')
        return True
```

## Channel-Specific Producer Implementations

### Email Channel Producer

```python
class EmailChannelProducer:
    def __init__(self, producer: MessageProducer):
        self.producer = producer

    def send_email_message(self, email_data: Dict[str, Any]) -> bool:
        """
        Send an email message to the ingestion pipeline.

        Args:
            email_data: Dictionary containing email information
                - from_email: Sender's email address
                - to_email: Recipient's email address
                - subject: Email subject
                - body: Email body content
                - timestamp: When email was received

        Returns:
            True if successfully sent, False otherwise
        """
        message = {
            'channel': 'email',
            'message_type': 'email_received',
            'payload': {
                'from_email': email_data['from_email'],
                'to_email': email_data['to_email'],
                'subject': email_data['subject'],
                'body': email_data['body'],
                'timestamp': email_data['timestamp'],
                'attachments': email_data.get('attachments', [])
            }
        }

        # Use email as partition key for consistent routing
        key = email_data['from_email']

        return self.producer.send_message(
            topic='ingestion.raw.messages',
            message=message,
            key=key
        )
```

### WhatsApp Channel Producer

```python
class WhatsAppChannelProducer:
    def __init__(self, producer: MessageProducer):
        self.producer = producer

    def send_whatsapp_message(self, whatsapp_data: Dict[str, Any]) -> bool:
        """
        Send a WhatsApp message to the ingestion pipeline.

        Args:
            whatsapp_data: Dictionary containing WhatsApp message information
                - sender_id: WhatsApp ID of sender
                - recipient_id: WhatsApp ID of recipient
                - message_text: Text content of the message
                - timestamp: When message was received
                - media_url: URL to media attachment (optional)

        Returns:
            True if successfully sent, False otherwise
        """
        message = {
            'channel': 'whatsapp',
            'message_type': 'whatsapp_received',
            'payload': {
                'sender_id': whatsapp_data['sender_id'],
                'recipient_id': whatsapp_data['recipient_id'],
                'message_text': whatsapp_data['message_text'],
                'timestamp': whatsapp_data['timestamp'],
                'media_url': whatsapp_data.get('media_url'),
                'message_id': whatsapp_data.get('message_id')
            }
        }

        # Use sender ID as partition key
        key = whatsapp_data['sender_id']

        return self.producer.send_message(
            topic='ingestion.raw.messages',
            message=message,
            key=key
        )
```

### Web Form Producer

```python
class WebFormProducer:
    def __init__(self, producer: MessageProducer):
        self.producer = producer

    def send_web_form_submission(self, form_data: Dict[str, Any]) -> bool:
        """
        Send a web form submission to the ingestion pipeline.

        Args:
            form_data: Dictionary containing form submission information
                - form_type: Type of form (contact, support, etc.)
                - submitted_data: Dictionary of form fields and values
                - submitter_email: Email of the person submitting
                - timestamp: When form was submitted

        Returns:
            True if successfully sent, False otherwise
        """
        message = {
            'channel': 'web_form',
            'message_type': 'form_submitted',
            'payload': {
                'form_type': form_data['form_type'],
                'submitted_data': form_data['submitted_data'],
                'submitter_email': form_data.get('submitter_email'),
                'timestamp': form_data['timestamp']
            }
        }

        # Use email as partition key if available
        key = form_data.get('submitter_email')

        return self.producer.send_message(
            topic='ingestion.raw.messages',
            message=message,
            key=key
        )
```

## Monitoring and Metrics

### Producer Metrics Collection

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Producer metrics
MESSAGES_SENT = Counter('kafka_producer_messages_sent_total',
                       'Total messages sent by producer',
                       ['topic', 'client_id'])
SEND_LATENCY = Histogram('kafka_producer_send_duration_seconds',
                        'Time taken to send messages')
CURRENT_QUEUE_SIZE = Gauge('kafka_producer_queue_size',
                          'Current number of messages in producer queue')

class InstrumentedMessageProducer:
    def __init__(self, bootstrap_servers: str, client_id: str):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            client_id=client_id,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
        )
        self.client_id = client_id

    def send_with_metrics(self, topic: str, message: Dict[str, Any]) -> bool:
        """Send message with Prometheus metrics collection."""
        start_time = time.time()

        try:
            future = self.producer.send(topic, value=message)
            record_metadata = future.get(timeout=10)

            # Record metrics
            MESSAGES_SENT.labels(topic=topic, client_id=self.client_id).inc()
            SEND_LATENCY.observe(time.time() - start_time)

            print(f'Message sent to {topic}[{record_metadata.partition}] '
                  f'at offset {record_metadata.offset}')
            return True

        except Exception as e:
            SEND_LATENCY.observe(time.time() - start_time)
            print(f'Error sending message to {topic}: {str(e)}')
            return False
```

## Error Handling and Recovery

### Dead Letter Queue Integration

```python
class ProducerWithDLQ:
    def __init__(self, main_producer: MessageProducer,
                 dlq_producer: MessageProducer,
                 max_retries: int = 3):
        self.main_producer = main_producer
        self.dlq_producer = dlq_producer
        self.max_retries = max_retries

    def send_with_dlq_fallback(self, topic: str, message: Dict[str, Any],
                              key: Optional[str] = None) -> bool:
        """
        Send message with fallback to dead letter queue on repeated failures.
        """
        for attempt in range(self.max_retries + 1):
            try:
                success = self.main_producer.send_message(topic, message, key)
                if success:
                    return True
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")

                if attempt == self.max_retries:
                    # Send to DLQ after max retries
                    dlq_message = {
                        'original_message': message,
                        'error': str(e),
                        'failed_topic': topic,
                        'retry_count': attempt,
                        'failed_at': datetime.utcnow().isoformat()
                    }

                    dlq_success = self.dlq_producer.send_message(
                        'ingestion.dlq.messages',
                        dlq_message,
                        key=key
                    )

                    print(f"Message sent to DLQ: {dlq_success}")
                    return dlq_success

        return False
```

This comprehensive producer implementation guide provides all the patterns and best practices needed for reliable message production in the CRM system.