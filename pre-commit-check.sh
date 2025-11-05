#!/bin/bash
# Pre-Commit Validation Script for LINEAGE Backend
#
# Run this before EVERY commit to ensure:
# - No backend errors (500s)
# - No Python exceptions in responses
# - Timer/progress bar mechanics work
# - All critical endpoints operational
#
# Usage: ./pre-commit-check.sh

set -e  # Exit on first error

echo "🧪 LINEAGE Pre-Commit Validation"
echo "================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    echo -e "${RED}❌ Error: Must run from project root directory${NC}"
    echo "   Current directory: $(pwd)"
    exit 1
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 not found${NC}"
    exit 1
fi

# Check if pytest is installed
if ! python3 -m pytest --version &> /dev/null; then
    echo -e "${RED}❌ Error: pytest not installed${NC}"
    echo "   Install with: pip3 install pytest"
    exit 1
fi

echo "📋 Running enhanced smoke tests..."
echo ""

# Run the critical endpoint tests
echo "1️⃣  Testing critical API endpoints for 500 errors..."
if python3 -m pytest backend/tests/test_smoke.py::TestCriticalEndpoints::test_all_critical_endpoints_return_success -v --tb=short 2>&1 | grep -q "PASSED"; then
    echo -e "   ${GREEN}✅ All critical endpoints passed${NC}"
else
    echo -e "   ${RED}❌ FAILED: Critical endpoints returning 500 errors${NC}"
    echo ""
    echo "   Run full output:"
    echo "   python3 -m pytest backend/tests/test_smoke.py::TestCriticalEndpoints::test_all_critical_endpoints_return_success -v -s"
    exit 1
fi

# Run the timer mechanics test
echo ""
echo "2️⃣  Testing timer/progress bar mechanics..."
if python3 -m pytest backend/tests/test_smoke.py::TestCriticalEndpoints::test_timer_mechanics_with_active_tasks -v --tb=short 2>&1 | grep -q "PASSED"; then
    echo -e "   ${GREEN}✅ Timer mechanics validated${NC}"
else
    echo -e "   ${RED}❌ FAILED: Timer mechanics broken${NC}"
    echo ""
    echo "   Run full output:"
    echo "   python3 -m pytest backend/tests/test_smoke.py::TestCriticalEndpoints::test_timer_mechanics_with_active_tasks -v -s"
    exit 1
fi

# Run the error keyword test
echo ""
echo "3️⃣  Checking for Python errors in API responses..."
if python3 -m pytest backend/tests/test_smoke.py::TestCriticalEndpoints::test_no_errors_in_response_bodies -v --tb=short 2>&1 | grep -q "PASSED"; then
    echo -e "   ${GREEN}✅ No error keywords found${NC}"
else
    echo -e "   ${RED}❌ FAILED: API responses contain Python errors${NC}"
    echo ""
    echo "   Run full output:"
    echo "   python3 -m pytest backend/tests/test_smoke.py::TestCriticalEndpoints::test_no_errors_in_response_bodies -v -s"
    exit 1
fi

# Run the golden path test (most important)
echo ""
echo "4️⃣  Running golden path smoke test (complete user journey)..."
if python3 -m pytest backend/tests/test_smoke.py::TestGoldenPath::test_complete_golden_path_from_scratch -v --tb=short 2>&1 | grep -q "PASSED"; then
    echo -e "   ${GREEN}✅ Golden path complete (game is playable)${NC}"
else
    echo -e "   ${RED}❌ FAILED: Golden path broken (game is unplayable!)${NC}"
    echo ""
    echo "   Run full output:"
    echo "   python3 -m pytest backend/tests/test_smoke.py::TestGoldenPath::test_complete_golden_path_from_scratch -v -s"
    exit 1
fi

# Run test coverage validation (suggestions only, non-blocking)
echo ""
echo "5️⃣  Checking if tests need updates based on code changes..."
if python3 scripts/validate_test_coverage.py --check 2>&1 | grep -q "TESTS THAT MAY NEED UPDATES"; then
    echo -e "   ${YELLOW}⚠️  Some tests may need updates - review suggestions above${NC}"
    echo ""
    echo "   Run: python3 scripts/validate_test_coverage.py --check"
    echo "   for detailed suggestions"
else
    echo -e "   ${GREEN}✅ Test coverage looks good${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ ALL PRE-COMMIT CHECKS PASSED!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   ✅ No 500 errors on critical endpoints"
echo "   ✅ Timer/progress bar mechanics working"
echo "   ✅ No Python exceptions in responses"
echo "   ✅ Golden path validated (game is playable)"
echo ""
echo "🚀 Safe to commit!"
echo ""
