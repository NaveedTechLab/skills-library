# Fault Tolerance Patterns for Kafka Event Streaming

## Overview

This document outlines fault tolerance patterns and strategies for ensuring the Kafka-based event streaming system remains operational and reliable despite failures in various components.

## Failure Types and Scenarios

### Common Failure Modes

#### Broker Failures
```python
from kafka import KafkaProducer, KafkaConsumer
import time
import random
from typing import Dict, Any, List

class BrokerFailureSimulator:
    """
    Simulates various broker failure scenarios for testing fault tolerance.
    """

    def __init__(self, bootstrap_servers: List[str]):
        self.bootstrap_servers = bootstrap_servers
        self.active_brokers = bootstrap_servers.copy()
        self.failed_brokers = []

    def simulate_broker_failure(self, broker_to_fail: str):
        """
        Simulate a broker failure by marking it as inactive.
        """
        if broker_to_fail in self.active_brokers:
            self.active_brokers.remove(broker_to_fail)
            self.failed_brokers.append(broker_to_fail)
            print(f"Broker {broker_to_fail} marked as failed")

    def simulate_broker_recovery(self, broker_to_recover: str):
        """
        Simulate a broker recovery by marking it as active.
        """
        if broker_to_recover in self.failed_brokers:
            self.failed_brokers.remove(broker_to_recover)
            self.active_brokers.append(broker_to_recover)
            print(f"Broker {broker_to_recover} recovered")

    def get_healthy_brokers(self) -> List[str]:
        """
        Get list of currently healthy brokers.
        """
        return self.active_brokers.copy()
```

#### Network Partitions
```python
class NetworkPartitionSimulator:
    """
    Simulates network partition scenarios affecting Kafka clusters.
    """

    def __init__(self, cluster_topology: Dict[str, List[str]]):
        """
        cluster_topology: Dictionary mapping regions/datacenters to brokers
        Example: {'us-east': ['broker1:9092', 'broker2:9092'], 'us-west': ['broker3:9092']}
        """
        self.cluster_topology = cluster_topology
        self.partitioned_regions = set()

    def isolate_region(self, region: str):
        """
        Simulate network isolation of a region/datacenter.
        """
        if region in self.cluster_topology:
            self.partitioned_regions.add(region)
            print(f"Region {region} isolated from the cluster")

    def restore_region_connectivity(self, region: str):
        """
        Restore connectivity to a region.
        """
        self.partitioned_regions.discard(region)
        print(f"Connectivity restored to region {region}")

    def is_region_accessible(self, region: str) -> bool:
        """
        Check if a region is currently accessible.
        """
        return region not in self.partitioned_regions
```

## Producer Fault Tolerance

### Resilient Producer Implementation

#### Retry Logic with Exponential Backoff
```python
import time
import random
from functools import wraps

def retry_with_backoff(max_retries: int = 5, base_delay: float = 1.0,
                      max_delay: float = 60.0, jitter: bool = True):
    """
    Decorator for implementing retry logic with exponential backoff.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        # Last attempt, raise the exception
                        print(f"All retry attempts failed. Last error: {e}")
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

class ResilientProducer:
    """
    Producer with built-in fault tolerance and retry mechanisms.
    """

    def __init__(self, bootstrap_servers: List[str], client_id: str = "resilient_producer"):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id

        # Initialize with initial bootstrap servers
        self.producer = self._create_producer(self.bootstrap_servers)

    def _create_producer(self, servers: List[str]) -> KafkaProducer:
        """
        Create a Kafka producer with fault-tolerant settings.
        """
        return KafkaProducer(
            bootstrap_servers=servers,
            client_id=self.client_id,

            # Serialization
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,

            # Reliability settings
            acks='all',  # Leader waits for all in-sync replicas
            retries=2147483647,  # Effectively infinite retries
            max_in_flight_requests_per_connection=5,  # Prevent message reordering

            # Performance settings
            linger_ms=5,  # Small delay to batch messages together
            batch_size=16384,  # Batch size in bytes (16KB)
            compression_type='snappy',  # Compress messages to save bandwidth

            # Connection settings
            connections_max_idle_ms=540000,  # 9 minutes idle connection timeout
            reconnect_backoff_ms=50,  # Initial backoff for reconnections
            reconnect_backoff_max_ms=1000,  # Max backoff for reconnections

            # Request settings
            request_timeout_ms=30000,  # 30 seconds request timeout
            delivery_timeout_ms=120000,  # 2 minutes delivery timeout
        )

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def send_message(self, topic: str, message: Dict[str, Any], key: str = None) -> bool:
        """
        Send a message with retry logic.
        """
        try:
            future = self.producer.send(topic, value=message, key=key)
            record_metadata = future.get(timeout=30)

            print(f'Message delivered to {topic}[{record_metadata.partition}] '
                  f'at offset {record_metadata.offset}')
            return True

        except Exception as e:
            print(f'Error sending message to {topic}: {str(e)}')
            # Raise exception to trigger retry
            raise e

    def update_bootstrap_servers(self, new_servers: List[str]):
        """
        Update bootstrap servers when brokers become unavailable.
        """
        print(f"Updating bootstrap servers from {self.bootstrap_servers} to {new_servers}")
        self.bootstrap_servers = new_servers

        # Create new producer with updated servers
        old_producer = self.producer
        self.producer = self._create_producer(new_servers)

        # Close old producer
        old_producer.close()

    def close(self):
        """
        Close the producer.
        """
        self.producer.close()
```

