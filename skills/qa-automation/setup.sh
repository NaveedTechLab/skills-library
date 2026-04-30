#!/bin/bash
# Setup script for QA Automation System

set -e  # Exit on any error

echo "Setting up QA Automation System..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate  # Use venv\Scripts\activate on Windows

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p test_reports
mkdir -p test_reports/unit
mkdir -p test_reports/integration
mkdir -p test_reports/e2e
mkdir -p test_reports/performance
mkdir -p test_reports/edge_case
mkdir -p test_reports/coverage

# Create example test directory structure if it doesn't exist
if [ ! -d "tests" ]; then
    echo "Creating example test directory structure..."
    mkdir -p tests/{unit,integration,e2e,performance,edge_cases}

    # Create basic conftest.py
    cat > tests/conftest.py << EOF
import pytest
import tempfile
import os

@pytest.fixture
def temp_file():
    """Create a temporary file for testing"""
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, "test_file.txt")
    with open(temp_path, 'w') as f:
        f.write("test content")
    yield temp_path
    os.remove(temp_path)
    os.rmdir(temp_dir)
EOF

    # Create basic pytest config
    cat > pytest.ini << EOF
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --strict-config
    --cov=myapp
    --cov-report=html:test_reports/coverage
    --junitxml=test_reports/junit.xml
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    performance: marks tests as performance tests
    edge_case: marks tests as edge case tests
filterwarnings =
    error
    ignore::DeprecationWarning
    ignore::UserWarning
EOF

    echo "Created example test structure in tests/"
fi

# Check if ChromeDriver is installed for Selenium tests
if ! command -v chromedriver &> /dev/null; then
    echo "ChromeDriver is not installed. For Selenium tests, please install ChromeDriver:"
    echo "Ubuntu/Debian: sudo apt-get install chromium-chromedriver"
    echo "macOS: brew install chromedriver"
    echo "Windows: Download from https://chromedriver.chromium.org/"
fi

# Check if required tools are available
if ! command -v python &> /dev/null; then
    echo "Python is not installed. Please install Python 3.8+."
    exit 1
fi

if ! command -v pip &> /dev/null; then
    echo "Pip is not installed. Please install pip."
    exit 1
fi

echo "Setup complete!"
echo "To run the QA Automation System, activate your virtual environment and run: python scripts/qa_automation_system.py"
echo "To run specific tests: python -m pytest tests/unit/"