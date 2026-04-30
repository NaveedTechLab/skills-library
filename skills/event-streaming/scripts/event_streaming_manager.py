#!/usr/bin/env python3
"""
Event Streaming Manager
Implements Kafka-based event streaming to decouple channel intake from agent processing.
Manages producers, consumers, and message reliability across the processing pipeline.
"""

import os
import sys
import json
import time
import uuid
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

# Import required libraries
try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError
    import redis
    from cryptography.fernet import Fernet
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install required packages: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EventType(Enum):
    RAW_MESSAGE = "raw_message"
    NORMALIZED_MESSAGE = "normalized_message"
    CUSTOMER_IDENTITY = "customer_identity"
    TICKET_CREATED = "ticket_created"
    TICKET_UPDATED = "ticket_updated"
    RESPONSE_OUTBOUND = "response_outbound"
    SYSTEM_ALERT = "system_alert"

class EventStreamingManager:
    def __init__(self, bootstrap_servers: str, redis_url: str = None, encryption_key: bytes = None):
        self.bootstrap_servers = bootstrap_servers
        self.redis_client = None

        # Initialize Redis if URL provided
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                logger.info("Connected to Redis successfully")
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {e}")

        # Initialize Kafka producer and consumer
        self.producer = self._create_producer()
        self.consumer = None

        # Initialize encryption
        if encryption_key:
            self.cipher_suite = Fernet(encryption_key)
        else:
            # Generate a key for demonstration (use proper key management in production)
            key = Fernet.generate_key()
            self.cipher_suite = Fernet(key)
            logger.warning("Generated temporary encryption key. Use proper key management in production.")

        # Initialize internal state
        self.running = False
        self.consumer_thread = None
        self.message_handlers = {}

    def _create_producer(self) -> KafkaProducer:
        """Create a Kafka producer with fault-tolerant settings."""
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,

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

    def _create_consumer(self, group_id: str) -> KafkaConsumer:
        """Create a Kafka consumer with fault-tolerant settings."""
        return KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,

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

    def initialize_topics(self):
        """Initialize Kafka topics needed for the event streaming system."""
        logger.info("Initializing Kafka topics...")

        # In a real implementation, you would use KafkaAdminClient to create topics
        # For this example, we'll just log the expected topics
        topics = [
            'ingestion.raw.messages',
            'ingestion.normalized.messages',
            'processing.customer.identities',
            'processing.tickets.in',
            'processing.tickets.out',
            'processing.responses.out',
            'notifications.alerts',
            'notifications.audit'
        ]

        logger.info(f"Expected topics: {topics}")
        logger.info("Note: Topics should be created using KafkaAdminClient in production")

    def publish_event(self, topic: str, event_type: EventType, data: Dict[str, Any],
                     key: Optional[str] = None, headers: Optional[Dict[str, str]] = None) -> bool:
        """Publish an event to a Kafka topic."""
        try:
            # Create the event envelope
            event = {
                'event_id': str(uuid.uuid4()),
                'event_type': event_type.value,
                'timestamp': datetime.utcnow().isoformat(),
                'producer_id': 'event_streaming_manager',
                'data': data
            }

            # Send message
            future = self.producer.send(
                topic=topic,
                value=event,
                key=key,
                headers=headers or {}
            )

            # Wait for acknowledgment (synchronous send for reliability)
            record_metadata = future.get(timeout=30)

            logger.info(f'Event published to {topic}[{record_metadata.partition}] '
                       f'at offset {record_metadata.offset}')
            return True

        except Exception as e:
            logger.error(f'Error publishing event to {topic}: {e}')
            return False

    def subscribe_to_topic(self, topic: str, group_id: str, handler: Callable[[Dict[str, Any]], bool]):
        """Subscribe to a topic and register a handler for processing messages."""
        self.message_handlers[topic] = handler

        if self.consumer is None:
            self.consumer = self._create_consumer(group_id)

        # Subscribe to the topic
        self.consumer.subscribe(topics=[topic])
        logger.info(f"Subscribed to topic: {topic} with group: {group_id}")

    def start_consumer(self):
        """Start the consumer in a separate thread."""
        if not self.message_handlers:
            logger.warning("No message handlers registered. Consumer will have nothing to process.")
            return

        self.running = True
        self.consumer_thread = threading.Thread(target=self._consumer_loop, daemon=True)
        self.consumer_thread.start()
        logger.info("Event consumer started")

    def _consumer_loop(self):
        """Main consumer loop that processes messages."""
        logger.info("Starting consumer loop...")

        try:
            while self.running:
                try:
                    for message in self.consumer:
                        if not self.running:
                            break

                        topic = message.topic
                        event_data = message.value

                        # Find and call the appropriate handler
                        handler = self.message_handlers.get(topic)

                        if handler:
                            try:
                                success = handler(event_data)

                                if success:
                                    # Commit offset only after successful processing
                                    self.consumer.commit()
                                    logger.debug(f'Successfully processed event from {topic}')
                                else:
                                    logger.warning(f'Handler failed for event from {topic}')

                            except Exception as e:
                                logger.error(f'Error in handler for {topic}: {e}')
                        else:
                            logger.warning(f'No handler registered for topic: {topic}')

                except Exception as e:
                    logger.error(f'Error in consumer loop: {e}')
                    time.sleep(5)  # Wait before retrying

        except KeyboardInterrupt:
            logger.info("Consumer loop interrupted")
        finally:
            if self.consumer:
                self.consumer.close()

    def stop_consumer(self):
        """Stop the consumer."""
        logger.info("Stopping event consumer...")
        self.running = False

        if self.consumer_thread:
            self.consumer_thread.join(timeout=10)  # Wait up to 10 seconds

        if self.consumer:
            try:
                self.consumer.commit()  # Commit any remaining offsets
                self.consumer.close()
            except Exception as e:
                logger.error(f"Error closing consumer: {e}")

        logger.info("Event consumer stopped")

    def send_raw_message(self, channel: str, message_data: Dict[str, Any],
                        message_id: str = None) -> bool:
        """Send a raw message to the ingestion pipeline."""
        if message_id is None:
            message_id = str(uuid.uuid4())

        data = {
            'channel': channel,
            'message_id': message_id,
            'content': message_data,
            'received_at': datetime.utcnow().isoformat()
        }

        return self.publish_event(
            topic='ingestion.raw.messages',
            event_type=EventType.RAW_MESSAGE,
            data=data,
            key=message_id
        )

    def send_normalized_message(self, normalized_data: Dict[str, Any],
                              correlation_id: str = None) -> bool:
        """Send a normalized message to the processing pipeline."""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())

        data = {
            'correlation_id': correlation_id,
            'normalized_content': normalized_data,
            'processed_at': datetime.utcnow().isoformat()
        }

        return self.publish_event(
            topic='ingestion.normalized.messages',
            event_type=EventType.NORMALIZED_MESSAGE,
            data=data,
            key=correlation_id
        )

    def send_customer_identity_event(self, customer_id: str, identity_data: Dict[str, Any]) -> bool:
        """Send a customer identity resolution event."""
        data = {
            'customer_id': customer_id,
            'identity_data': identity_data,
            'resolved_at': datetime.utcnow().isoformat()
        }

        return self.publish_event(
            topic='processing.customer.identities',
            event_type=EventType.CUSTOMER_IDENTITY,
            data=data,
            key=customer_id
        )

    def send_ticket_created_event(self, ticket_id: str, ticket_data: Dict[str, Any]) -> bool:
        """Send a ticket created event."""
        data = {
            'ticket_id': ticket_id,
            'ticket_data': ticket_data,
            'created_at': datetime.utcnow().isoformat()
        }

        return self.publish_event(
            topic='processing.tickets.in',
            event_type=EventType.TICKET_CREATED,
            data=data,
            key=ticket_id
        )

    def send_system_alert(self, alert_type: str, alert_data: Dict[str, Any]) -> bool:
        """Send a system alert notification."""
        data = {
            'alert_type': alert_type,
            'alert_data': alert_data,
            'timestamp': datetime.utcnow().isoformat()
        }

        return self.publish_event(
            topic='notifications.alerts',
            event_type=EventType.SYSTEM_ALERT,
            data=data
        )

    def get_consumer_lag(self, group_id: str) -> Dict[str, Any]:
        """Get consumer lag information for monitoring."""
        if not self.consumer:
            return {}

        try:
            # Get current positions
            current_positions = self.consumer.position(self.consumer.assignment())

            # Get end offsets (high watermarks)
            end_offsets = self.consumer.end_offsets(self.consumer.assignment())

            # Calculate lag for each partition
            lag_info = {}
            total_lag = 0

            for tp in self.consumer.assignment():
                current_pos = current_positions.get(tp, 0)
                end_offset = end_offsets.get(tp, 0)
                lag = max(0, end_offset - current_pos)

                lag_info[f"{tp.topic}[{tp.partition}]"] = {
                    'current_offset': current_pos,
                    'high_watermark': end_offset,
                    'lag': lag
                }
                total_lag += lag

            return {
                'group_id': group_id,
                'total_lag': total_lag,
                'partition_lag': lag_info
            }

        except Exception as e:
            logger.error(f"Error getting consumer lag: {e}")
            return {}

