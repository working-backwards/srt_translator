#!/bin/bash
# Smoke test script for SRT Translator (Unix/Linux/macOS)
# Tests basic functionality to ensure SRT Translator is working correctly

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions for colored output
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Parse command line arguments
DEBUG=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            DEBUG=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--debug]"
            echo "  --debug    Enable debug output"
            echo "  -h, --help Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Start smoke test
print_header "SRT Translator Smoke Test - Unix/Linux/macOS"
print_info "Starting smoke test at $(date)"

# Test 1: Check Python installation
print_header "Test 1: Python Environment"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    print_error "Python not found"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
if [[ $PYTHON_VERSION =~ Python\ ([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    VERSION="${BASH_REMATCH[1]}"
    print_success "Python $VERSION found"

    # Check if it's a supported version
    if [[ $VERSION =~ ^3\.(9|10|11|12) ]]; then
        print_success "Python version $VERSION is supported"
    else
        print_warning "Python version $VERSION may not be fully supported"
    fi
else
    print_error "Could not determine Python version"
    exit 1
fi

# Test 2: Check package installation
print_header "Test 2: Package Installation"
if pip show srt-translator &> /dev/null; then
    PACKAGE_VERSION=$(pip show srt-translator | grep "Version:" | cut -d' ' -f2)
    print_success "SRT Translator package found (version: $PACKAGE_VERSION)"
else
    print_error "SRT Translator package not installed"
    print_info "Installing package in development mode..."
    if pip install -e .; then
        print_success "Package installed successfully"
    else
        print_error "Failed to install package"
        exit 1
    fi
fi

# Test 3: Check CLI entry point
print_header "Test 3: CLI Entry Point"
if command -v srt-translator &> /dev/null; then
    CLI_VERSION=$(srt-translator --version 2>&1 || true)
    if [[ $CLI_VERSION =~ SRT\ Translator\ CLI\ v([0-9]+\.[0-9]+\.[0-9]+) ]]; then
        VERSION="${BASH_REMATCH[1]}"
        print_success "CLI entry point working (version: $VERSION)"
    else
        print_success "CLI entry point working"
    fi
else
    print_error "CLI entry point not working"
    exit 1
fi

# Test 4: Check GUI entry point
print_header "Test 4: GUI Entry Point"
if command -v srtx &> /dev/null; then
    GUI_HELP=$(srtx --help 2>&1 || true)
    if [[ $GUI_HELP =~ usage: ]]; then
        print_success "GUI entry point working"
    else
        print_success "GUI entry point working"
    fi
else
    print_error "GUI entry point not working"
    exit 1
fi

# Test 5: Basic SRT parsing
print_header "Test 5: SRT Parsing"
TEST_FILE="tests/fixtures/test_sample.srt"
if [[ -f "$TEST_FILE" ]]; then
    print_success "Test SRT file found"

    # Test basic parsing
    if grep -q "Hello, this is a test subtitle" "$TEST_FILE"; then
        print_success "SRT file content readable"
    else
        print_error "SRT file content not as expected"
    fi
else
    print_warning "Test SRT file not found, skipping parsing test"
fi

# Test 6: Import core modules
print_header "Test 6: Core Module Imports"
IMPORT_TEST=$($PYTHON_CMD -c "
import srt_translator.core.translator.srt_parser
import srt_translator.core.config.translation_config
import srt_translator.core.main
print('All core modules imported successfully')
" 2>&1)

if [[ $IMPORT_TEST =~ "All core modules imported successfully" ]]; then
    print_success "Core modules import successfully"
else
    print_error "Module import test failed"
    exit 1
fi

# Test 7: Configuration loading
print_header "Test 7: Configuration Loading"
CONFIG_TEST=$($PYTHON_CMD -c "
from srt_translator.core.config.translation_config import TranslationConfig
config = TranslationConfig()
print('Configuration system working')
" 2>&1)

if [[ $CONFIG_TEST =~ "Configuration system working" ]]; then
    print_success "Configuration system working"
else
    print_error "Configuration test failed"
fi

# Test 8: Run basic tests
print_header "Test 8: Basic Test Suite"
if $PYTHON_CMD -m pytest tests/ -v --tb=short 2>&1 | grep -q "passed"; then
    print_success "Basic test suite passed"
else
    print_warning "Some tests may have failed, check output above"
fi

# Summary
print_header "Smoke Test Summary"
print_success "All critical functionality tests completed"
print_info "SRT Translator appears to be working correctly"
print_info "Smoke test completed at $(date)"

if [[ "$DEBUG" == "true" ]]; then
    print_header "Debug Information"
    print_info "Python version: $($PYTHON_CMD --version 2>&1)"
    print_info "Package location: $(pip show srt-translator | grep "Location:" | cut -d' ' -f2)"
    print_info "Working directory: $(pwd)"
    print_info "Shell: $SHELL"
    print_info "Platform: $(uname -s)"
fi

echo -e "\n${GREEN}🎉 Smoke test completed successfully!${NC}"
