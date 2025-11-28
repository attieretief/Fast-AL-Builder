#!/bin/bash
# Test runner script for Fast-AL-Builder
# Usage: ./run-tests.sh [options]

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions
print_section() {
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    print_error "pytest not found. Installing dependencies..."
    pip install -r scripts/requirements.txt
fi

# Parse command line arguments
COVERAGE=false
PARALLEL=false
VERBOSE=false
SUITE="all"
MARK=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --parallel|-p)
            PARALLEL=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --unit)
            SUITE="unit"
            shift
            ;;
        --integration)
            SUITE="integration"
            shift
            ;;
        --e2e)
            SUITE="e2e"
            shift
            ;;
        --fast)
            MARK="not slow"
            shift
            ;;
        --help|-h)
            echo "Usage: ./run-tests.sh [options]"
            echo ""
            echo "Options:"
            echo "  --coverage, -c      Run with coverage reporting"
            echo "  --parallel, -p      Run tests in parallel"
            echo "  --verbose, -v       Verbose output"
            echo "  --unit             Run only unit tests"
            echo "  --integration      Run only integration tests"
            echo "  --e2e              Run only E2E tests"
            echo "  --fast             Skip slow tests"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run-tests.sh                    # Run all tests"
            echo "  ./run-tests.sh --coverage         # Run with coverage"
            echo "  ./run-tests.sh --parallel --fast  # Fast parallel tests"
            echo "  ./run-tests.sh --unit --verbose   # Verbose unit tests"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

# Add test suite
case $SUITE in
    unit)
        PYTEST_CMD="$PYTEST_CMD tests/unit/"
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD tests/integration/"
        ;;
    e2e)
        PYTEST_CMD="$PYTEST_CMD tests/e2e/"
        ;;
    all)
        PYTEST_CMD="$PYTEST_CMD tests/"
        ;;
esac

# Add options
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
fi

if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

if [ ! -z "$MARK" ]; then
    PYTEST_CMD="$PYTEST_CMD -m \"$MARK\""
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=scripts --cov-report=html --cov-report=term"
fi

# Print configuration
print_section "Test Configuration"
echo "Suite: $SUITE"
echo "Coverage: $COVERAGE"
echo "Parallel: $PARALLEL"
echo "Verbose: $VERBOSE"
[ ! -z "$MARK" ] && echo "Markers: $MARK"

# Run tests
print_section "Running Tests"
echo "Command: $PYTEST_CMD"
echo ""

if eval $PYTEST_CMD; then
    print_section "Test Results"
    print_success "All tests passed!"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        print_success "Coverage report generated in htmlcov/index.html"
        echo "Open with: open htmlcov/index.html (macOS) or xdg-open htmlcov/index.html (Linux)"
    fi
    
    exit 0
else
    print_section "Test Results"
    print_error "Some tests failed!"
    exit 1
fi
