---
name: event_streaming
description: Implements Kafka-based event streaming to decouple channel intake from agent processing. Manages producers, consumers, and message reliability across the processing pipeline. Use when Claude needs to implement Kafka-based event streaming, set up producers/consumers, manage message reliability, or decouple system components using event streaming.
---

# Event Streaming Skill

This skill provides guidance for implementing Kafka-based event streaming to decouple channel intake from agent processing. It covers producer/consumer patterns, message reliability, and stream processing across the system pipeline.

## Overview

The event streaming system uses Apache Kafka to decouple various components of the CRM system, particularly to separate channel intake (email, WhatsApp, web forms) from agent processing. This architecture provides scalability, reliability, and fault tolerance.

## Core Concepts

### 1. Event Streaming Architecture
- **Producers**: Channel intake services publish messages to Kafka topics
- **Topics**: Logical channels for organizing different types of events
- **Consumers**: Agent processing services consume messages from topics
- **Brokers**: Kafka cluster managing message persistence and delivery
- **Partitions**: Horizontal scaling units within topics

### 2. Key Benefits
- **Decoupling**: Channel intake and agent processing can scale independently
- **Reliability**: Messages persist even if consumers are down
- **Scalability**: Multiple consumers can process messages in parallel
- **Fault Tolerance**: Redundant brokers ensure high availability

## Kafka Topics Design

### Topic Categories

#### Ingestion Topics
- `ingestion.raw.messages` - Raw messages from all channels before processing
- `ingestion.normalized.messages` - Normalized messages after channel-specific processing
- `ingestion.validation.results` - Results of message validation

#### Processing Topics
- `processing.customer.identities` - Customer identity resolution events
- `processing.tickets.in` - Incoming ticket creation requests
- `processing.tickets.out` - Ticket status update events
- `processing.responses.out` - Response messages to be sent back to customers

#### Notification Topics
- `notifications.alerts` - System alerts and notifications
- `notifications.audit` - Audit trail for compliance
- `notifications.metrics` - System metrics and monitoring data

### Topic Configuration
```bash
# Example topic creation with optimal settings
kafka-topics --create \
  --topic ingestion.raw.messages \
  --partitions 6 \
  --replication-factor 3 \
  --config retention.ms=604800000 \  # 7 days
  --config cleanup.policy=delete \
  --bootstrap-server localhost:9092
```

## Producer Implementation

### Python Producer Example
```python
from kafka import KafkaProducer
import json
import logging
from typing import Dict, Any

class MessageProducer:
    def __init__(self, bootstrap_servers: str, retries: int = 3):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            retries=retries,
            acks='all',  # Strongest consistency guarantee
            linger_ms=5,  # Small delay to batch messages
            batch_size=16384  # Batch size in bytes
        )
        self.logger = logging.getLogger(__name__)

    def send_message(self, topic: str, message: Dict[str, Any], key: str = None):
        """
        Send a message to a Kafka topic with error handling.
        """
        try:
            future = self.producer.send(topic, value=message, key=key)
            # Block until message is acknowledged
            record_metadata = future.get(timeout=10)

            self.logger.info(f'Message sent to {topic}[{record_metadata.partition}] '
                           f'at offset {record_metadata.offset}')
            return record_metadata
        except Exception as e:
            self.logger.error(f'Error sending message to {topic}: {e}')
            raise

    def flush(self):
        """Flush all pending messages."""
        self.producer.flush()

    def close(self):
        """Close the producer and clean up resources."""
        self.producer.close()
```

### Message Enrichment Pattern
```python
def enrich_message(raw_message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich raw message with additional metadata before publishing.
    """
    enriched_message = {
        'original_message': raw_message,
        'enriched_at': datetime.utcnow().isoformat(),
        'source_system': 'channel_intake',
        'processing_stage': 'raw_to_enriched',
        'correlation_id': str(uuid.uuid4()),
        'partition_key': raw_message.get('customer_id') or raw_message.get('email')
    }
    return enriched_message
```

## Consumer Implementation

