# Event Streaming Skill

This skill provides guidance and tools for implementing Kafka-based event streaming to decouple channel intake from agent processing. It manages producers, consumers, and message reliability across the processing pipeline.

## Overview

The event streaming system uses Apache Kafka to decouple various components of the CRM system, particularly to separate channel intake (email, WhatsApp, web forms) from agent processing. This architecture provides scalability, reliability, and fault tolerance.

## Components

### SKILL.md
Main skill file containing overview, core concepts, and implementation guidelines.

### Reference Files
- `PRODUCER_PATTERNS.md` - Producer implementation patterns
- `CONSUMER_PATTERNS.md` - Consumer implementation patterns
- `RELIABILITY_PATTERNS.md` - Message reliability patterns
- `MONITORING_GUIDE.md` - Monitoring and observability
- `SCALING_STRATEGIES.md` - Scaling strategies
- `SECURITY_BEST_PRACTICES.md` - Security implementation
- `FAULT_TOLERANCE.md` - Fault tolerance patterns

### Scripts
- `event_streaming_manager.py` - Complete event streaming management implementation

### Dependencies
- `requirements.txt` - Required Python packages

## Architecture

### Core Concepts
- **Producers**: Channel intake services publish messages to Kafka topics
- **Topics**: Logical channels for organizing different types of events
- **Consumers**: Agent processing services consume messages from topics
- **Brokers**: Kafka cluster managing message persistence and delivery
- **Partitions**: Horizontal scaling units within topics

### Topic Categories
1. **Ingestion Topics**:
   - `ingestion.raw.messages` - Raw messages from all channels
   - `ingestion.normalized.messages` - Normalized messages after processing

2. **Processing Topics**:
   - `processing.customer.identities` - Customer identity resolution events
   - `processing.tickets.in` - Incoming ticket creation requests
   - `processing.tickets.out` - Ticket status update events

3. **Notification Topics**:
   - `notifications.alerts` - System alerts and notifications
   - `notifications.audit` - Audit trail for compliance

## Usage

When implementing event streaming functionality:

1. Review the main `SKILL.md` for architectural guidance
2. Consult the relevant reference files for specific implementation details:
   - For producer patterns: `PRODUCER_PATTERNS.md`
   - For consumer patterns: `CONSUMER_PATTERNS.md`
   - For reliability: `RELIABILITY_PATTERNS.md`
   - For monitoring: `MONITORING_GUIDE.md`
   - For scaling: `SCALING_STRATEGIES.md`
   - For security: `SECURITY_BEST_PRACTICES.md`
   - For fault tolerance: `FAULT_TOLERANCE.md`
3. Use the example manager in `scripts/event_streaming_manager.py` as a starting point

## Implementation Steps

1. Set up Kafka cluster with appropriate topics
2. Implement secure producers for channel intake
3. Implement resilient consumers for agent processing
4. Configure monitoring and alerting
5. Set up security (authentication, encryption, ACLs)
6. Implement fault tolerance and disaster recovery

## Prerequisites

- Apache Kafka 2.8+
- Redis server (for caching and duplicate detection)
- Python 3.8+

## Running the Event Streaming Manager

1. Install dependencies: `pip install -r requirements.txt`
2. Set up your environment variables (see `.env` template)
3. Run the manager: `python scripts/event_streaming_manager.py`

The example demonstrates core event streaming operations including message publishing, consumer handling, and monitoring capabilities.