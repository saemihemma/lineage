# Testing Requirements for LINEAGE

**MANDATORY**: All unit tests must pass before pushing to `web-version` branch.

## Test Enforcement

### Before Every Push
```bash
python3 scripts/verify.py
```

This command:
- Runs all backend unit tests
- Verifies frontend TypeScript compilation and build
- Catches unused variables, type errors, and build failures
- Should exit with code 0 (success) before pushing

**What it checks:**
1. ✅ Backend Python unit tests (`test_*.py`)
2. ✅ Frontend TypeScript compilation (`npm run build`)
3. ✅ No unused variables or type errors

### Test Requirements

1. **New Features MUST Have Tests**
   - When adding new game logic → Write tests
   - When adding new API endpoints → Write tests
   - When adding new UI components → Write component tests (if applicable)

2. **Bug Fixes SHOULD Have Tests**
   - Fix a bug → Add a test that would have caught it
   - Regression prevention

3. **Core Game Logic Always Has Tests**
   - `backend/tests/test_game.py` - Core game logic tests
   - `backend/tests/test_smoke.py` - Golden path smoke tests
   - Backend API tests in `backend/tests/`

## Test Structure

```
backend/tests/
├── test_smoke.py              # Golden path smoke tests (CRITICAL - must pass)
├── test_critical_path.py      # Critical API endpoints (CRITICAL)
├── test_user_journey.py       # End-to-end user journeys
├── test_game.py               # Core game logic and mechanics
├── test_game_integration.py   # Integration tests
├── test_property_timers.py    # Property-based timer validation
├── test_expedition_count.py   # Expedition mechanics
├── test_security.py           # Security validations (CRITICAL)
├── test_csrf.py               # CSRF protection (CRITICAL)
├── test_anticheat.py          # Anti-cheat HMAC signing (CRITICAL)
├── test_database.py           # Database operations
├── test_database_resilience.py # DB error handling
├── test_leaderboard.py        # Leaderboard API
├── test_telemetry.py          # Telemetry API
├── test_bugfixes.py           # Bug fix validations
└── test_regression_bugs.py    # Regression prevention

tests/
└── test_migrations.py         # State migration tests
```

**Frontend Tests**: Currently missing - add React component tests using Jest/React Testing Library

## Running Tests

### Run All Tests
```bash
python3 scripts/verify.py
```

### Run Specific Test File
```bash
python3 -m unittest test_frontier.py -v
python3 -m unittest test_loading_screen.py -v
```

### Run Backend Tests
```bash
cd backend && python3 -m pytest tests/ -v
# Or with unittest:
python3 -m unittest discover -v backend/tests/
```

## Writing New Tests

### Example: Testing Game Logic
```python
import unittest
from game.rules import gather_resource
from game.state import GameState

class TestNewFeature(unittest.TestCase):
    def test_new_feature_works(self):
        state = GameState()
        # Test the feature
        result = your_new_function(state)
        # Assert expected behavior
        self.assertEqual(result, expected_value)
```

### Example: Testing API Endpoint
```python
import unittest
from fastapi.testclient import TestClient
from backend.main import app

class TestNewEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
    
    def test_new_endpoint(self):
        response = self.client.post("/api/game/new-endpoint")
        self.assertEqual(response.status_code, 200)
```

## CI/CD Integration (Future)

When setting up CI/CD:
- Tests run automatically on every push
- Push blocked if tests fail
- See `.github/workflows/` (to be created)

## Current Test Coverage

### Critical Path Tests ✅
- Golden path smoke tests (complete user journey)
- Critical API endpoints (no 500 errors)
- End-to-end user journeys

### Security Tests ✅
- CSRF protection
- Anti-cheat HMAC signing
- Security validations

### Game Logic Tests ✅
- Core game mechanics
- Game rules and state management
- Integration tests
- Property-based timer validation
- Expedition mechanics

### Infrastructure Tests ✅
- Database operations
- Database resilience (error handling)
- Leaderboard API
- Telemetry API

### Regression Tests ✅
- Bug fix validations
- Regression prevention

### Missing Tests
- **Frontend React components** (Jest/React Testing Library) - Priority: High
- End-to-end browser tests (Playwright/Cypress) - Priority: Medium
- Performance/load tests - Priority: Low
- Accessibility tests - Priority: Low

## Test Validation

### Test Coverage Validation

Use the test coverage validation script to check if code changes require test updates:

```bash
# Check mode (suggestions only, non-blocking)
python scripts/validate_test_coverage.py --check

# Enforce mode (block commit if tests missing, blocking)
python scripts/validate_test_coverage.py --enforce
```

The script analyzes git diff and suggests which tests should be updated based on `tests/test_map.json`.

### Test Mapping

See `tests/test_map.json` for mapping between code paths and required test files.

**Example**: Changes to `backend/routers/game.py` require updates to:
- `backend/tests/test_smoke.py`
- `backend/tests/test_critical_path.py`
- `backend/tests/test_game.py`

## Test Documentation

- **`tests/TEST_RULES.md`** - Rules for when tests are required
- **`tests/TEST_INVENTORY.md`** - Complete inventory of all test files
- **`tests/test_map.json`** - Code-to-test mapping configuration

## Test Best Practices

1. **One Assertion Per Test** (when possible)
2. **Clear Test Names**: `test_gather_resource_adds_to_inventory`
3. **Isolate Tests**: Each test should be independent
4. **Test Edge Cases**: Empty states, invalid inputs, boundaries
5. **Fast Tests**: Unit tests should run quickly (<1 second each)

## Troubleshooting

### "Tests pass locally but fail in CI"
- Check Python version differences
- Check environment variables
- Check import paths

### "Test is flaky"
- Check for time-dependent logic (use mocks)
- Check for race conditions
- Check for shared state between tests

### "Can't run tests"
```bash
# Install test dependencies
pip install -r requirements.txt

# Make sure you're in project root
pwd  # Should show .../frontier_ui_package_v4
```

## Enforcement Reminder

**Before pushing to production:**
1. ✅ Run critical smoke tests: `python3 -m pytest backend/tests/test_smoke.py -v`
2. ✅ Run test coverage validation: `python scripts/validate_test_coverage.py --check`
3. ✅ All critical tests must pass
4. ✅ Review suggested test updates
5. ✅ Fix any failing tests
6. ✅ Then push: `git push origin web-version`

**If tests fail:**
- Don't push
- Fix the issues
- Run tests again
- Then push

**Pre-commit Hook:**
The pre-commit hook automatically runs smoke tests. If they fail, your commit will be blocked (unless using `--no-verify`).

