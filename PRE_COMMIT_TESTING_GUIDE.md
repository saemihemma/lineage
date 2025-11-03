# Pre-Commit Testing Guide for LINEAGE

## 🚨 CRITICAL: Always Run Before Committing!

**This document is for:**
- Claude (AI backend developer)
- Cursor (AI frontend developer)
- ChatGPT (AI assistant)
- Human developers

**Purpose:** Ensure no broken code enters the repository.

---

## Quick Start (TL;DR)

Before **EVERY commit**, run:

```bash
./pre-commit-check.sh
```

If it passes ✅, you can commit. If it fails ❌, **DO NOT COMMIT** until fixed.

---

## Why Pre-Commit Testing?

### The Problem We Solve

Without automated pre-commit checks, we risk:

1. **500 Errors in Production** - Backend crashes that break the game
2. **Timer/Progress Bar Failures** - UI shows "Loading..." forever
3. **Silent Errors** - Python exceptions leaked into JSON responses
4. **Broken Game Loop** - Users can't complete core gameplay

### Real Example (What We Caught)

**Before enhanced smoke tests:**
```bash
# Backend server was returning 500 error
GET /api/game/debug/upload_breakdown
→ 500 Internal Server Error
→ AttributeError: type object 'GameState' has no attribute 'from_dict'
```

**Problem:** The server was running old code with a bug. Without automated testing, this would have been committed and deployed!

**After enhanced smoke tests:**
```bash
./pre-commit-check.sh
→ ❌ FAILED: Critical endpoints returning 500 errors
→ Commit blocked until fixed ✅
```

---

## The Pre-Commit Validation Script

### What It Tests

The script runs **4 critical tests** in order:

#### 1. **Critical API Endpoints** (No 500 Errors)
Tests all essential endpoints for backend crashes:
- `/api/config/gameplay` - Config endpoint
- `/api/game/time` - Server time sync
- `/api/game/debug/upload_breakdown` - Upload formula
- `/api/game/state` - Game state
- `/api/leaderboard` - Leaderboard
- `/api/health` - Health check

**What it catches:**
- Import errors (missing modules)
- AttributeErrors (wrong method calls)
- Database errors
- Syntax errors

#### 2. **Timer/Progress Bar Mechanics**
Tests that timers work correctly:
- Womb build starts a timer
- Timer has `start_time`, `duration`, `type`
- `/api/game/tasks/status` returns progress
- Elapsed time is calculated correctly

**What it catches:**
- Progress bars stuck at 0%
- Timers not starting
- Task status endpoint broken
- Elapsed time calculation errors

#### 3. **No Python Errors in Responses**
Scans API responses for error keywords:
- `Traceback`
- `Exception`
- `AttributeError`
- `KeyError`
- `TypeError`

**What it catches:**
- Unhandled exceptions serialized into JSON
- Stack traces leaked to frontend
- Debug info exposed to users

#### 4. **Golden Path (Complete User Journey)**
Tests the full game loop end-to-end:
1. Create session → Get session_id + CSRF token
2. Gather resources (Tritanium, Metal Ore, Biomass)
3. Build Womb → Start construction task
4. Grow clone → Assign traits and XP
5. Apply clone to spaceship
6. Run MINING expedition → Gain XP + resources
7. Upload clone to SELF → Gain soul XP

**What it catches:**
- Any step in core gameplay broken
- Security features (HMAC, CSRF) not working
- Game state corruption
- Resource/XP calculation errors

---

## How to Use

### For Claude (Backend Developer)

**Before committing backend changes:**

```bash
# 1. Make your code changes
vim backend/routers/game.py

# 2. Run pre-commit check
./pre-commit-check.sh

# 3. If it passes, commit
git add backend/
git commit -m "fix: correct upload formula calculation"
git push
```

**If the check fails:**

```bash
# 1. Read the error output carefully
./pre-commit-check.sh
# → ❌ FAILED: Critical endpoints returning 500 errors
#    Run full output:
#    python3 -m pytest backend/tests/test_smoke.py::TestCriticalEndpoints::test_all_critical_endpoints_return_success -v -s

# 2. Run the detailed test output
python3 -m pytest backend/tests/test_smoke.py::TestCriticalEndpoints::test_all_critical_endpoints_return_success -v -s

# 3. Fix the error
# 4. Re-run pre-commit check
./pre-commit-check.sh

# 5. Once it passes, commit
```

**Common Backend Errors:**

| Error | Cause | Fix |
|-------|-------|-----|
| `AttributeError: 'GameState' has no attribute 'from_dict'` | Wrong deserialization method | Use `dict_to_game_state()` instead |
| `500 Internal Server Error` | Unhandled exception | Add try/except or fix logic |
| `KeyError: 'clones'` | Missing state field | Check state structure |
| `ImportError: No module named 'X'` | Missing dependency | Add to requirements.txt |

