# Kafka Consumer Implementation Patterns

## Overview

This document covers best practices and implementation patterns for Kafka consumers in the CRM system. Consumers are responsible for processing messages from Kafka topics and performing actions such as customer identity resolution, ticket creation, and response generation.

## Consumer Configuration

### Essential Consumer Properties

```python
from kafka import KafkaConsumer
import json
from typing import Dict, Any, Callable, List

class KafkaConsumerConfig:
    """Configuration class for Kafka consumers with optimal settings for CRM system."""

    def __init__(self, bootstrap_servers: str, group_id: str, client_id: str = None):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.client_id = client_id or "crm-consumer"

    def create_consumer(self) -> KafkaConsumer:
        """Create a Kafka consumer with production-ready settings."""
        return KafkaConsumer(
            # Basic connection settings
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            client_id=self.client_id,

            # Deserialization
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,

            # Offset management
            auto_offset_reset='latest',  # Start from latest if no committed offset
            enable_auto_commit=False,    # Manual offset management for reliability

            # Performance settings
            max_poll_records=100,        # Number of records per poll
            max_poll_interval_ms=300000, # 5 minutes for long-running processing
            fetch_max_wait_ms=500,       # Max time server waits for min bytes
            fetch_min_bytes=1,           # Minimum bytes to return from fetch
            max_partition_fetch_bytes=1048576,  # 1MB per partition

            # Session timeout settings
            session_timeout_ms=30000,    # Group membership timeout
            heartbeat_interval_ms=3000,  # Heartbeat frequency
        )
```

### Consumer Group Management

```python
from kafka import KafkaConsumer
from kafka.structs import TopicPartition
from typing import Optional

class ConsumerGroupManager:
    def __init__(self, bootstrap_servers: str, group_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id

    def create_consumer_with_assignment(self, topics: List[str]) -> KafkaConsumer:
        """Create consumer with specific topic partition assignment."""
        consumer = KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            enable_auto_commit=False,
            session_timeout_ms=30000,
            heartbeat_interval_ms=3000
        )

        # Subscribe to topics
        consumer.subscribe(topics=topics)

        # Wait for assignment
        consumer.poll(timeout_ms=1000, max_records=1)

        return consumer

    def get_current_assignment(self, consumer: KafkaConsumer) -> List[TopicPartition]:
        """Get current partition assignments for the consumer."""
        return consumer.assignment()

    def pause_partitions(self, consumer: KafkaConsumer, partitions: List[TopicPartition]):
        """Pause consumption from specific partitions."""
        consumer.pause(*partitions)

    def resume_partitions(self, consumer: KafkaConsumer, partitions: List[TopicPartition]):
        """Resume consumption from specific partitions."""
        consumer.resume(*partitions)
```

## Basic Consumer Patterns

### Simple Consumer Loop

```python
import logging
from typing import Optional

class SimpleConsumer:
    def __init__(self, consumer: KafkaConsumer, logger: logging.Logger):
        self.consumer = consumer
        self.logger = logger

    def consume_messages(self, message_handler: Callable[[str, Dict[str, Any]], bool]):
        """
        Consume messages and process them using the provided handler.

        Args:
            message_handler: Function that takes (topic, message) and returns success status

        Returns:
            True if successful, raises exception on critical error
        """
        try:
            self.logger.info("Starting message consumption loop")

            for message in self.consumer:
                try:
                    # Process the message
                    success = message_handler(message.topic, message.value)

                    if success:
                        # Commit offset only after successful processing
                        self.consumer.commit()
                        self.logger.debug(
                            f'Successfully processed message from {message.topic} '
                            f'[partition {message.partition}] at offset {message.offset}'
                        )
                    else:
                        self.logger.warning(
                            f'Failed to process message from {message.topic} '
                            f'[partition {message.partition}] at offset {message.offset}'
                        )

                except Exception as e:
                    self.logger.error(
                        f'Error processing message from {message.topic} '
                        f'[partition {message.partition}] at offset {message.offset}: {e}'
                    )
                    # Continue processing other messages

        except KeyboardInterrupt:
            self.logger.info("Consumer interrupted by user")
        except Exception as e:
            self.logger.error(f"Critical error in consumer: {e}")
            raise
        finally:
            self.consumer.close()
            self.logger.info("Consumer closed")
```

### Batch Consumer Pattern