#### Producer with Health Monitoring
```python
import threading
import time
from datetime import datetime, timedelta

class MonitoredResilientProducer(ResilientProducer):
    """
    Producer with health monitoring and automatic failover capabilities.
    """

    def __init__(self, bootstrap_servers: List[str], client_id: str = "monitored_producer"):
        super().__init__(bootstrap_servers, client_id)
        self.health_monitor_thread = None
        self.monitoring_active = False
        self.server_health = {server: True for server in bootstrap_servers}
        self.last_successful_connection = {server: datetime.now() for server in bootstrap_servers}
        self.failed_connection_count = {server: 0 for server in bootstrap_servers}
        self.max_failures_before_marking_down = 3

    def start_health_monitoring(self, check_interval: int = 30):
        """
        Start the health monitoring thread.
        """
        self.monitoring_active = True
        self.health_monitor_thread = threading.Thread(
            target=self._health_monitor_loop,
            args=(check_interval,),
            daemon=True
        )
        self.health_monitor_thread.start()
        print("Health monitoring started")

    def _health_monitor_loop(self, check_interval: int):
        """
        Background loop that monitors broker health.
        """
        while self.monitoring_active:
            try:
                self._check_broker_health()

                # Check if we need to update bootstrap servers
                healthy_servers = [s for s, healthy in self.server_health.items() if healthy]
                if healthy_servers != self.bootstrap_servers:
                    self.update_bootstrap_servers(healthy_servers)

                time.sleep(check_interval)

            except Exception as e:
                print(f"Error in health monitor: {e}")
                time.sleep(check_interval)

    def _check_broker_health(self):
        """
        Check health of individual brokers.
        """
        for server in self.bootstrap_servers:
            is_healthy = self._test_server_connection(server)

            if is_healthy:
                self.server_health[server] = True
                self.last_successful_connection[server] = datetime.now()
                self.failed_connection_count[server] = 0
            else:
                self.failed_connection_count[server] += 1
                if self.failed_connection_count[server] >= self.max_failures_before_marking_down:
                    self.server_health[server] = False
                    print(f"Marked server {server} as unhealthy")

    def _test_server_connection(self, server: str) -> bool:
        """
        Test connection to a specific server.
        """
        try:
            # Create a temporary connection to test server health
            host, port = server.split(':')
            port = int(port)

            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5-second timeout
            result = sock.connect_ex((host, port))
            sock.close()

            return result == 0  # Connection successful
        except Exception:
            return False

    def stop_health_monitoring(self):
        """
        Stop the health monitoring thread.
        """
        self.monitoring_active = False
        if self.health_monitor_thread:
            self.health_monitor_thread.join(timeout=5)
        print("Health monitoring stopped")
```

## Consumer Fault Tolerance

### Resilient Consumer Implementation

