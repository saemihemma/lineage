#!/bin/bash
#
# Pre-commit hook: Run smoke tests before allowing commit
#
# This ensures that critical user journeys (golden path) never break.
# Smoke tests validate the complete game loop: session → gather → build → expedition → upload
#
# To skip this hook (emergency only):
#   git commit --no-verify -m "emergency: skip smoke tests"
#
# To run manually:
#   python3 -m pytest backend/tests/test_smoke.py -v

set -e  # Exit on any error

echo "🧪 Running smoke tests before commit..."
echo ""

# Check if pytest is available
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: python3 not found. Install Python 3.11+ to run smoke tests."
    exit 1
fi

# Check if pytest is installed
if ! python3 -m pytest --version &> /dev/null; then
    echo "⚠️  WARNING: pytest not installed. Installing dependencies..."
    if [ -f "requirements.txt" ]; then
        python3 -m pip install -q -r requirements.txt
    elif [ -f "backend/requirements.txt" ]; then
        python3 -m pip install -q -r backend/requirements.txt
    else
        echo "❌ ERROR: No requirements.txt found. Cannot install pytest."
        exit 1
    fi
fi

# Set test environment variables
export DATABASE_URL="sqlite:///./test_lineage_precommit.db"
export HMAC_SECRET_KEY_V1="test-secret-key-precommit"
export CSRF_SECRET_KEY="test-csrf-secret-precommit"

# Run smoke tests
echo "Running: python3 -m pytest backend/tests/test_smoke.py -v"
echo ""

if python3 -m pytest backend/tests/test_smoke.py -v --tb=short; then
    echo ""
    echo "✅ Smoke tests passed! Proceeding with commit..."
    # Clean up test database
    rm -f test_lineage_precommit.db
    exit 0
else
    echo ""
    echo "❌ ERROR: Smoke tests FAILED!"
    echo ""
    echo "Your commit was blocked because smoke tests failed."
    echo "This means a critical user journey is broken."
    echo ""
    echo "Please fix the failing tests before committing."
    echo "To see full error output, run:"
    echo "  python3 -m pytest backend/tests/test_smoke.py -v"
    echo ""
    echo "To skip this hook (EMERGENCY ONLY):"
    echo "  git commit --no-verify -m 'emergency: skip smoke tests'"
    echo ""
    # Clean up test database
    rm -f test_lineage_precommit.db
    exit 1
fi

