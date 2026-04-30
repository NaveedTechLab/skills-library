# Monitoring and Observability Guide

## Overview

This document provides comprehensive guidance for monitoring and observing the Kafka-based event streaming system. Effective monitoring is crucial for maintaining system reliability, performance, and availability.

## Metrics Collection

### Key Metrics Categories

#### Producer Metrics
```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Message production metrics
MESSAGES_PRODUCED = Counter(
    'kafka_producer_messages_total',
    'Total messages produced by topic and producer',
    ['topic', 'producer_id', 'status']  # status: success, failure
)

PRODUCE_LATENCY = Histogram(
    'kafka_producer_latency_seconds',
    'Time taken to produce messages',
    ['topic', 'producer_id']
)

PRODUCER_QUEUE_SIZE = Gauge(
    'kafka_producer_queue_size',
    'Current number of messages in producer queue',
    ['producer_id']
)

PRODUCER_BYTES_SENT = Counter(
    'kafka_producer_bytes_total',
    'Total bytes sent by producer',
    ['topic', 'producer_id']
)

PRODUCER_ERRORS = Counter(
    'kafka_producer_errors_total',
    'Total producer errors by type',
    ['error_type', 'topic', 'producer_id']
)
```

#### Consumer Metrics
```python
# Message consumption metrics
MESSAGES_CONSUMED = Counter(
    'kafka_consumer_messages_total',
    'Total messages consumed by topic and consumer group',
    ['topic', 'consumer_group', 'status']  # status: success, failure, error
)

CONSUME_LATENCY = Histogram(
    'kafka_consumer_latency_seconds',
    'Time taken to consume and process messages',
    ['topic', 'consumer_group']
)

CONSUMER_OFFSET = Gauge(
    'kafka_consumer_offset',
    'Current consumer offset by partition',
    ['topic', 'partition', 'consumer_group']
)

CONSUMER_LAG = Gauge(
    'kafka_consumer_lag',
    'Current consumer lag by partition',
    ['topic', 'partition', 'consumer_group']
)

CONSUMER_BYTES_RECEIVED = Counter(
    'kafka_consumer_bytes_total',
    'Total bytes received by consumer',
    ['topic', 'consumer_group']
)
```

### Custom Business Metrics
```python
# Channel-specific metrics
CHANNEL_MESSAGES_RECEIVED = Counter(
    'channel_messages_received_total',
    'Messages received by channel type',
    ['channel_type']
)

TICKETS_CREATED = Counter(
    'tickets_created_total',
    'Tickets created from incoming messages',
    ['channel_type', 'priority']
)

RESPONSE_TIME = Histogram(
    'response_time_seconds',
    'Time from message receipt to response',
    ['channel_type']
)

CUSTOMER_IDENTITY_RESOLUTIONS = Counter(
    'customer_identity_resolutions_total',
    'Customer identity resolution attempts',
    ['resolution_type', 'success']
)
```

## Producer Monitoring Implementation

### Instrumented Producer
```python
import time
from typing import Dict, Any, Optional

class InstrumentedProducer:
    def __init__(self, producer, producer_id: str):
        self.producer = producer
        self.producer_id = producer_id

    def send_with_metrics(self, topic: str, message: Dict[str, Any],
                         key: Optional[str] = None) -> bool:
        """
        Send message with metric collection.
        """
        start_time = time.time()

        try:
            future = self.producer.send(topic, value=message, key=key)
            record_metadata = future.get(timeout=30)

            # Record success metrics
            duration = time.time() - start_time
            PRODUCE_LATENCY.labels(topic=topic, producer_id=self.producer_id).observe(duration)
            MESSAGES_PRODUCED.labels(
                topic=topic,
                producer_id=self.producer_id,
                status='success'
            ).inc()

            # Record message size
            message_size = len(str(message).encode('utf-8'))
            PRODUCER_BYTES_SENT.labels(topic=topic, producer_id=self.producer_id).inc(message_size)

            return True

        except Exception as e:
            # Record failure metrics
            duration = time.time() - start_time
            PRODUCE_LATENCY.labels(topic=topic, producer_id=self.producer_id).observe(duration)
            MESSAGES_PRODUCED.labels(
                topic=topic,
                producer_id=self.producer_id,
                status='failure'
            ).inc()
            PRODUCER_ERRORS.labels(
                error_type=type(e).__name__,
                topic=topic,
                producer_id=self.producer_id
            ).inc()

            return False

    def update_queue_size(self):
        """Update producer queue size metric."""
        # This is a simplified approach - actual implementation depends on the Kafka client
        # For confluent-kafka-python, you might use producer.metrics()
        queue_size = 0  # Placeholder
        PRODUCER_QUEUE_SIZE.labels(producer_id=self.producer_id).set(queue_size)
```

## Consumer Monitoring Implementation

