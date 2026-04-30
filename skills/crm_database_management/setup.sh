#!/bin/bash
# Setup script for CRM Database Management

set -e  # Exit on any error

echo "Setting up CRM Database Management..."

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
# CRM Database Management Configuration
DATABASE_URL=postgresql://username:password@localhost/crm_db
REDIS_URL=redis://localhost:6379

# Security settings
FIELD_ENCRYPTION_KEY=your_32_byte_base64_encoded_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# Application settings
LOG_LEVEL=INFO
DEBUG=False

# PostgreSQL settings
PGVECTOR_AVAILABLE=True
EOF
    echo "Please update the .env file with your actual configuration values."
    echo "For FIELD_ENCRYPTION_KEY, generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
fi

echo "Setup complete!"
echo "To run the CRM Database Manager, activate your virtual environment and run: python scripts/crm_database_manager.py"