### Python Consumer Example
```python
from kafka import KafkaConsumer
import json
import logging
from typing import Dict, Any, Callable

class MessageConsumer:
    def __init__(self, bootstrap_servers: str, group_id: str, auto_offset_reset: str = 'latest'):
        self.consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset=auto_offset_reset,  # 'earliest' or 'latest'
            enable_auto_commit=False,  # Manual offset management for reliability
            max_poll_records=100,  # Batch processing
            max_poll_interval_ms=300000  # 5 minutes for long-running processing
        )
        self.logger = logging.getLogger(__name__)

    def subscribe_to_topics(self, topics: list):
        """Subscribe to one or more topics."""
        self.consumer.subscribe(topics=topics)

    def process_messages(self, message_handler: Callable[[str, Dict[str, Any]], bool]):
        """
        Process messages using the provided handler.
        Returns True if message was processed successfully, False otherwise.
        """
        try:
            for message in self.consumer:
                try:
                    success = message_handler(message.topic, message.value)

                    if success:
                        # Commit offset only after successful processing
                        self.consumer.commit()
                        self.logger.debug(f'Processed message from {message.topic} '
                                        f'partition {message.partition} offset {message.offset}')
                    else:
                        self.logger.warning(f'Failed to process message from {message.topic} '
                                          f'partition {message.partition} offset {message.offset}')

                except Exception as e:
                    self.logger.error(f'Error processing message: {e}')
                    # Decide whether to continue or stop based on error type
                    continue

        except KeyboardInterrupt:
            self.logger.info('Consumer interrupted')
        finally:
            self.consumer.close()
```

### Consumer Group Management
```python
def handle_rebalance(consumer, partitions):
    """Handle partition rebalancing events."""
    logging.info(f"Partition assignment: {partitions}")

def create_consumer_with_rebalance_handling(bootstrap_servers: str, group_id: str):
    consumer = KafkaConsumer(
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest',
        enable_auto_commit=False
    )

    # Register rebalance listener
    consumer.subscribe(topics=['ingestion.normalized.messages'], listener=ConsumerRebalanceListener())

    return consumer
```

## Message Reliability Patterns

### 1. At-Least-Once Delivery
```python
def process_with_acknowledgment(consumer: KafkaConsumer, processor_func: Callable):
    """
    Process messages with manual acknowledgment for at-least-once semantics.
    """
    for message in consumer:
        try:
            # Process the message
            result = processor_func(message.value)

            if result.success:
                # Only commit offset after successful processing
                consumer.commit()
            else:
                # Log failure but continue processing other messages
                logging.error(f"Processing failed for message {message.offset}")

        except Exception as e:
            logging.error(f"Error processing message {message.offset}: {e}")
            # Don't commit offset on error to ensure redelivery
```

### 2. Dead Letter Queue Pattern
```python
class DeadLetterQueueHandler:
    def __init__(self, dlq_topic: str, producer: MessageProducer):
        self.dlq_topic = dlq_topic
        self.producer = producer
        self.max_retry_attempts = 3

    def send_to_dlq(self, original_message: Dict[str, Any], error: Exception, retry_count: int = 0):
        """
        Send failed messages to dead letter queue.
        """
        dlq_message = {
            'original_message': original_message,
            'error': str(error),
            'retry_count': retry_count + 1,
            'failed_at': datetime.utcnow().isoformat(),
            'max_retries_exceeded': retry_count >= self.max_retry_attempts
        }

        self.producer.send_message(self.dlq_topic, dlq_message)
```

### 3. Duplicate Message Handling
```python
import hashlib

class DuplicateMessageDetector:
    def __init__(self, redis_client, window_minutes: int = 1440):  # 24 hours
        self.redis = redis_client
        self.window = window_minutes * 60  # Convert to seconds

    def is_duplicate(self, message: Dict[str, Any]) -> bool:
        """
        Check if message is a duplicate based on content hash.
        """
        # Create a hash of message content (excluding timestamp fields)
        content_to_hash = {
            k: v for k, v in message.items()
            if k not in ['timestamp', 'processed_at', 'correlation_id']
        }

        message_hash = hashlib.sha256(
            json.dumps(content_to_hash, sort_keys=True).encode()
        ).hexdigest()

        # Check if hash exists in Redis
        if self.redis.exists(f"duplicate_check:{message_hash}"):
            return True

        # Store hash with expiration
        self.redis.setex(f"duplicate_check:{message_hash}", self.window, "1")
        return False
```

## Stream Processing with Kafka Streams

