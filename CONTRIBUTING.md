# Contributing to LINEAGE

Thank you for your interest in contributing to LINEAGE! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/lineage.git
   cd lineage
   ```
3. **Add the upstream repository**:
   ```bash
   git remote add upstream https://github.com/saemihemma/lineage.git
   ```
4. **Create a new branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

## Development Setup

### Backend Setup

1. **Install Python dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set up environment variables** (optional, for local development):
   ```bash
   export DATABASE_URL="sqlite:///./lineage.db"
   export HMAC_SECRET_KEY_V1="dev-secret-key"
   export CSRF_SECRET_KEY="dev-csrf-secret"
   ```

3. **Run the backend server**:
   ```bash
   python backend/main.py
   # or
   uvicorn backend.main:app --reload
   ```

### Frontend Setup

1. **Install Node.js dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Set up environment variables** (create `frontend/.env.local`):
   ```env
   VITE_API_URL=http://localhost:8000
   ```

3. **Run the development server**:
   ```bash
   npm run dev
   ```

### Full Stack Development

For full-stack development, run both backend and frontend:

```bash
# Terminal 1: Backend
cd backend
python main.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

## Making Changes

### Branch Workflow (Simple)

LINEAGE uses a simple two-branch workflow:

- **`staging` branch** - Testing environment (auto-deploys to Railway staging)
- **`web-version` branch** - Production environment (auto-deploys to Railway production)

**Workflow:**
1. Work directly on `staging` branch
2. Test changes in staging environment
3. Merge `staging` → `web-version` when ready for production

**No feature branches needed** - just commit to `staging`, test, then merge to production.

```bash
# Start from staging
git checkout staging
git pull origin staging

# Make your changes
# ... edit files ...

# Commit and push to staging
git add .
git commit -m "feat: Your change description"
git push origin staging

# Test in staging environment, then merge to production
git checkout web-version
git merge staging
git push origin web-version
```

### Commit Message Guidelines

Use clear, descriptive commit messages:

```
feat: Add clone unlock system for MINER and VOLATILE clones
fix: Resolve attention decay not updating in UI
docs: Update README with contribution guidelines
refactor: Simplify session cookie handling
test: Add smoke tests for clone unlock system
```

**Format:** `<type>: <description>`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Maintenance tasks

## Testing

### Smoke Tests (Required)

**Critical:** All commits must pass smoke tests before merging. These tests validate the complete user journey.

**Run smoke tests:**
```bash
python3 -m pytest backend/tests/test_smoke.py -v
```

**Pre-commit hook:**
The repository includes a pre-commit hook that automatically runs smoke tests. If tests fail, your commit will be blocked.

**To skip hook (emergency only):**
```bash
git commit --no-verify -m "emergency: skip smoke tests"
```

### Backend Tests

**Run all backend tests:**
```bash
python -m pytest backend/tests/ -v
```

**Run specific test suites:**
```bash
# Smoke tests (critical user journey)
python -m pytest backend/tests/test_smoke.py -v

# Property-based tests
python -m pytest backend/tests/test_property_timers.py -v

# Security tests
python -m pytest backend/tests/test_security.py -v

# CSRF tests
python -m pytest backend/tests/test_csrf.py -v
```

**Run with coverage:**
```bash
python -m pytest backend/tests/ --cov=backend --cov=core --cov-report=term-missing
```

### Frontend Tests

**Run frontend tests:**
```bash
cd frontend
npm test
```

## Pull Request Process

### Before Submitting

1. **Ensure tests pass:**
   - Run smoke tests: `python3 -m pytest backend/tests/test_smoke.py -v`
   - Run relevant test suites
   - Ensure no TypeScript errors: `cd frontend && npm run build`

2. **Update documentation:**
   - Update README.md if needed
   - Add/update code comments
   - Update API documentation if backend changes

3. **Check for secrets:**
   - No hardcoded API keys
   - No database credentials
   - No personal tokens
   - All secrets use environment variables

4. **Follow code style:**
   - Python: Follow PEP 8
   - TypeScript: Follow existing patterns
   - Use meaningful variable names
   - Add comments for complex logic

### Creating a Pull Request

1. **Push your branch to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create PR on GitHub:**
   - Go to https://github.com/saemihemma/lineage
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template

3. **PR Requirements:**
   - ✅ All tests pass (CI will run automatically)
   - ✅ No merge conflicts
   - ✅ Clear description of changes
   - ✅ Related issues referenced (if any)
   - ✅ Screenshots (if UI changes)

### PR Review Process

1. **Maintainers will review:**
   - Code quality and style
   - Test coverage
   - Security concerns
   - Documentation updates

2. **Address feedback:**
   - Make requested changes
   - Push updates to your branch
   - PR will automatically update

3. **After approval:**
   - Maintainer will merge
   - Branch will be deleted (if enabled)

## Code Style

### Python

- Follow PEP 8 style guide
- Use type hints where appropriate
- Maximum line length: 100 characters (flexible)
- Use meaningful variable and function names
- Add docstrings for public functions/classes

**Example:**
```python
def calculate_clone_cost(state: GameState, clone_kind: str) -> Dict[str, int]:
    """
    Calculate resource cost for growing a clone.
    
    Args:
        state: Current game state
        clone_kind: Type of clone (BASIC, MINER, VOLATILE)
    
    Returns:
        Dictionary of resource costs
    """
    # Implementation
    pass
```

### TypeScript/React

- Use TypeScript for type safety
- Use functional components with hooks
- Follow existing component patterns
- Use meaningful prop and variable names
- Add JSDoc comments for complex functions

**Example:**
```typescript
/**
 * Check if a clone type is unlocked based on Construction practice level
 */
export function isCloneTypeUnlocked(
  state: GameState, 
  cloneKind: string
): boolean {
  // Implementation
}
```

### General Guidelines

- **Null Safety:** Always use optional chaining (`?.`) and nullish coalescing (`??`) to prevent errors
- **Error Handling:** Handle errors gracefully with clear error messages
- **Logging:** Use appropriate log levels (debug, info, warning, error)
- **Comments:** Explain "why" not "what" - code should be self-documenting

## Reporting Bugs

### Before Reporting

1. Check if the bug has already been reported
2. Try to reproduce the bug consistently
3. Check if it's a known issue in closed issues

### Bug Report Template

Use the GitHub issue template or include:

- **Description:** Clear description of the bug
- **Steps to Reproduce:** Detailed steps to reproduce
- **Expected Behavior:** What should happen
- **Actual Behavior:** What actually happens
- **Screenshots/Logs:** If applicable
- **Environment:**
  - OS and version
  - Python version
  - Node.js version
  - Browser (if frontend issue)

## Suggesting Features

### Feature Request Template

- **Description:** Clear description of the feature
- **Use Case:** Why is this feature needed?
- **Proposed Solution:** How should it work?
- **Alternatives:** Other solutions considered
- **Additional Context:** Screenshots, mockups, etc.

### Before Suggesting

1. Check if the feature has been requested
2. Consider if it fits the game's design
3. Think about implementation complexity
4. Consider backward compatibility

## Getting Help

- **GitHub Discussions:** For questions and discussions
- **GitHub Issues:** For bugs and feature requests
- **Pull Requests:** For code contributions

## Additional Resources

- [README.md](README.md) - Project overview
- [backend/README.md](backend/README.md) - Backend API documentation
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide

## Thank You!

Contributions are what make open source great. Thank you for taking the time to contribute to LINEAGE!
