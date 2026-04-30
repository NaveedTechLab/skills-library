#!/bin/bash
# Setup script for Channel Ingestion Service

set -e  # Exit on any error

echo "Setting up Channel Ingestion Service..."

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
mkdir -p uploads

# Copy environment template if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Channel Ingestion Service Configuration
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_NUMBER=

GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=
GMAIL_ALLOWED_ADDRESSES=user@example.com

WEBHOOK_SECRET_KEY=
ENCRYPTION_KEY=

DEBUG=False
EOF
    echo "Please update the .env file with your actual configuration values."
fi

echo "Setup complete!"
echo "To start the service, run: python scripts/channel_ingestion_service.py"