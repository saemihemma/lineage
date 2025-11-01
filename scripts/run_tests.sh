#!/bin/bash
# Simple test runner for Unix/Mac
# Runs all unit tests and exits with appropriate exit code

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Run tests using Python's unittest discover
python3 -m unittest discover -v

# Exit with the test result code
exit $?