### For Cursor (Frontend Developer)

**Before committing frontend changes:**

```bash
# 1. Make your frontend changes
vim frontend/src/components/LeaderboardDialog.tsx

# 2. Run backend smoke tests (ensure API compatibility)
./pre-commit-check.sh

# 3. If it passes, commit
git add frontend/
git commit -m "feat: add expedition count to leaderboard"
git push
```

**Why frontend devs should run backend tests:**
- Ensures frontend changes don't break API calls
- Validates CSRF token handling
- Confirms timer/progress bar UI has working backend
- Catches cookie/session issues

### For All Developers

**When to run pre-commit checks:**

✅ **ALWAYS run before:**
- Committing code
- Creating a pull request
- Merging branches
- Deploying to production
- Tagging a release

❌ **Don't skip if:**
- "It's just a small change" - Small changes can break big things
- "I'm in a hurry" - Broken code wastes more time than testing
- "Tests are slow" - Tests run in <5 seconds
- "I only changed frontend" - Frontend changes affect API calls

---

## Detailed Test Documentation

### Test File Location

All smoke tests are in:
```
backend/tests/test_smoke.py
```

### Test Classes

#### `TestGoldenPath`
**Purpose:** Validate complete user journey
**Tests:**
- `test_complete_golden_path_from_scratch` - Full game loop
- `test_multiple_expeditions_same_clone` - Expedition count tracking
- `test_different_expedition_types` - MINING/COMBAT/EXPLORATION

#### `TestCriticalEndpoints`
**Purpose:** Catch backend errors before commit
**Tests:**
- `test_all_critical_endpoints_return_success` - No 500 errors
- `test_timer_mechanics_with_active_tasks` - Progress bar validation
- `test_no_errors_in_response_bodies` - No Python tracebacks

### Running Individual Tests

```bash
# Run all smoke tests
python3 -m pytest backend/tests/test_smoke.py -v

# Run only golden path
python3 -m pytest backend/tests/test_smoke.py::TestGoldenPath -v

# Run only critical endpoint tests
python3 -m pytest backend/tests/test_smoke.py::TestCriticalEndpoints -v

# Run specific test with detailed output
python3 -m pytest backend/tests/test_smoke.py::TestCriticalEndpoints::test_all_critical_endpoints_return_success -v -s
```

### Test Output Example

**Success:**
```bash
🔍 Testing critical endpoints for errors...
   Testing GET /api/config/gameplay...
   ✅ /api/config/gameplay returned 200
   Testing GET /api/game/time...
   ✅ /api/game/time returned 200

✅ All 8 critical endpoints passed!
```

**Failure:**
```bash
🔍 Testing critical endpoints for errors...
   Testing GET /api/game/debug/upload_breakdown...
   ❌ FAILED: /api/game/debug/upload_breakdown returned 500

❌ CRITICAL ENDPOINTS FAILING WITH 500 ERRORS:

/api/game/debug/upload_breakdown (Upload breakdown):
  Error: AttributeError: type object 'GameState' has no attribute 'from_dict'
```

---

## Integration with CI/CD

### GitHub Actions