```python
import time
from typing import List, Tuple

class BatchConsumer:
    def __init__(self, consumer: KafkaConsumer, logger: logging.Logger,
                 batch_size: int = 100, batch_timeout: int = 5000):
        self.consumer = consumer
        self.logger = logger
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout  # in milliseconds

    def consume_batch(self, batch_handler: Callable[[List[Tuple[str, Dict[str, Any]]]], bool]):
        """
        Consume messages in batches and process them together.

        Args:
            batch_handler: Function that takes a list of (topic, message) tuples
                          and returns success status for the entire batch
        """
        batch = []

        try:
            while True:
                # Poll for messages with timeout
                messages = self.consumer.poll(
                    timeout_ms=self.batch_timeout,
                    max_records=self.batch_size
                )

                # Process messages from each topic
                for topic_partition, records in messages.items():
                    for record in records:
                        batch.append((record.topic, record.value))

                        # Process batch when it reaches the desired size
                        if len(batch) >= self.batch_size:
                            self._process_batch(batch, batch_handler)

                # Process remaining messages in batch if timeout occurred
                if batch:
                    # Check if we've waited long enough without new messages
                    # (implementation would track time since last message)
                    if len(batch) >= self.batch_size or self._should_flush_batch():
                        self._process_batch(batch, batch_handler)

        except KeyboardInterrupt:
            self.logger.info("Batch consumer interrupted")
        finally:
            # Process any remaining messages in the batch
            if batch:
                self._process_batch(batch, batch_handler)
            self.consumer.close()

    def _process_batch(self, batch: List[Tuple[str, Dict[str, Any]]],
                      batch_handler: Callable) -> bool:
        """Process a batch of messages."""
        try:
            success = batch_handler(batch)

            if success:
                # Commit offsets for all messages in the batch
                self.consumer.commit()
                self.logger.info(f"Successfully processed batch of {len(batch)} messages")
            else:
                self.logger.warning(f"Failed to process batch of {len(batch)} messages")

            # Clear the batch
            batch.clear()
            return success

        except Exception as e:
            self.logger.error(f"Error processing batch: {e}")
            # Don't clear batch on error - messages will be reprocessed
            return False

    def _should_flush_batch(self) -> bool:
        """Determine if batch should be flushed based on time or other criteria."""
        # Implementation would track time since first message in batch
        return True  # Simplified for example
```

## Advanced Consumer Patterns

### Resilient Consumer with Circuit Breaker

```python
import time
from enum import Enum
from typing import Optional

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Tripped, not allowing requests
    HALF_OPEN = "half_open"  # Testing if failure condition is resolved

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def on_success(self):
        """Called when operation succeeds."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def on_failure(self):
        """Called when operation fails."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

class ResilientConsumer:
    def __init__(self, consumer: KafkaConsumer, logger: logging.Logger):
        self.consumer = consumer
        self.logger = logger
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        self.error_count = 0
        self.max_errors_before_pause = 100

    def resilient_consume(self, message_handler: Callable[[str, Dict[str, Any]], bool]):
        """
        Consume messages with resilience to failures and circuit breaker protection.
        """
        consecutive_errors = 0

        try:
            for message in self.consumer:
                try:
                    # Wrap message processing in circuit breaker
                    success = self.circuit_breaker.call(message_handler, message.topic, message.value)

                    if success:
                        self.consumer.commit()
                        consecutive_errors = 0  # Reset error counter
                    else:
                        consecutive_errors += 1
                        self.logger.warning(
                            f'Processing failed for message from {message.topic} '
                            f'at offset {message.offset}'
                        )

                except Exception as e:
                    consecutive_errors += 1
                    self.error_count += 1

                    self.logger.error(
                        f'Circuit breaker triggered or processing error: {e} '
                        f'for message from {message.topic} at offset {message.offset}'
                    )

                    # Pause briefly after repeated errors to avoid overwhelming system
                    if consecutive_errors >= 10:
                        pause_time = min(30, consecutive_errors // 10)  # Max 30 second pause
                        self.logger.info(f"Pausing consumer for {pause_time} seconds due to errors")
                        time.sleep(pause_time)

                    # Stop if too many errors
                    if self.error_count > self.max_errors_before_pause:
                        self.logger.error("Too many errors, stopping consumer")
                        break

        except KeyboardInterrupt:
            self.logger.info("Resilient consumer interrupted")
        finally:
            self.consumer.close()
```

### Consumer with Backpressure Control

