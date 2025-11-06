# LINEAGE

![Test Suite](https://github.com/saemihemma/lineage/actions/workflows/tests.yml/badge.svg?branch=web-version)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A strategic simulation game about clone management, expeditions, and SELF evolution in the EVE Frontier universe.

## Overview

LINEAGE is a strategic simulation about managing clones, expeditions, and SELF evolution in the EVE Frontier universe. You are the SELF—a core consciousness that splits itself into clones to explore a dangerous frontier. Each clone is a fragment of your identity, grown in a Womb and sent on expeditions that can end in permanent death.

The core tension: You must fragment yourself to grow stronger, but every fragment risks complete annihilation. A clone that dies before upload is lost forever—their experience, their growth, their memory. Only successful returns can strengthen the SELF.

The cycle: Gather resources → Build Wombs → Grow clones → Deploy on expeditions → Upload survivors to preserve their memory → Evolve your Practices → Repeat, with higher stakes.

Operations draw attention. The more you do, the more feral drones notice. High attention increases the chance of attacks that damage your infrastructure and risk your clones. Build multiple Wombs for parallel operations, but each one increases the attention you generate—and the danger.

**Practices**: Kinetic, Cognitive, and Constructive disciplines evolve through use. Each uploaded clone carries experience back to the SELF, unlocking capabilities and reducing costs. The more experienced the clone, the greater the benefit—but only if they survive.

## Core Gameplay

**Build and Grow**
- Gather resources (Tritanium, Metal Ore, Biomass, Synthetic, Organic, and rare Shilajit) to construct your first Womb
- The Womb enables you to grow different types of clones, each requiring specific materials

**Expeditions**
- Deploy clones on expeditions: Mining, Combat, or Exploration
- Match clone types to expedition types for optimal XP gains
- Risk and reward: every venture strengthens the clone but risks permanent loss

**SELF Evolution**
- Each clone consumes a portion of your SELF when grown
- Upload returning clones to preserve their accumulated memory and strengthen the SELF
- Permanent loss: if a clone dies before upload, no progress is saved

**Practices**
- Advance LINEAGE Practices: Kinetic, Cognitive, and Constructive disciplines
- Practices evolve through use, unlocking perks and enhancements
- More experienced uploaded clones make the SELF stronger

## Features

- **Modular Architecture**: Clean separation between game logic, UI, and backend API
- **State Management**: Robust save/load system with versioning and migrations
- **Leaderboard**: Online leaderboard for comparing SELF progress (optional backend API)
- **Telemetry**: Game analytics and data collection (optional)
- **Localization**: i18n support for internationalization
- **Automated Agent**: Optional AI agent for automated gameplay

## Quick Start

LINEAGE is deployed as a web application with a React frontend and FastAPI backend, both hosted on Railway.

### Play Online

**Production:** [https://wonderful-wisdom-production.up.railway.app](https://wonderful-wisdom-production.up.railway.app)

**Staging:** Available for testing (see [CONTRIBUTING.md](CONTRIBUTING.md) for staging workflow)

### Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python3 -m uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Requirements

- **Backend**: Python 3.11+
- **Frontend**: Node.js 18+ and npm

## Project Structure

```
├── backend/       # FastAPI backend API (Railway deployment)
├── frontend/      # React + TypeScript web UI (Railway deployment)
├── core/          # Core game logic and models
├── game/          # Game rules, state, and telemetry
├── agents/        # Automated agent logic
├── data/          # Game data (JSON files)
├── config/        # Game configuration (JSON files)
└── scripts/       # Utility scripts (testing, verification)
```

## Testing

### Pre-commit Hook (Automatic Smoke Tests)

**IMPORTANT:** This repository uses a pre-commit hook that automatically runs smoke tests before every commit.

**Setup (first time only):**
```bash
./scripts/install-pre-commit-hook.sh
```

This ensures critical user journeys never break. If smoke tests fail, your commit will be blocked.

**To skip hook (emergency only):**
```bash
git commit --no-verify -m "emergency: skip smoke tests"
```

**Manual test run:**
```bash
python3 -m pytest backend/tests/test_smoke.py -v
```

See `.pre-commit-config.md` for detailed documentation.

### Backend Tests (pytest)

Run all backend tests:
```bash
python -m pytest backend/tests/ -v
```

Run specific test suites:
```bash
# Golden Path smoke test (critical user journey)
python -m pytest backend/tests/test_smoke.py -v

# Property-based tests (timer validation invariants)
python -m pytest backend/tests/test_property_timers.py -v

# Anti-cheat tests (HMAC signing, anomaly detection)
python -m pytest backend/tests/test_anticheat.py -v

# CSRF protection tests
python -m pytest backend/tests/test_csrf.py -v
```

Run with coverage:
```bash
python -m pytest backend/tests/ --cov=backend --cov=core --cov-report=term-missing
```

### Legacy Unit Tests

Run legacy unit tests:
```bash
python scripts/verify.py --tests-only
```

Or manually:
```bash
python -m unittest discover -v
```

### Continuous Integration

All tests run automatically on push and pull requests via GitHub Actions.
See [.github/workflows/tests.yml](.github/workflows/tests.yml) for CI configuration.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Setting up your development environment
- Code style and conventions
- Testing requirements
- Pull request process
- Reporting bugs and suggesting features

**Quick Start for Contributors:**

1. Fork the repository
2. Clone your fork and work on the `staging` branch
3. Make your changes and ensure tests pass
4. Commit and push to `staging` (`git push origin staging`)
5. Test changes in the staging environment
6. When ready, merge to `web-version` for production

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed instructions on the staging workflow.

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow and testing
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Code of Conduct
- [TESTING.md](TESTING.md) - Testing guide and requirements
- [backend/README.md](backend/README.md) - Backend API documentation
- [frontend/README.md](frontend/README.md) - Frontend development guide

## Support

- **GitHub Issues:** [Report bugs or request features](https://github.com/saemihemma/lineage/issues)
- **GitHub Discussions:** [Ask questions or discuss ideas](https://github.com/saemihemma/lineage/discussions)
- **Pull Requests:** [Contribute code improvements](https://github.com/saemihemma/lineage/pulls)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
