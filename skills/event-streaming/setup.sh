#!/bin/bash
# Setup script for Event Streaming System

set -e  # Exit on any error

echo "Setting up Event Streaming System..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate  # Use venv\Scripts\activate on Windows

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs
mkdir -p config

# Copy environment template if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Event Streaming System Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_URL=redis://localhost:6379

# Security settings
KAFKA_SECURITY_PROTOCOL=PLAINTEXT
KAFKA_SASL_MECHANISM=PLAIN
# KAFKA_USERNAME=your_username
# KAFKA_PASSWORD=your_password

# Encryption settings
ENCRYPTION_KEY=your_32_byte_base64_encoded_key_here

# Application settings
LOG_LEVEL=INFO
CONSUMER_GROUP_ID=event_streaming_demo

# Topic configuration
RAW_MESSAGES_TOPIC=ingestion.raw.messages
NORMALIZED_MESSAGES_TOPIC=ingestion.normalized.messages
CUSTOMER_IDENTITIES_TOPIC=processing.customer.identities
TICKETS_TOPIC=processing.tickets.in
ALERTS_TOPIC=notifications.alerts
EOF
    echo "Please update the .env file with your actual configuration values."
    echo "For ENCRYPTION_KEY, generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
fi

echo "Setup complete!"
echo "To run the Event Streaming Manager, activate your virtual environment and run: python scripts/event_streaming_manager.py"