### Kafka Streams Example (Java-based concepts applicable to Python with ksqlDB)
```python
# Conceptual example - in practice, Kafka Streams is Java-based
# For Python, use ksqlDB or Faust streaming library

def create_stream_processing_topology(builder, serde_config):
    """
    Create a Kafka Streams processing topology.
    This would typically be implemented in Java, but conceptually:
    """
    # Read from input topic
    source_stream = builder.stream('ingestion.normalized.messages')

    # Transform messages
    processed_stream = source_stream.map(process_message)

    # Filter messages
    filtered_stream = processed_stream.filter(filter_valid_messages)

    # Write to output topic
    filtered_stream.to('processing.customer.identities')

    return builder.build()
```

## Error Handling and Monitoring

### Consumer Error Handling
```python
class ResilientConsumer:
    def __init__(self, consumer: MessageConsumer, dlq_handler: DeadLetterQueueHandler):
        self.consumer = consumer
        self.dlq_handler = dlq_handler
        self.processing_errors = 0
        self.max_errors_before_pause = 100

    def resilient_process(self, processor_func: Callable):
        """
        Process messages with resilience to transient errors.
        """
        error_streak = 0

        for message in self.consumer:
            try:
                success = processor_func(message.value)

                if success:
                    self.consumer.commit()
                    error_streak = 0  # Reset error streak
                else:
                    error_streak += 1
                    self.handle_processing_failure(message, "Processor returned failure")

            except Exception as e:
                error_streak += 1
                self.handle_processing_failure(message, e)

                # Pause briefly after repeated errors
                if error_streak >= 5:
                    time.sleep(min(error_streak, 30))  # Max 30 second pause

    def handle_processing_failure(self, message, error):
        """
        Handle message processing failures with exponential backoff.
        """
        self.processing_errors += 1

        if self.processing_errors > self.max_errors_before_pause:
            # Send to DLQ and pause consumer
            self.dlq_handler.send_to_dlq(message.value, error)
        else:
            # Log and continue
            logging.error(f"Processing error: {error}")
```

### Monitoring and Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics for Kafka consumers
MESSAGES_PROCESSED = Counter('kafka_messages_processed_total', 'Total messages processed', ['topic', 'consumer_group'])
PROCESSING_LATENCY = Histogram('kafka_message_processing_duration_seconds', 'Message processing time')
CONSUMER_OFFSET = Gauge('kafka_consumer_offset', 'Current consumer offset', ['topic', 'partition', 'consumer_group'])

def instrumented_message_handler(topic: str, value: Dict[str, Any]) -> bool:
    """
    Message handler with Prometheus metrics instrumentation.
    """
    start_time = time.time()

    try:
        # Process message
        success = process_message(value)

        # Record metrics
        MESSAGES_PROCESSED.labels(topic=topic, consumer_group='agent_processor').inc()
        PROCESSING_LATENCY.observe(time.time() - start_time)

        return success
    except Exception as e:
        # Record error metrics
        PROCESSING_LATENCY.observe(time.time() - start_time)
        raise
```

## Best Practices

### 1. Topic Design
- Use descriptive topic names that indicate the event type
- Design partition keys to ensure even distribution
- Set appropriate retention policies based on business needs

### 2. Producer Best Practices
- Use synchronous sends for critical messages
- Implement proper error handling and retry logic
- Batch messages appropriately for throughput

### 3. Consumer Best Practices
- Use consumer groups for parallel processing
- Implement manual offset management for reliability
- Monitor consumer lag regularly

### 4. Security Considerations
- Enable SSL/TLS encryption for data in transit
- Use SASL authentication for broker access
- Implement ACLs for topic access control

## Reference Materials

For detailed implementation patterns, see:
- [PRODUCER_PATTERNS.md](references/PRODUCER_PATTERNS.md) - Producer implementation patterns
- [CONSUMER_PATTERNS.md](references/CONSUMER_PATTERNS.md) - Consumer implementation patterns
- [RELIABILITY_PATTERNS.md](references/RELIABILITY_PATTERNS.md) - Message reliability patterns
- [MONITORING_GUIDE.md](references/MONITORING_GUIDE.md) - Monitoring and observability
- [SCALING_STRATEGIES.md](references/SCALING_STRATEGIES.md) - Scaling strategies
- [SECURITY_BEST_PRACTICES.md](references/SECURITY_BEST_PRACTICES.md) - Security implementation
- [FAULT_TOLERANCE.md](references/FAULT_TOLERANCE.md) - Fault tolerance patterns