### Instrumented Consumer
```python
import time
from typing import Dict, Any, Callable

class InstrumentedConsumer:
    def __init__(self, consumer, consumer_group: str):
        self.consumer = consumer
        self.consumer_group = consumer_group

    def consume_with_metrics(self, message_handler: Callable[[str, Dict[str, Any]], bool]):
        """
        Consume messages with metric collection.
        """
        for message in self.consumer:
            start_time = time.time()

            try:
                success = message_handler(message.topic, message.value)

                # Record processing time
                duration = time.time() - start_time
                CONSUME_LATENCY.labels(
                    topic=message.topic,
                    consumer_group=self.consumer_group
                ).observe(duration)

                # Record message consumption
                status = 'success' if success else 'failure'
                MESSAGES_CONSUMED.labels(
                    topic=message.topic,
                    consumer_group=self.consumer_group,
                    status=status
                ).inc()

                # Record message size
                message_size = len(str(message.value).encode('utf-8'))
                CONSUMER_BYTES_RECEIVED.labels(
                    topic=message.topic,
                    consumer_group=self.consumer_group
                ).inc(message_size)

                if success:
                    # Update offset metrics
                    CONSUMER_OFFSET.labels(
                        topic=message.topic,
                        partition=message.partition,
                        consumer_group=self.consumer_group
                    ).set(message.offset)

                    # Commit offset after successful processing
                    self.consumer.commit()

            except Exception as e:
                # Record error metrics
                duration = time.time() - start_time
                CONSUME_LATENCY.labels(
                    topic=message.topic,
                    consumer_group=self.consumer_group
                ).observe(duration)

                MESSAGES_CONSUMED.labels(
                    topic=message.topic,
                    consumer_group=self.consumer_group,
                    status='error'
                ).inc()

                PRODUCER_ERRORS.labels(
                    error_type=type(e).__name__,
                    topic=message.topic,
                    producer_id=self.consumer_group
                ).inc()

    def update_consumer_lag(self):
        """
        Update consumer lag metrics.
        """
        try:
            # Get current positions
            current_positions = self.consumer.position(self.consumer.assignment())

            # Get end offsets (high watermarks)
            end_offsets = self.consumer.end_offsets(self.consumer.assignment())

            # Calculate and update lag for each partition
            for tp in self.consumer.assignment():
                current_pos = current_positions.get(tp, 0)
                end_offset = end_offsets.get(tp, 0)
                lag = max(0, end_offset - current_pos)

                CONSUMER_LAG.labels(
                    topic=tp.topic,
                    partition=tp.partition,
                    consumer_group=self.consumer_group
                ).set(lag)

        except Exception as e:
            print(f"Error updating consumer lag metrics: {e}")
```

## Health Checks

### System Health Checker
```python
import requests
import socket
from typing import Dict, Any

class HealthChecker:
    def __init__(self, bootstrap_servers: str, zookeeper_servers: str = None):
        self.bootstrap_servers = bootstrap_servers
        self.zookeeper_servers = zookeeper_servers

    def check_kafka_health(self) -> Dict[str, Any]:
        """
        Check Kafka cluster health.
        """
        health_status = {
            'kafka_cluster': {'status': 'unknown', 'details': {}},
            'brokers': [],
            'topics': []
        }

        try:
            # Check if we can connect to bootstrap servers
            for server in self.bootstrap_servers.split(','):
                host, port = server.strip().split(':')
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, int(port)))
                sock.close()

                broker_status = {
                    'server': server,
                    'reachable': result == 0
                }
                health_status['brokers'].append(broker_status)

            # Overall cluster status
            reachable_brokers = [b for b in health_status['brokers'] if b['reachable']]
            if len(reachable_brokers) == len(health_status['brokers']):
                health_status['kafka_cluster']['status'] = 'healthy'
            elif len(reachable_brokers) > 0:
                health_status['kafka_cluster']['status'] = 'degraded'
            else:
                health_status['kafka_cluster']['status'] = 'unhealthy'

        except Exception as e:
            health_status['kafka_cluster']['status'] = 'error'
            health_status['kafka_cluster']['details']['error'] = str(e)

        return health_status

    def check_topic_health(self, topic: str) -> Dict[str, Any]:
        """
        Check health of a specific topic.
        """
        from kafka import KafkaConsumer
        import time

        topic_health = {
            'topic': topic,
            'status': 'unknown',
            'partitions': [],
            'replication_factor': 0
        }

        try:
            consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                enable_auto_commit=False,
                consumer_timeout_ms=5000
            )

            # Get topic metadata
            metadata = consumer.topics()
            if topic in metadata:
                # Get partition information
                partitions = consumer.partitions_for_topic(topic)
                if partitions:
                    for partition in partitions:
                        partition_info = {
                            'partition': partition,
                            'status': 'active',
                            'leader': None,
                            'replicas': [],
                            'isrs': []
                        }

                        # In a real implementation, you'd get leader/replica info
                        topic_health['partitions'].append(partition_info)

                    topic_health['status'] = 'healthy'
                else:
                    topic_health['status'] = 'no_partitions'
            else:
                topic_health['status'] = 'topic_not_found'

            consumer.close()

        except Exception as e:
            topic_health['status'] = 'error'
            topic_health['error'] = str(e)

        return topic_health
```

