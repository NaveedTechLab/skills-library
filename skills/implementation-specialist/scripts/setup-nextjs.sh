#!/bin/bash
# Setup script for Next.js project

set -e

PROJECT_NAME=$1

if [ -z "$PROJECT_NAME" ]; then
    echo "Usage: ./setup-nextjs.sh <project-name>"
    exit 1
fi

echo "Setting up Next.js project: $PROJECT_NAME"

# Create project directory
mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME"

# Copy template files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/../assets/nextjs-template"

cp -r "$TEMPLATE_DIR"/* .
cp -r "$TEMPLATE_DIR"/.[!.]* . 2>/dev/null || true

# Install dependencies
npm install

echo "Next.js project setup complete!"
echo "To start development:"
echo "  cd $PROJECT_NAME"
echo "  npm run dev"