```python
import threading
from queue import Queue, Full, Empty
from typing import Dict, Any

class BackpressureControlledConsumer:
    def __init__(self, consumer: KafkaConsumer, logger: logging.Logger,
                 max_queue_size: int = 1000):
        self.consumer = consumer
        self.logger = logger
        self.max_queue_size = max_queue_size
        self.message_queue = Queue(maxsize=max_queue_size)
        self.processing_active = threading.Event()
        self.processing_active.set()

    def start_consuming(self, processor_func: Callable[[Dict[str, Any]], bool]):
        """
        Start consuming messages with backpressure control.
        """
        # Start the consumption thread
        consume_thread = threading.Thread(target=self._consume_loop)
        consume_thread.daemon = True
        consume_thread.start()

        # Process messages from the queue
        try:
            while self.processing_active.is_set():
                try:
                    # Get message from queue with timeout
                    topic, message = self.message_queue.get(timeout=1.0)

                    try:
                        success = processor_func(message)

                        if success:
                            # Mark message as processed
                            self.message_queue.task_done()
                        else:
                            self.logger.warning(f"Processor failed for message: {message}")
                            # Optionally requeue or send to DLQ

                    except Exception as e:
                        self.logger.error(f"Error processing message: {e}")
                        self.message_queue.task_done()

                except Empty:
                    # Queue is empty, continue loop
                    continue

        except KeyboardInterrupt:
            self.logger.info("Backpressure controlled consumer interrupted")
        finally:
            self.stop_consuming()

    def _consume_loop(self):
        """Internal consumption loop that feeds messages to the queue."""
        try:
            for message in self.consumer:
                try:
                    # Put message in queue with timeout to respect backpressure
                    self.message_queue.put(
                        (message.topic, message.value),
                        timeout=1.0
                    )

                    # Commit offset after successfully queuing
                    self.consumer.commit()

                except Full:
                    # Queue is full, consumer is falling behind
                    self.logger.warning(
                        f"Message queue is full, dropping message from {message.topic} "
                        f"at offset {message.offset}"
                    )
                    # In production, you might want to send dropped messages to DLQ

        except Exception as e:
            self.logger.error(f"Error in consumption loop: {e}")
        finally:
            self.consumer.close()

    def stop_consuming(self):
        """Stop the consumer gracefully."""
        self.processing_active.clear()
```

## Message Processing Patterns

### Message Router

```python
from typing import Dict, Callable, Any
from functools import singledispatch

class MessageRouter:
    def __init__(self, logger: logging.Logger):
        self.handlers = {}
        self.logger = logger

    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type."""
        self.handlers[message_type] = handler
        self.logger.info(f"Registered handler for message type: {message_type}")

    def route_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """
        Route message to appropriate handler based on type.

        Args:
            topic: The topic the message came from
            message: The message payload

        Returns:
            True if processed successfully, False otherwise
        """
        # Determine message type
        message_type = message.get('message_type') or message.get('type')

        if not message_type:
            self.logger.error(f"No message type found in message: {message}")
            return False

        handler = self.handlers.get(message_type)

        if not handler:
            self.logger.warning(f"No handler registered for message type: {message_type}")
            return False

        try:
            result = handler(topic, message)
            return result
        except Exception as e:
            self.logger.error(f"Error in handler for {message_type}: {e}")
            return False

# Example usage
def setup_message_router() -> MessageRouter:
    router = MessageRouter(logging.getLogger(__name__))

    # Register handlers
    router.register_handler('email_received', process_email_message)
    router.register_handler('whatsapp_received', process_whatsapp_message)
    router.register_handler('form_submitted', process_form_message)

    return router

def process_email_message(topic: str, message: Dict[str, Any]) -> bool:
    """Process email received message."""
    # Implementation for email processing
    print(f"Processing email message: {message}")
    return True

def process_whatsapp_message(topic: str, message: Dict[str, Any]) -> bool:
    """Process WhatsApp received message."""
    # Implementation for WhatsApp processing
    print(f"Processing WhatsApp message: {message}")
    return True

def process_form_message(topic: str, message: Dict[str, Any]) -> bool:
    """Process form submitted message."""
    # Implementation for form processing
    print(f"Processing form message: {message}")
    return True
```

## Consumer Groups and Scaling

### Consumer Group Coordinator