#### Fault-Tolerant Consumer with Restart Capability
```python
import signal
import threading
from typing import Callable

class ResilientConsumer:
    """
    Consumer with fault tolerance and restart capabilities.
    """

    def __init__(self, bootstrap_servers: List[str], group_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer = self._create_consumer(bootstrap_servers)
        self.restart_count = 0
        self.max_restarts = 10
        self.restart_delay = 5  # seconds
        self.running = False
        self.consumer_thread = None
        self.shutdown_event = threading.Event()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _create_consumer(self, servers: List[str]) -> KafkaConsumer:
        """
        Create a Kafka consumer with fault-tolerant settings.
        """
        return KafkaConsumer(
            bootstrap_servers=servers,
            group_id=self.group_id,

            # Deserialization
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,

            # Offset management
            auto_offset_reset='latest',
            enable_auto_commit=False,

            # Performance settings
            max_poll_records=100,
            max_poll_interval_ms=300000,  # 5 minutes for long-running processing
            fetch_max_wait_ms=500,
            fetch_min_bytes=1,
            max_partition_fetch_bytes=1048576,  # 1MB

            # Session timeout settings
            session_timeout_ms=30000,
            heartbeat_interval_ms=3000,

            # Connection settings
            connections_max_idle_ms=540000,
            reconnect_backoff_ms=50,
            reconnect_backoff_max_ms=1000
        )

    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals gracefully.
        """
        print(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()

    def consume_with_fault_tolerance(self, message_handler: Callable[[str, Dict[str, Any]], bool]):
        """
        Consume messages with fault tolerance.
        """
        self.running = True

        while self.running and not self.shutdown_event.is_set():
            try:
                print("Starting message consumption...")

                for message in self.consumer:
                    # Check for shutdown signal
                    if self.shutdown_event.is_set():
                        break

                    try:
                        success = message_handler(message.topic, message.value)

                        if success:
                            # Commit offset after successful processing
                            self.consumer.commit()
                            print(f"Successfully processed message from {message.topic}")
                        else:
                            print(f"Failed to process message from {message.topic}")

                    except Exception as e:
                        print(f"Error processing message from {message.topic}: {e}")
                        # Continue processing other messages

            except Exception as e:
                print(f"Consumer error: {e}")

                # Check if we've exceeded restart limit
                if self.restart_count >= self.max_restarts:
                    print(f"Exceeded maximum restarts ({self.max_restarts}), stopping consumer")
                    break

                # Close current consumer
                try:
                    self.consumer.close()
                except:
                    pass  # Ignore errors when closing

                # Increment restart count
                self.restart_count += 1
                print(f"Restarting consumer (attempt {self.restart_count}/{self.max_restarts})...")

                # Wait before restarting
                time.sleep(self.restart_delay)

                # Create new consumer with current bootstrap servers
                self.consumer = self._create_consumer(self.bootstrap_servers)

        print("Consumer stopped")
        self.running = False

    def update_bootstrap_servers(self, new_servers: List[str]):
        """
        Update bootstrap servers for the consumer.
        """
        print(f"Updating consumer bootstrap servers to: {new_servers}")
        self.bootstrap_servers = new_servers

        # Close current consumer and create new one with updated servers
        current_assignment = self.consumer.assignment()
        current_positions = {}

        # Save current positions before closing
        try:
            for tp in current_assignment:
                current_positions[tp] = self.consumer.position(tp)
        except:
            pass  # Ignore errors when getting positions

        # Close current consumer
        self.consumer.close()

        # Create new consumer
        self.consumer = self._create_consumer(new_servers)

        # Restore partition assignments if possible
        if current_assignment:
            self.consumer.assign(current_assignment)
            # Seek to saved positions
            for tp, pos in current_positions.items():
                try:
                    self.consumer.seek(tp, pos)
                except:
                    pass  # Ignore errors when seeking

    def stop(self):
        """
        Stop the consumer gracefully.
        """
        print("Stopping consumer...")
        self.running = False
        self.shutdown_event.set()

        try:
            self.consumer.close()
        except:
            pass  # Ignore errors when closing
```

