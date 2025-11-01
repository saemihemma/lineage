# Testing Requirements for LINEAGE

**MANDATORY**: All unit tests must pass before pushing to `web-version` branch.

## Test Enforcement

### Before Every Push
```bash
python3 scripts/verify.py
```

This command:
- Runs all unit tests
- Verifies tests pass
- Should exit with code 0 (success) before pushing

### Test Requirements

1. **New Features MUST Have Tests**
   - When adding new game logic → Write tests
   - When adding new API endpoints → Write tests
   - When adding new UI components → Write component tests (if applicable)

2. **Bug Fixes SHOULD Have Tests**
   - Fix a bug → Add a test that would have caught it
   - Regression prevention

3. **Core Game Logic Always Has Tests**
   - `test_frontier.py` - Main game logic tests
   - `test_loading_screen.py` - UI component tests
   - Backend API tests in `backend/tests/`

## Test Structure

```
tests/
├── test_frontier.py          # Core game logic (resources, clones, expeditions)
├── test_loading_screen.py    # Loading screen UI tests
└── test_migrations.py        # State migration tests

backend/tests/
├── test_database.py         # Database operations
├── test_leaderboard.py      # Leaderboard API
└── test_telemetry.py        # Telemetry API
```

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

### Core Game Logic ✅
- Resource gathering
- Clone growing
- Expeditions
- Upload mechanics
- SELF evolution

### UI Components ✅
- Loading screen
- Name input
- Progress bar

### Backend API ✅
- Leaderboard endpoints
- Telemetry endpoints
- Game state management

### Missing Tests (To Be Added)
- Frontend React components (Jest/React Testing Library)
- Integration tests (end-to-end game flow)
- API endpoint response validation

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
1. ✅ Run `python3 scripts/verify.py`
2. ✅ All tests must pass
3. ✅ Fix any failing tests
4. ✅ Then push: `git push origin web-version`

**If tests fail:**
- Don't push
- Fix the issues
- Run tests again
- Then push