### Application Health Endpoints
```python
from flask import Flask, jsonify
import time

app = Flask(__name__)

# Global health status tracker
health_status = {
    'last_updated': time.time(),
    'overall_status': 'unknown',
    'components': {},
    'checks': {}
}

@app.route('/health')
def health_check():
    """
    Overall health check endpoint.
    """
    # Update health status
    update_health_status()

    return jsonify({
        'status': health_status['overall_status'],
        'timestamp': health_status['last_updated'],
        'components': health_status['components'],
        'checks': health_status['checks']
    })

@app.route('/health/kafka')
def kafka_health():
    """
    Kafka-specific health check.
    """
    checker = HealthChecker(bootstrap_servers='localhost:9092')
    kafka_health = checker.check_kafka_health()

    return jsonify(kafka_health)

@app.route('/health/topic/<topic_name>')
def topic_health(topic_name):
    """
    Specific topic health check.
    """
    checker = HealthChecker(bootstrap_servers='localhost:9092')
    topic_health = checker.check_topic_health(topic_name)

    return jsonify(topic_health)

def update_health_status():
    """
    Update the global health status.
    """
    global health_status

    # Perform various health checks
    checker = HealthChecker(bootstrap_servers='localhost:9092')

    # Kafka cluster health
    kafka_health = checker.check_kafka_health()
    health_status['components']['kafka'] = kafka_health['kafka_cluster']['status']

    # Overall status calculation
    statuses = list(health_status['components'].values())
    if 'unhealthy' in statuses or 'error' in statuses:
        health_status['overall_status'] = 'unhealthy'
    elif 'degraded' in statuses:
        health_status['overall_status'] = 'degraded'
    else:
        health_status['overall_status'] = 'healthy'

    health_status['last_updated'] = time.time()
```

## Alerting Rules

### Prometheus Alerting Rules
```yaml
# kafka-alerts.yml
groups:
- name: kafka_alerts
  rules:
  # Consumer lag alerts
  - alert: HighConsumerLag
    expr: kafka_consumer_lag > 1000
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High consumer lag detected"
      description: "Consumer {{ $labels.consumer_group }} on topic {{ $labels.topic }} has lag of {{ $value }} messages"

  # Producer error rate alerts
  - alert: HighProducerErrorRate
    expr: rate(kafka_producer_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High producer error rate"
      description: "Producer error rate is {{ $value }} errors per second"

  # Consumer error rate alerts
  - alert: HighConsumerErrorRate
    expr: rate(kafka_consumer_messages_total{status="error"}[5m]) > 0.05
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High consumer error rate"
      description: "Consumer error rate is {{ $value }} errors per second"

  # Low throughput alerts
  - alert: LowMessageThroughput
    expr: rate(kafka_consumer_messages_total[5m]) < 1 and kafka_consumer_messages_total offset 5m > 10
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Low message throughput"
      description: "Message throughput has dropped significantly"

  # Producer queue buildup
  - alert: ProducerQueueBuildup
    expr: kafka_producer_queue_size > 1000
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Producer queue buildup"
      description: "Producer queue has {{ $value }} messages waiting"
```

### Custom Alert Manager
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List