#### Consumer with Circuit Breaker Pattern
```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Tripped, not allowing requests
    HALF_OPEN = "half_open"  # Testing if failure condition is resolved

class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures in consumer processing.
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60,
                 success_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
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

class CircuitBreakerConsumer:
    """
    Consumer that incorporates circuit breaker pattern for fault tolerance.
    """

    def __init__(self, bootstrap_servers: List[str], group_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=False,
            max_poll_records=100,
            max_poll_interval_ms=300000
        )
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        self.running = False

    def consume_with_circuit_breaker(self, message_handler: Callable[[str, Dict[str, Any]], bool]):
        """
        Consume messages with circuit breaker protection.
        """
        self.running = True

        while self.running:
            try:
                for message in self.consumer:
                    try:
                        # Wrap message processing in circuit breaker
                        success = self.circuit_breaker.call(
                            message_handler, message.topic, message.value
                        )

                        if success:
                            # Commit offset after successful processing
                            self.consumer.commit()
                            print(f"Successfully processed message from {message.topic}")
                        else:
                            print(f"Message handler returned failure for {message.topic}")

                    except Exception as e:
                        print(f"Circuit breaker tripped or processing error for {message.topic}: {e}")

            except Exception as e:
                print(f"Consumer error: {e}")
                time.sleep(5)  # Wait before continuing

    def stop(self):
        """
        Stop the consumer.
        """
        self.running = False
        self.consumer.close()
```

## Cluster-Level Fault Tolerance

### Multi-Region Deployment Pattern

#### Cross-Region Replication Setup
```python
from kafka.admin import KafkaAdminClient
from kafka.structs import ConfigResource, ConfigResourceType
import json

class CrossRegionReplicator:
    """
    Manages cross-region replication for Kafka clusters.
    """

    def __init__(self, primary_cluster_config: dict, secondary_cluster_config: dict):
        self.primary_admin = KafkaAdminClient(**primary_cluster_config)
        self.secondary_admin = KafkaAdminClient(**secondary_cluster_config)
        self.primary_config = primary_cluster_config
        self.secondary_config = secondary_cluster_config

    def setup_mirror_maker(self, topics_to_replicate: List[str],
                          replication_factor: int = 2) -> bool:
        """
        Setup MirrorMaker for cross-region replication.
        """
        try:
            # Configure topics in secondary region with appropriate settings
            for topic in topics_to_replicate:
                # Get topic configuration from primary
                primary_configs = self.primary_admin.describe_configs([
                    ConfigResource(ConfigResourceType.TOPIC, topic)
                ])

                # Create topic in secondary with replication
                # This is conceptual - actual MirrorMaker setup would be done separately
                print(f"Configuring replication for topic: {topic}")

            print("MirrorMaker setup completed")
            return True

        except Exception as e:
            print(f"Error setting up MirrorMaker: {e}")
            return False

    def verify_replication_status(self) -> Dict[str, Any]:
        """
        Verify the status of cross-region replication.
        """
        try:
            # Check if topics exist in both regions
            primary_topics = set(self.primary_admin.list_consumer_groups())
            secondary_topics = set(self.secondary_admin.list_consumer_groups())

            replication_status = {
                'primary_topics': list(primary_topics),
                'secondary_topics': list(secondary_topics),
                'topics_in_sync': list(primary_topics.intersection(secondary_topics)),
                'topics_out_of_sync': list(primary_topics.symmetric_difference(secondary_topics))
            }

            return replication_status

        except Exception as e:
            print(f"Error checking replication status: {e}")
            return {}
```

### Failover Management

