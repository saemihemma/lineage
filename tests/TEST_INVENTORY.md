# Test Inventory

Complete inventory of all test files in the LINEAGE codebase.

## Backend Tests (16 files, ~74 test classes/functions)

### Critical Path Tests

**`backend/tests/test_smoke.py`** (3 tests)
- **Purpose**: Golden path smoke tests - complete user journey
- **Category**: Critical
- **Must Pass**: Yes (pre-commit)
- **Description**: Tests the complete user journey: gather → build → grow → expedition → upload
- **Last Updated**: 2024 (localStorage-based state management)

**`backend/tests/test_critical_path.py`** (4 tests)
- **Purpose**: Critical API endpoints validation
- **Category**: Critical
- **Must Pass**: Yes (pre-commit)
- **Description**: Ensures no 500 errors on critical endpoints

**`backend/tests/test_user_journey.py`** (5 tests)
- **Purpose**: End-to-end user journey tests
- **Category**: Critical
- **Must Pass**: No
- **Description**: Extended user journey scenarios

### Security Tests

**`backend/tests/test_security.py`** (9 tests)
- **Purpose**: Security validations
- **Category**: Security
- **Must Pass**: Yes (pre-commit)
- **Description**: General security checks

**`backend/tests/test_csrf.py`** (3 tests)
- **Purpose**: CSRF protection
- **Category**: Security
- **Must Pass**: Yes (pre-commit)
- **Description**: CSRF token validation and protection

**`backend/tests/test_anticheat.py`** (5 tests)
- **Purpose**: Anti-cheat HMAC signing and anomaly detection
- **Category**: Security
- **Must Pass**: Yes (pre-commit)
- **Description**: Validates expedition outcome signatures and anomaly detection

### Functional Tests

**`backend/tests/test_game.py`** (9 tests)
- **Purpose**: Core game logic and mechanics
- **Category**: Game Logic
- **Must Pass**: No
- **Description**: Tests game rules, state management, and mechanics

**`backend/tests/test_game_integration.py`** (4 tests)
- **Purpose**: Integration tests
- **Category**: Game Logic
- **Must Pass**: No
- **Description**: Integration between game components

**`backend/tests/test_property_timers.py`** (4 tests)
- **Purpose**: Property-based timer validation
- **Category**: Game Logic
- **Must Pass**: No
- **Description**: Validates timer invariants using property-based testing

**`backend/tests/test_expedition_count.py`** (1 test)
- **Purpose**: Expedition mechanics
- **Category**: Game Logic
- **Must Pass**: No
- **Description**: Tests expedition counting and mechanics

### Infrastructure Tests

**`backend/tests/test_database.py`** (4 tests)
- **Purpose**: Database operations
- **Category**: Infrastructure
- **Must Pass**: No
- **Description**: Database connection and query tests

**`backend/tests/test_database_resilience.py`** (4 tests)
- **Purpose**: DB error handling and resilience
- **Category**: Infrastructure
- **Must Pass**: No
- **Description**: Tests database error handling and graceful degradation

**`backend/tests/test_leaderboard.py`** (4 tests)
- **Purpose**: Leaderboard API
- **Category**: Infrastructure
- **Must Pass**: No
- **Description**: Leaderboard endpoint tests

**`backend/tests/test_telemetry.py`** (3 tests)
- **Purpose**: Telemetry API
- **Category**: Infrastructure
- **Must Pass**: No
- **Description**: Telemetry endpoint tests

### Regression Tests

**`backend/tests/test_bugfixes.py`** (8 tests)
- **Purpose**: Bug fix validations
- **Category**: Regression
- **Must Pass**: No
- **Description**: Tests that validate bug fixes

**`backend/tests/test_regression_bugs.py`** (4 tests)
- **Purpose**: Regression prevention
- **Category**: Regression
- **Must Pass**: No
- **Description**: Tests that prevent regressions

## Legacy Tests

**`tests/test_migrations.py`**
- **Purpose**: State migration tests
- **Category**: Game Logic
- **Must Pass**: No
- **Description**: Tests game state version migrations

## Frontend Tests

**Status**: Missing
- No frontend tests found
- **Recommendation**: Add React component tests using Jest/React Testing Library

## Test Coverage Summary

- **Total Test Files**: 17 (16 backend + 1 legacy)
- **Total Test Classes/Functions**: ~74
- **Critical Tests**: 5 files (must pass before commit)
- **Security Tests**: 3 files (must pass before commit)
- **Game Logic Tests**: 5 files
- **Infrastructure Tests**: 4 files
- **Regression Tests**: 2 files

## Test Coverage Gaps

1. **Frontend Tests**: No React component tests
2. **E2E Tests**: No end-to-end browser tests
3. **Performance Tests**: No performance/load tests
4. **Accessibility Tests**: No a11y tests

## Maintenance

This inventory should be updated when:
- New test files are added
- Test files are removed
- Test counts change significantly

Use `find backend/tests -name "test_*.py" -exec sh -c 'echo "=== {} ===" && grep -c "^def test_\|^class Test" {}' \;` to regenerate test counts.

