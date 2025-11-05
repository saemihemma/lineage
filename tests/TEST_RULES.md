# Test Rules and Guidelines

Rules for when tests are required, how to categorize them, and when to update vs create new tests.

## When Tests Are Required

### Always Required

**Critical Path Changes:**
- Changes to `backend/routers/game.py` → Update `test_smoke.py` and `test_critical_path.py`
- Changes to `backend/engine/outcomes.py` → Update `test_game.py` and `test_smoke.py`
- Changes to `game/rules.py` → Update `test_game.py` and `test_smoke.py`

**Security Changes:**
- Changes to `backend/middleware/csrf.py` → Update `test_csrf.py` and `test_security.py`
- Changes to `core/anticheat.py` → Update `test_anticheat.py` and `test_security.py`

### Should Have Tests

**Game Logic Changes:**
- Changes to `config/gameplay.json` → Update `test_game.py` (adjust expected values)
- New game mechanics → Add to `test_game.py` or create new test file
- Balance changes → Update `test_game.py` expected values

**Infrastructure Changes:**
- Changes to `backend/database.py` → Update `test_database.py` and `test_database_resilience.py`
- Changes to `backend/routers/leaderboard.py` → Update `test_leaderboard.py`
- New API endpoints → Add to `test_critical_path.py` and `test_smoke.py` if critical

### Optional But Recommended

**Frontend Changes:**
- React component changes → Add frontend tests (currently missing)
- UI logic changes → Add component tests

**State Management:**
- State schema changes → Update `tests/test_migrations.py`
- localStorage changes → Add tests for state persistence

## Test Categories

### Critical (Must Pass Before Commit)
- `test_smoke.py` - Golden path, complete user journey
- `test_critical_path.py` - Critical API endpoints
- `test_security.py` - Security validations
- `test_csrf.py` - CSRF protection
- `test_anticheat.py` - Anti-cheat

### Game Logic (Should Pass Before Push)
- `test_game.py` - Core game mechanics
- `test_game_integration.py` - Integration tests
- `test_property_timers.py` - Property-based validation
- `test_expedition_count.py` - Expedition mechanics

### Infrastructure (Should Pass Before Push)
- `test_database.py` - Database operations
- `test_database_resilience.py` - DB error handling
- `test_leaderboard.py` - Leaderboard API
- `test_telemetry.py` - Telemetry API

### Regression (Run in CI)
- `test_bugfixes.py` - Bug fix validations
- `test_regression_bugs.py` - Regression prevention

## Test Naming Conventions

### Test Files
- Pattern: `test_<category>_<feature>.py` or `test_<feature>.py`
- Examples: `test_smoke.py`, `test_game.py`, `test_csrf.py`

### Test Classes
- Pattern: `Test<FeatureName>` or `Test<Category><Feature>`
- Examples: `TestGoldenPath`, `TestCriticalEndpoints`, `TestDatabaseConnection`

### Test Functions
- Pattern: `test_<what>_<expected_result>`
- Examples: `test_gather_resource_adds_to_inventory`, `test_expedition_returns_signature`

## When to Update vs Create New Tests

### Update Existing Tests When:
- Fixing a bug → Add a test case that would have caught it
- Changing expected behavior → Update assertions in existing tests
- Refactoring → Update test setup/mocks to match new structure
- Balance changes → Update expected values in `test_game.py`

### Create New Tests When:
- Adding new feature → Create new test file or add to relevant category
- New edge case discovered → Add test case to appropriate file
- New security concern → Add to `test_security.py` or create dedicated file

## Test Validation

Use the test coverage validation script to check if tests need updates:

```bash
# Check mode (suggestions only)
python scripts/validate_test_coverage.py --check

# Enforce mode (block commit if tests missing)
python scripts/validate_test_coverage.py --enforce
```

The script analyzes git diff and suggests which tests should be updated based on `tests/test_map.json`.

## Best Practices

1. **One Assertion Per Test** (when possible)
2. **Clear Test Names**: Describe what is being tested and expected result
3. **Isolate Tests**: Each test should be independent
4. **Test Edge Cases**: Empty states, invalid inputs, boundaries
5. **Fast Tests**: Unit tests should run quickly (<1 second each)
6. **Use Fixtures**: Share common setup via pytest fixtures
7. **Mock External Dependencies**: Database, APIs, time-dependent logic

## Test Coverage Goals

- **Critical Path**: 100% coverage (golden path must always work)
- **Security**: 100% coverage (all security features must be tested)
- **Game Logic**: 80%+ coverage (core mechanics should be well tested)
- **Infrastructure**: 70%+ coverage (database, APIs should be tested)

## Suspect/Failing Tests

If a test is failing but the build is stable (code works correctly):

1. **Mark as SUSPECT**: Add `@pytest.mark.skip(reason="SUSPECT: ...")` with clear reason
2. **Document Issue**: Add TODO comment explaining what needs fixing
3. **Fix Test Setup**: If test setup is incorrect, fix it rather than skipping
4. **Remove Skip**: Once fixed, remove skip decorator

Tests should be suspect only when:
- Test setup is incorrect (not code issue)
- Test is outdated (functionality changed but test wasn't updated)
- Test is flaky (non-deterministic, needs fixing)

Never mark tests as suspect just because they fail - fix the underlying issue.

