#!/bin/bash
# Setup script for FastAPI project

set -e

PROJECT_NAME=$1

if [ -z "$PROJECT_NAME" ]; then
    echo "Usage: ./setup-fastapi.sh <project-name>"
    exit 1
fi

echo "Setting up FastAPI project: $PROJECT_NAME"

# Create project directory
mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME"

# Copy template files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/../assets/fastapi-template"

cp -r "$TEMPLATE_DIR"/* .

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate || . venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env
cp .env.example .env

echo "FastAPI project setup complete!"
echo "To start development:"
echo "  cd $PROJECT_NAME"
echo "  source venv/bin/activate  # or . venv/Scripts/activate on Windows"
echo "  python main.py"