```python
from kafka import KafkaAdminClient, KafkaConsumer
from kafka.structs import TopicPartition
import threading
import time

class ConsumerGroupCoordinator:
    def __init__(self, bootstrap_servers: str, group_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
        self.logger = logging.getLogger(__name__)

    def get_consumer_lag(self) -> Dict[str, Dict[int, int]]:
        """
        Get consumer lag for all partitions in the consumer group.
        Returns a dictionary with topic names as keys and partition lags as values.
        """
        try:
            # This is a simplified approach - in practice you'd use Kafka's admin APIs
            # or a monitoring solution like Confluent Control Center

            # For now, return a mock implementation
            consumer = KafkaConsumer(
                group_id=self.group_id,
                bootstrap_servers=self.bootstrap_servers
            )

            # Get assignment
            assignment = consumer.assignment()

            lag_info = {}
            for tp in assignment:
                # Get current position and high watermark
                current_pos = consumer.position(tp)
                high_watermark = consumer.end_offsets([tp])[tp]

                lag = high_watermark - current_pos
                if tp.topic not in lag_info:
                    lag_info[tp.topic] = {}
                lag_info[tp.topic][tp.partition] = lag

            consumer.close()
            return lag_info

        except Exception as e:
            self.logger.error(f"Error getting consumer lag: {e}")
            return {}

    def rebalance_callback(self, consumer, partitions):
        """Callback for partition rebalancing events."""
        self.logger.info(f"Rebalanced: {partitions}")
        # Perform any necessary cleanup or initialization for new partitions

    def create_consumer_with_callbacks(self, topics: List[str]) -> KafkaConsumer:
        """Create consumer with rebalancing callbacks."""
        consumer = KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            enable_auto_commit=False
        )

        # Subscribe with callbacks
        consumer.subscribe(topics=topics, listener=ConsumerRebalanceListener(
            on_assign=self.rebalance_callback
        ))

        return consumer
```

## Error Handling and Monitoring

### Consumer with Error Tracking

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Consumer metrics
MESSAGES_CONSUMED = Counter('kafka_consumer_messages_consumed_total',
                          'Total messages consumed by consumer',
                          ['topic', 'consumer_group', 'status'])
PROCESSING_LATENCY = Histogram('kafka_message_processing_duration_seconds',
                             'Time taken to process messages')
CONSUMER_LAG = Gauge('kafka_consumer_lag',
                    'Current consumer lag',
                    ['topic', 'partition', 'consumer_group'])

class MonitoredConsumer:
    def __init__(self, consumer: KafkaConsumer, logger: logging.Logger):
        self.consumer = consumer
        self.logger = logger

    def consume_with_monitoring(self, message_handler: Callable[[str, Dict[str, Any]], bool]):
        """Consume messages with Prometheus metrics collection."""
        try:
            for message in self.consumer:
                start_time = time.time()

                try:
                    success = message_handler(message.topic, message.value)

                    # Record processing time
                    processing_time = time.time() - start_time
                    PROCESSING_LATENCY.observe(processing_time)

                    if success:
                        self.consumer.commit()
                        MESSAGES_CONSUMED.labels(
                            topic=message.topic,
                            consumer_group=self.consumer.config['group_id'],
                            status='success'
                        ).inc()
                        self.logger.debug(f'Successfully processed message from {message.topic}')
                    else:
                        MESSAGES_CONSUMED.labels(
                            topic=message.topic,
                            consumer_group=self.consumer.config['group_id'],
                            status='failure'
                        ).inc()
                        self.logger.warning(f'Failed to process message from {message.topic}')

                except Exception as e:
                    processing_time = time.time() - start_time
                    PROCESSING_LATENCY.observe(processing_time)

                    MESSAGES_CONSUMED.labels(
                        topic=message.topic,
                        consumer_group=self.consumer.config['group_id'],
                        status='error'
                    ).inc()

                    self.logger.error(f'Error processing message from {message.topic}: {e}')

        except KeyboardInterrupt:
            self.logger.info("Monitored consumer interrupted")
        finally:
            self.consumer.close()
```

## Consumer Shutdown Patterns

### Graceful Consumer Shutdown

```python
import signal
import threading

class GracefulConsumer:
    def __init__(self, consumer: KafkaConsumer, logger: logging.Logger):
        self.consumer = consumer
        self.logger = logger
        self.shutdown_event = threading.Event()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()

    def consume_with_graceful_shutdown(self, message_handler: Callable[[str, Dict[str, Any]], bool]):
        """Consume messages with ability to shut down gracefully."""
        try:
            for message in self.consumer:
                # Check for shutdown signal
                if self.shutdown_event.is_set():
                    self.logger.info("Shutdown signal received, stopping consumption...")
                    break

                try:
                    success = message_handler(message.topic, message.value)

                    if success:
                        self.consumer.commit()
                    else:
                        self.logger.warning(f'Failed to process message from {message.topic}')

                except Exception as e:
                    self.logger.error(f'Error processing message from {message.topic}: {e}')
                    # Continue processing other messages

        finally:
            # Flush any remaining messages and close consumer
            try:
                self.consumer.commit()
            except Exception as e:
                self.logger.warning(f"Error committing final offsets: {e}")

            self.consumer.close()
            self.logger.info("Consumer closed gracefully")
```

This comprehensive consumer implementation guide provides all the patterns and best practices needed for reliable message consumption in the CRM system.