#!/bin/bash
# Setup script for Customer Success Agent

set -e  # Exit on any error

echo "Setting up Customer Success Agent..."

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
mkdir -p data

# Copy environment template if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Customer Success Agent Configuration
OPENAI_API_KEY=your_openai_api_key_here
REDIS_HOST=localhost
REDIS_PORT=6379

# Application settings
MODEL_NAME=gpt-4-turbo
DEBUG=False
LOG_LEVEL=INFO

# Security settings
JWT_SECRET_KEY=your_jwt_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here
EOF
    echo "Please update the .env file with your actual configuration values."
fi

echo "Setup complete!"
echo "To start the agent, run: python scripts/customer_success_agent.py"