The smoke tests run automatically on:
- Every push to main/web-version/feature/* branches
- Every pull request to main/web-version

**CI Configuration:** `.github/workflows/test.yml`

```yaml
- name: Golden Path Critical Test
  run: python -m pytest backend/tests/test_smoke.py::TestGoldenPath::test_complete_golden_path_from_scratch -v

- name: Critical Endpoints Test
  run: python -m pytest backend/tests/test_smoke.py::TestCriticalEndpoints -v
```

### Pre-Commit Hooks (Optional)

For automatic enforcement, install Git pre-commit hook:

```bash
# Copy pre-commit script to Git hooks
cp pre-commit-check.sh .git/hooks/pre-commit

# Now tests run automatically on every commit
git commit -m "feat: add new feature"
# → Runs ./pre-commit-check.sh automatically
# → Blocks commit if tests fail
```

---

## Troubleshooting

### "Command not found: python"

**Solution:**
```bash
# Use python3 instead
python3 -m pytest backend/tests/test_smoke.py -v
```

### "pytest not installed"

**Solution:**
```bash
pip3 install pytest
# or
pip3 install -r requirements.txt
```

### "Tests are slow"

**Normal runtime:** <5 seconds for all 4 checks

If tests take >10 seconds, check:
- Database file is not corrupted
- No other server running on port 8000
- Enough disk space for test database

### "Tests pass locally but fail in CI"

**Common causes:**
1. **Environment variables missing** - Check CI env vars match local
2. **Database URL different** - CI uses different DATABASE_URL
3. **Python version mismatch** - CI uses Python 3.11, local uses 3.12
4. **Dependencies not installed** - Check requirements.txt in CI

**Solution:**
```bash
# Test with same Python version as CI
python3.11 -m pytest backend/tests/test_smoke.py -v

# Test with CI environment variables
export DATABASE_URL="sqlite:///./test_lineage.db"
./pre-commit-check.sh
```

---

## Best Practices

### For Claude (AI Backend Developer)

1. **Always test after code changes**
   ```bash
   # Edit code
   vim backend/routers/game.py

   # Test immediately
   ./pre-commit-check.sh
   ```

2. **Read error messages carefully**
   - Error messages show exact endpoint + error type
   - Run suggested pytest command for full traceback
   - Fix root cause, not symptoms

3. **Test both happy path and edge cases**
   ```bash
   # Run all tests (not just smoke tests)
   python3 -m pytest backend/tests/ -v
   ```

4. **Never commit with failing tests**
   - If stuck, ask user for help
   - Don't disable or skip tests
   - Don't commit with `# TODO: fix test`

### For Cursor (AI Frontend Developer)

1. **Verify API compatibility**
   ```bash
   # After changing frontend API calls
   ./pre-commit-check.sh
   ```

2. **Check CSRF token handling**
   - Golden path test validates CSRF protection
   - Ensure X-CSRF-Token header is sent
   - Confirm csrf_token cookie is read correctly

3. **Test timer UI integration**
   - Timer test validates `/api/game/tasks/status`
   - Ensure frontend polls this endpoint
   - Verify progress bar updates correctly

### For All Developers

1. **Run tests before git push** (not just before commit)
2. **Add tests for new features** (don't just test, enhance tests)
3. **Keep tests fast** (<5 seconds total)
4. **Document test failures** (add to this guide)

---

## Test Coverage

Current smoke test coverage:

| Feature | Covered | Test |
|---------|---------|------|
| Session creation | ✅ | Golden path |
| Resource gathering | ✅ | Golden path |
| Womb construction | ✅ | Golden path + Timer test |
| Clone growth | ✅ | Golden path |
| Clone application | ✅ | Golden path |
| Expeditions (MINING) | ✅ | Golden path |
| Expeditions (COMBAT/EXPLORATION) | ✅ | Expedition types test |
| Clone upload | ✅ | Golden path |
| SELF XP progression | ✅ | Golden path |
| HMAC anti-cheat | ✅ | Golden path (signature check) |
| CSRF protection | ✅ | Golden path (token check) |
| Timer mechanics | ✅ | Timer test |
| Config endpoint | ✅ | Critical endpoints test |
| Time endpoint | ✅ | Critical endpoints test |
| Debug endpoints | ✅ | Critical endpoints test |
| Error handling | ✅ | Error keywords test |

**Not covered by smoke tests** (covered by other tests):
- Property tests (timer invariants)
- Anti-cheat tests (anomaly detection)
- CSRF tests (token validation)
- Database tests (schema, queries)

---

## FAQ

### Q: Do I need to run ALL tests before every commit?

**A:** No. Run `./pre-commit-check.sh` (4 smoke tests, <5 seconds). Run full test suite (`pytest backend/tests/ -v`) before merging PRs.

### Q: What if I'm only changing frontend code?

**A:** Still run `./pre-commit-check.sh`. Frontend changes can break API calls, cookie handling, or CSRF tokens.

### Q: Can I skip tests for "minor changes"?

**A:** No. The bug we caught (500 error on debug endpoint) was from a "minor change". Always test.

### Q: Tests failed but I need to commit now. What do I do?

**A:** Don't commit. Fix the test failure first. If urgent, ask user for help or revert your changes.

### Q: How do I add a new endpoint to the smoke test?

**A:** Edit `backend/tests/test_smoke.py`, add to `critical_endpoints` list in `test_all_critical_endpoints_return_success()`.

### Q: Pre-commit check passed, but CI failed. Why?

**A:** Environment differences (Python version, DATABASE_URL, missing env vars). Check CI logs and replicate locally.

---

## Summary

✅ **Always run `./pre-commit-check.sh` before committing**
✅ **Fix all test failures before pushing code**
✅ **Add tests for new features**
✅ **Read error messages carefully**
✅ **Never disable or skip tests**

**Remember:** 5 seconds of testing saves hours of debugging production issues!

---

## Related Documentation

- `CURSOR_CLAUDE_HANDOFF_SUMMARY.md` - Complete API reference
- `PRODUCTION_READINESS_REPORT.md` - System status and test results
- `backend/tests/test_smoke.py` - Smoke test source code
- `.github/workflows/test.yml` - CI/CD configuration

---

## Changelog

- **2025-11-03:** Created pre-commit testing guide
  - Added enhanced smoke tests (critical endpoints, timer mechanics, error keywords)
  - Created `pre-commit-check.sh` script
  - Documented testing workflow for Claude, Cursor, ChatGPT