class AlertManager:
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str,
                 recipients: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients

    def send_alert(self, alert_name: str, severity: str, description: str):
        """
        Send an alert notification.
        """
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = ', '.join(self.recipients)
        msg['Subject'] = f"[{severity.upper()}] {alert_name}"

        body = f"""
        Alert: {alert_name}
        Severity: {severity}
        Description: {description}
        Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}

        This is an automated alert from the Kafka monitoring system.
        """

        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()

            print(f"Alert '{alert_name}' sent successfully")
        except Exception as e:
            print(f"Failed to send alert: {e}")

    def evaluate_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Evaluate metrics against alert conditions.
        """
        alerts = []

        # Check consumer lag
        for (topic, partition, consumer_group), lag in metrics.get('consumer_lag', {}).items():
            if lag > 1000:  # Threshold for high lag
                alerts.append({
                    'name': 'HighConsumerLag',
                    'severity': 'warning',
                    'description': f'Consumer {consumer_group} on {topic}[{partition}] has lag of {lag} messages'
                })

        # Check error rates
        error_rate = metrics.get('error_rate', 0)
        if error_rate > 0.1:  # More than 10% error rate
            alerts.append({
                'name': 'HighErrorRate',
                'severity': 'critical',
                'description': f'High error rate detected: {error_rate}/sec'
            })

        return alerts
```

## Dashboard Configuration

### Grafana Dashboard JSON
```json
{
  "dashboard": {
    "id": null,
    "title": "Kafka Event Streaming Dashboard",
    "tags": ["kafka", "streaming", "crm"],
    "timezone": "utc",
    "panels": [
      {
        "id": 1,
        "title": "Message Throughput",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(kafka_consumer_messages_total[1m])",
            "legendFormat": "{{topic}} - {{consumer_group}}"
          }
        ],
        "yAxes": [
          {
            "label": "Messages/sec"
          }
        ]
      },
      {
        "id": 2,
        "title": "Consumer Lag",
        "type": "graph",
        "targets": [
          {
            "expr": "kafka_consumer_lag",
            "legendFormat": "{{topic}}[{{partition}}] - {{consumer_group}}"
          }
        ],
        "yAxes": [
          {
            "label": "Lag (messages)"
          }
        ]
      },
      {
        "id": 3,
        "title": "Producer Success Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "sum(rate(kafka_producer_messages_total{status=\"success\"}[5m])) / sum(rate(kafka_producer_messages_total[5m])) * 100",
            "legendFormat": "Success Rate"
          }
        ],
        "colorValue": true,
        "colors": ["#d44a3a", "rgba(237, 129, 40, 0.89)", "#299c46"]
      },
      {
        "id": 4,
        "title": "Processing Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(kafka_consumer_latency_seconds_bucket[5m]))",
            "legendFormat": "{{topic}} - {{consumer_group}}"
          }
        ],
        "yAxes": [
          {
            "label": "Latency (seconds)"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    }
  }
}
```

## Logging Best Practices

### Structured Logging
```python
import logging
import json
from datetime import datetime
from typing import Dict, Any

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Create handler with structured format
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')  # We'll format in the adapter
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_event(self, level: int, event_type: str, details: Dict[str, Any] = None):
        """
        Log an event in structured JSON format.
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': logging.getLevelName(level),
            'event_type': event_type,
            'details': details or {}
        }

        self.logger.log(level, json.dumps(log_entry))

    def log_producer_event(self, topic: str, status: str, message_size: int, duration: float):
        """
        Log producer-specific events.
        """
        self.log_event(
            logging.INFO if status == 'success' else logging.WARNING,
            'producer_event',
            {
                'topic': topic,
                'status': status,
                'message_size_bytes': message_size,
                'duration_ms': duration * 1000,
                'component': 'producer'
            }
        )

    def log_consumer_event(self, topic: str, partition: int, offset: int,
                          status: str, duration: float, processing_time: float = None):
        """
        Log consumer-specific events.
        """
        details = {
            'topic': topic,
            'partition': partition,
            'offset': offset,
            'status': status,
            'duration_ms': duration * 1000,
            'component': 'consumer'
        }

        if processing_time:
            details['processing_time_ms'] = processing_time * 1000

        self.log_event(
            logging.INFO if status == 'success' else logging.ERROR,
            'consumer_event',
            details
        )

# Usage example
structured_logger = StructuredLogger('kafka-streaming')

# In producer/consumer code
def instrumented_produce(producer, topic: str, message: Dict[str, Any]):
    start_time = time.time()
    try:
        result = producer.send_with_metrics(topic, message)
        duration = time.time() - start_time
        message_size = len(str(message).encode('utf-8'))
        structured_logger.log_producer_event(topic, 'success', message_size, duration)
        return result
    except Exception as e:
        duration = time.time() - start_time
        structured_logger.log_producer_event(topic, 'error', 0, duration)
        raise
```

## Distributed Tracing

### OpenTelemetry Integration
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.kafka import KafkaInstrumentor
import json

# Initialize tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure exporter (to Jaeger, Zipkin, etc.)
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Instrument Kafka
KafkaInstrumentor().instrument()

def traced_message_processing(topic: str, message: Dict[str, Any]) -> bool:
    """
    Process a message with distributed tracing.
    """
    with tracer.start_as_current_span("process-message") as span:
        # Add attributes to the span
        span.set_attribute("messaging.system", "kafka")
        span.set_attribute("messaging.destination", topic)
        span.set_attribute("messaging.operation", "process")
        span.set_attribute("message.type", message.get("message_type", "unknown"))

        # Add correlation ID if available
        correlation_id = message.get("correlation_id")
        if correlation_id:
            span.set_attribute("correlation.id", correlation_id)

        try:
            # Process the message
            success = process_business_logic(message)

            if success:
                span.set_status(trace.Status(trace.StatusCode.OK))
            else:
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Business logic failed"))

            return success

        except Exception as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
```

This comprehensive monitoring and observability guide provides all the tools and patterns needed to maintain visibility into the Kafka-based event streaming system.