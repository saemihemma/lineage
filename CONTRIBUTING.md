# Contributing to LINEAGE

This document outlines the development workflow and verification process for LINEAGE.

## Development Workflow

### Before Submitting Changes

Before submitting any code changes, you should:

1. **Run Unit Tests**: Verify that all existing tests pass
2. **Verify Application Launch**: Ensure the application starts without errors
3. **Test on Target Platforms**: If possible, test on both Windows and Mac

### Quick Verification

The easiest way to verify your changes is to run the verification script:

```bash
# Quick check: Run tests only (fast)
python scripts/verify.py --tests-only

# Full verification: Tests + app launch check
python scripts/verify.py --full
```

On Windows:
```cmd
python scripts\verify.py --tests-only
python scripts\verify.py --full
```

### Manual Verification

If you prefer to run tests manually:

**Unix/Mac:**
```bash
# Using shell script
./scripts/run_tests.sh

# Or directly with Python
python3 -m unittest discover -v
```

**Windows:**
```cmd
REM Using batch file
scripts\run_tests.bat

REM Or directly with Python
python -m unittest discover -v
```

### Running the Application

**Unix/Mac:**
```bash
./run_mac_linux.sh
```

**Windows:**
```cmd
run_windows.bat
```

Or directly:
```bash
python main.py
```

## Test Structure

Tests are located in:
- `test_*.py` files in the project root
- `tests/test_*.py` files in the tests/ directory

The test suite includes:
- `test_frontier.py`: Core game mechanics and logic
- `test_loading_screen.py`: Loading screen UI tests
- `tests/test_migrations.py`: State migration tests

## Verification Script Options

The `scripts/verify.py` script supports the following options:

- **No arguments**: Runs tests only (default, quick check)
- `--tests-only`: Explicitly run only tests
- `--full`: Run tests and verify app launch

## Expected Behavior

### Tests Should Always Pass

Before submitting changes, ensure:
- All existing unit tests pass
- New functionality has corresponding tests (when applicable)
- No regressions are introduced

### Application Should Launch

The application should:
- Start without import errors
- Load all required assets
- Display the briefing screen first
- Transition correctly between screens

## Platform-Specific Notes

### Mac/Linux
- Use `python3` command
- Shell scripts should have execute permissions
- Tkinter should be available in standard Python installations

### Windows
- Use `python` command (may be `py` on some systems)
- Batch files (`.bat`) are used instead of shell scripts
- Tkinter should be available in standard Python installations

## Troubleshooting

### Tests Fail
- Check that all dependencies are installed
- Verify Python version (3.9+ recommended)
- Check for syntax errors in code

### App Won't Launch
- Verify Tkinter is installed: `python -c "import tkinter"`
- Check for missing asset files in `assets/` directory
- Review console output for import errors

### Verification Script Issues
- Ensure you're running from the project root directory
- Check that `scripts/verify.py` has execute permissions (Unix/Mac): `chmod +x scripts/verify.py`
- Verify Python path is correct

## Continuous Integration

For automated testing, the verification script can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: python scripts/verify.py --tests-only
```

## Questions?

If you encounter issues with the verification process or have questions about the workflow, please check:
1. This CONTRIBUTING.md file
2. The verification script help: `python scripts/verify.py --help`
3. Test files for examples of how to write tests