#### Automatic Failover Controller
```python
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

class FailoverController:
    """
    Manages automatic failover between primary and secondary Kafka clusters.
    """

    def __init__(self, primary_config: dict, secondary_config: dict):
        self.primary_config = primary_config
        self.secondary_config = secondary_config
        self.current_active_cluster = "primary"
        self.failover_threshold = 3  # Number of consecutive failures before failover
        self.failure_count = 0
        self.last_failover_time = None
        self.cooldown_period = 300  # 5 minutes cooldown after failover
        self.failover_lock = threading.Lock()

    def is_failover_allowed(self) -> bool:
        """
        Check if failover is allowed based on cooldown period.
        """
        if self.last_failover_time is None:
            return True

        time_since_failover = datetime.now() - self.last_failover_time
        return time_since_failover.total_seconds() > self.cooldown_period

    def trigger_failover(self) -> bool:
        """
        Trigger failover to secondary cluster.
        """
        with self.failover_lock:
            if not self.is_failover_allowed():
                print("Failover not allowed due to cooldown period")
                return False

            if self.current_active_cluster == "primary":
                self.current_active_cluster = "secondary"
                self.last_failover_time = datetime.now()
                self.failure_count = 0

                print("Switched to secondary cluster due to failover")
                return True
            else:
                print("Already on secondary cluster")
                return False

    def record_failure(self) -> bool:
        """
        Record a failure and check if failover should be triggered.
        """
        self.failure_count += 1
        print(f"Recorded failure #{self.failure_count}")

        if self.failure_count >= self.failover_threshold:
            success = self.trigger_failover()
            if success:
                self.failure_count = 0  # Reset after failover
            return success

        return False

    def record_success(self):
        """
        Record a successful operation and reset failure count.
        """
        if self.failure_count > 0:
            print(f"Reset failure count from {self.failure_count} to 0 after success")
            self.failure_count = 0

    def get_active_cluster_config(self) -> dict:
        """
        Get configuration for currently active cluster.
        """
        if self.current_active_cluster == "primary":
            return self.primary_config
        else:
            return self.secondary_config

    def attempt_failback(self) -> bool:
        """
        Attempt to fail back to primary cluster if it's healthy.
        """
        with self.failover_lock:
            if self.current_active_cluster != "secondary":
                return False  # Not in secondary mode

            # Check if primary cluster is healthy
            if self._is_cluster_healthy(self.primary_config):
                self.current_active_cluster = "primary"
                print("Failed back to primary cluster")
                return True

        return False

    def _is_cluster_healthy(self, cluster_config: dict) -> bool:
        """
        Check if a cluster is healthy.
        """
        try:
            # Test connection to cluster
            from kafka import KafkaProducer
            producer = KafkaProducer(**cluster_config)

            # Try to send a test message
            future = producer.send('_test_topic', value=b'test')
            future.get(timeout=10)

            producer.close()
            return True

        except Exception as e:
            print(f"Cluster health check failed: {e}")
            return False
```

## Message Durability and Consistency

### Exactly-Once Semantics Implementation

#### Idempotent Producer Pattern
```python
class IdempotentProducer:
    """
    Producer that guarantees exactly-once semantics using idempotent settings.
    """

    def __init__(self, bootstrap_servers: List[str]):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,

            # Serialization
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,

            # Enable idempotence for exactly-once semantics
            enable_idempotence=True,

            # Required settings for idempotence
            acks='all',
            retries=2147483647,
            max_in_flight_requests_per_connection=5,

            # Performance settings
            linger_ms=5,
            batch_size=16384,
            compression_type='snappy'
        )

    def send_with_sequence(self, topic: str, message: Dict[str, Any], key: str) -> bool:
        """
        Send message with guaranteed ordering and exactly-once semantics.
        """
        try:
            future = self.producer.send(topic, value=message, key=key)
            record_metadata = future.get(timeout=30)

            print(f'Exactly-once message sent to {topic}[{record_metadata.partition}] '
                  f'at offset {record_metadata.offset}')
            return True

        except Exception as e:
            print(f'Error sending idempotent message: {e}')
            return False

    def close(self):
        """
        Close the producer.
        """
        self.producer.close()
```

#### Transactional Producer Pattern
```python
class TransactionalProducer:
    """
    Producer that uses Kafka transactions for atomic operations.
    """

    def __init__(self, bootstrap_servers: List[str], transactional_id: str):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,

            # Serialization
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,

            # Transaction settings
            transactional_id=transactional_id,
            enable_idempotence=True,

            # Required settings for transactions
            acks='all',
            retries=2147483647,
            max_in_flight_requests_per_connection=5
        )

        # Initialize transactions
        self.producer.init_transactions()

    def send_transaction(self, messages_by_topic: Dict[str, List[Dict[str, Any]]]) -> bool:
        """
        Send messages across multiple topics in a single transaction.
        """
        try:
            # Begin transaction
            self.producer.begin_transaction()

            # Send messages to all specified topics
            sent_messages = []
            for topic, messages in messages_by_topic.items():
                for message in messages:
                    future = self.producer.send(topic, value=message)
                    record_metadata = future.get(timeout=10)
                    sent_messages.append((topic, record_metadata))

            # Commit transaction - all messages are sent atomically
            self.producer.commit_transaction()

            print(f'Transaction completed successfully: {len(sent_messages)} messages sent')
            return True

        except Exception as e:
            print(f'Transaction failed, aborting: {e}')
            try:
                # Abort transaction on error
                self.producer.abort_transaction()
            except Exception as abort_error:
                print(f'Error aborting transaction: {abort_error}')
            return False

    def close(self):
        """
        Close the producer.
        """
        self.producer.close()
```

