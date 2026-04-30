#!/bin/bash
# Test runner script for comprehensive test execution

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
TEST_TYPE="all"
COVERAGE=false
VERBOSE=false
MARKERS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: ./run_tests.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -t, --type TYPE       Test type: all, unit, integration, e2e, social, webhook, feedback"
            echo "  -c, --coverage        Generate coverage report"
            echo "  -v, --verbose         Verbose output"
            echo "  -m, --markers MARKERS Custom pytest markers"
            echo "  -h, --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}=== Running Tests ===${NC}"
echo -e "Test type: ${YELLOW}${TEST_TYPE}${NC}"

# Build pytest command
PYTEST_CMD="pytest"

# Add test path based on type
case $TEST_TYPE in
    unit)
        PYTEST_CMD="$PYTEST_CMD tests/unit"
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD tests/integration"
        ;;
    e2e)
        PYTEST_CMD="$PYTEST_CMD tests/e2e"
        ;;
    social)
        PYTEST_CMD="$PYTEST_CMD -k 'linkedin or twitter or facebook'"
        ;;
    webhook)
        PYTEST_CMD="$PYTEST_CMD -k 'whatsapp or webhook'"
        ;;
    feedback)
        PYTEST_CMD="$PYTEST_CMD -k 'feedback or learning'"
        ;;
    all)
        PYTEST_CMD="$PYTEST_CMD tests/"
        ;;
esac

# Add coverage if requested
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=html --cov-report=term --cov-report=xml"
fi

# Add verbose if requested
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add custom markers if provided
if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD -m '$MARKERS'"
fi

# Add asyncio mode
PYTEST_CMD="$PYTEST_CMD --asyncio-mode=auto"

# Run tests
echo -e "${BLUE}Executing: ${PYTEST_CMD}${NC}"
echo ""

if eval $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}✓ Tests passed successfully${NC}"

    if [ "$COVERAGE" = true ]; then
        echo -e "${BLUE}Coverage report generated in htmlcov/index.html${NC}"
    fi

    exit 0
else
    echo ""
    echo -e "${RED}✗ Tests failed${NC}"
    exit 1
fi