def main():
    """Main function demonstrating the Event Streaming Manager."""
    print("Event Streaming Manager")
    print("=" * 50)

    # Get configuration from environment or use defaults
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    try:
        # Initialize the Event Streaming Manager
        event_manager = EventStreamingManager(
            bootstrap_servers=bootstrap_servers,
            redis_url=redis_url
        )

        # Initialize topics (in production, this would be done separately)
        print("\n1. Initializing topics...")
        event_manager.initialize_topics()

        # Send a sample raw message
        print("\n2. Sending sample raw message...")
        sample_message = {
            "channel": "email",
            "from": "customer@example.com",
            "to": "support@company.com",
            "subject": "Help with my account",
            "body": "I'm having trouble logging into my account.",
            "timestamp": datetime.utcnow().isoformat()
        }

        success = event_manager.send_raw_message(
            channel="email",
            message_data=sample_message
        )
        print(f"   Raw message sent: {success}")

        # Send a sample normalized message
        print("\n3. Sending sample normalized message...")
        normalized_data = {
            "customer_id": "cust_12345",
            "message_type": "support_request",
            "priority": "medium",
            "content": "Customer needs help with login",
            "channel": "email"
        }

        success = event_manager.send_normalized_message(normalized_data)
        print(f"   Normalized message sent: {success}")

        # Send a sample customer identity event
        print("\n4. Sending sample customer identity event...")
        identity_data = {
            "email": "customer@example.com",
            "phone": "+1-555-0123",
            "name": "John Doe",
            "external_id": "ext_67890"
        }

        success = event_manager.send_customer_identity_event(
            customer_id="cust_12345",
            identity_data=identity_data
        )
        print(f"   Customer identity event sent: {success}")

        # Send a sample ticket created event
        print("\n5. Sending sample ticket created event...")
        ticket_data = {
            "subject": "Login Issues",
            "description": "Customer reported problems with account login",
            "priority": "high",
            "category": "technical",
            "customer_id": "cust_12345"
        }

        success = event_manager.send_ticket_created_event(
            ticket_id="ticket_abc123",
            ticket_data=ticket_data
        )
        print(f"   Ticket created event sent: {success}")

        # Register a simple message handler
        def simple_handler(event_data: Dict[str, Any]) -> bool:
            """Simple handler that logs received events."""
            logger.info(f"Received event: {event_data.get('event_type')} - {event_data.get('event_id')}")
            return True  # Indicate successful processing

        # Subscribe to the normalized messages topic
        print("\n6. Subscribing to normalized messages topic...")
        event_manager.subscribe_to_topic(
            topic='ingestion.normalized.messages',
            group_id='demo-consumer-group',
            handler=simple_handler
        )

        # Start the consumer
        print("\n7. Starting consumer...")
        event_manager.start_consumer()

        # Wait for a bit to see consumer in action
        print("\n8. Waiting to see consumer process messages...")
        time.sleep(10)

        # Get consumer lag information
        print("\n9. Getting consumer lag information...")
        lag_info = event_manager.get_consumer_lag('demo-consumer-group')
        print(f"   Consumer lag: {lag_info.get('total_lag', 'N/A')} messages")

        # Stop the consumer
        print("\n10. Stopping consumer...")
        event_manager.stop_consumer()

        print("\nEvent Streaming Manager demonstration completed successfully!")

    except Exception as e:
        logger.error(f"Error running Event Streaming Manager: {e}")
        print(f"\nError: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())