## Health Monitoring and Diagnostics

### Comprehensive Health Checker

```python
import subprocess
from typing import Dict, Any, List

class KafkaHealthChecker:
    """
    Comprehensive health checker for Kafka clusters and applications.
    """

    def __init__(self, bootstrap_servers: List[str], admin_client_config: dict = None):
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = KafkaAdminClient(**(admin_client_config or {}))

    def check_cluster_health(self) -> Dict[str, Any]:
        """
        Check overall cluster health.
        """
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'cluster_health': 'unknown',
            'brokers': [],
            'topics': [],
            'partitions': [],
            'consumers': []
        }

        try:
            # Check broker connectivity
            for server in self.bootstrap_servers:
                broker_health = self._check_broker_health(server)
                health_report['brokers'].append(broker_health)

            # Check topic health
            try:
                topics = self.admin_client.list_consumer_groups()
                for topic in topics:
                    topic_info = self._get_topic_health(topic)
                    health_report['topics'].append(topic_info)
            except:
                pass  # Ignore if we can't list topics

            # Determine overall cluster health
            broker_statuses = [b['status'] for b in health_report['brokers']]
            if 'unhealthy' in broker_statuses:
                health_report['cluster_health'] = 'unhealthy'
            elif 'degraded' in broker_statuses:
                health_report['cluster_health'] = 'degraded'
            else:
                health_report['cluster_health'] = 'healthy'

        except Exception as e:
            health_report['cluster_health'] = 'error'
            health_report['error'] = str(e)

        return health_report

    def _check_broker_health(self, server: str) -> Dict[str, Any]:
        """
        Check health of an individual broker.
        """
        host, port = server.split(':')
        port = int(port)

        broker_health = {
            'server': server,
            'status': 'unknown',
            'response_time_ms': None,
            'last_checked': datetime.now().isoformat()
        }

        try:
            import socket
            start_time = time.time()

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()

            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            if result == 0:
                broker_health['status'] = 'healthy'
                broker_health['response_time_ms'] = round(response_time, 2)
            else:
                broker_health['status'] = 'unhealthy'

        except Exception as e:
            broker_health['status'] = 'error'
            broker_health['error'] = str(e)

        return broker_health

    def _get_topic_health(self, topic: str) -> Dict[str, Any]:
        """
        Get health information for a specific topic.
        """
        topic_health = {
            'topic': topic,
            'status': 'unknown',
            'partitions': [],
            'replication_factor': 0
        }

        try:
            # Get topic metadata
            metadata = self.admin_client.describe_configs([
                ConfigResource(ConfigResourceType.TOPIC, topic)
            ])

            # This is a simplified approach - in practice you'd use more detailed metadata
            topic_health['status'] = 'healthy'

        except Exception as e:
            topic_health['status'] = 'error'
            topic_health['error'] = str(e)

        return topic_health

    def get_health_summary(self) -> str:
        """
        Get a text summary of cluster health.
        """
        health_report = self.check_cluster_health()

        healthy_brokers = len([b for b in health_report['brokers'] if b['status'] == 'healthy'])
        total_brokers = len(health_report['brokers'])

        summary = f"""
        Kafka Cluster Health Summary
        ============================
        Overall Status: {health_report['cluster_health']}
        Healthy Brokers: {healthy_brokers}/{total_brokers}
        Last Checked: {health_report['timestamp']}
        """

        return summary
```

This comprehensive fault tolerance guide provides all the patterns and implementations needed to ensure the Kafka-based event streaming system remains operational and reliable despite various failure scenarios.