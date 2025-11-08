# LINEAGE - Agent Onboarding Guide

**Version:** Systems v1 (as of latest commit)  
**Last Updated:** 2024  
**Purpose:** Comprehensive context for ChatGPT agents working on LINEAGE codebase

---

## Table of Contents

1. [Game Overview](#game-overview)
2. [Tech Stack](#tech-stack)
3. [Architecture](#architecture)
4. [Core Systems](#core-systems)
5. [Key Features](#key-features)
6. [Project Structure](#project-structure)
7. [Development Workflow](#development-workflow)
8. [Configuration System](#configuration-system)
9. [Testing](#testing)
10. [Deployment](#deployment)
11. [Common Patterns & Conventions](#common-patterns--conventions)

---

## Game Overview

### Narrative & Concept

**LINEAGE** is a strategic simulation game set in the EVE Frontier universe. You play as the **SELF**—a core consciousness that fragments itself into clones to explore a dangerous frontier.

**Core Tension:** You must fragment yourself to grow stronger, but every fragment risks complete annihilation. A clone that dies before upload is lost forever—their experience, their growth, their memory. Only successful returns can strengthen the SELF.

### Gameplay Loop

1. **Gather Resources** → Collect Tritanium, Metal Ore, Biomass, Synthetic, Organic, and rare Shilajit
2. **Build Wombs** → Construct infrastructure to grow clones (up to 4 wombs, with parallel processing)
3. **Grow Clones** → Create clones of different types (BASIC, MINER, VOLATILE) that consume SELF integrity
4. **Deploy on Expeditions** → Send clones on MINING, COMBAT, or EXPLORATION missions
5. **Upload Survivors** → Preserve clone memory and strengthen the SELF
6. **Evolve Practices** → Advance Kinetic, Cognitive, and Constructive disciplines
7. **Repeat** → With higher stakes and more complex operations

### Key Mechanics

- **Attention System:** Operations draw attention from feral drones. High attention increases attack probability.
- **Permanent Death:** Clones that die before upload lose all progress permanently.
- **SELF Integrity:** Growing clones consumes soul percentage. Uploading restores it based on clone XP.
- **Practices:** Three disciplines (Kinetic, Cognitive, Constructive) unlock capabilities and reduce costs.
- **Womb Overload:** Multiple wombs enable parallel operations but increase attention and time penalties.
- **Feral Drone Attacks:** Random attacks damage wombs and can kill clones, triggered by high attention.

---

## Tech Stack

### Backend

- **Language:** Python 3.11+
- **Framework:** FastAPI 0.104.1
- **Server:** Uvicorn (ASGI)
- **Database:** 
  - SQLite (primary, in-process with WAL mode)
  - PostgreSQL (optional, for production leaderboard/telemetry)
- **Dependencies:**
  - `fastapi` - Web framework
  - `uvicorn[standard]` - ASGI server
  - `python-multipart` - Form data handling
  - `psycopg2-binary` - PostgreSQL adapter (optional)

### Frontend

- **Language:** TypeScript 5.9.3
- **Framework:** React 19.1.1
- **Build Tool:** Vite 7.1.7
- **Routing:** React Router DOM 7.9.5
- **State Management:** React Hooks + localStorage
- **Testing:** Vitest 2.1.5, React Testing Library

### Deployment

- **Platform:** Railway
- **Backend Service:** `lineage-production` (production), `lineage-staging-backend` (staging)
- **Frontend Service:** `wonderful-wisdom-production` (production), `lineage-staging-frontend` (staging)
- **CI/CD:** GitHub Actions (`.github/workflows/tests.yml`)

### Development Tools

- **Version Control:** Git (GitHub)
- **Code Editor:** Cursor (AI-powered IDE)
- **AI Assistant:** Claude Code (via Cursor), ChatGPT (for game design)
- **Testing:** pytest (backend), Vitest (frontend)

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Briefing    │  │  Loading     │  │ Simulation  │     │
│  │   Screen     │→ │   Screen     │→ │   Screen    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  State: localStorage + React Hooks                          │
│  API: fetch() → Backend endpoints                          │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/JSON
                        │ (with CSRF tokens)
┌───────────────────────▼─────────────────────────────────────┐
│                  Backend (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Routers    │  │  Outcome    │  │   Game      │     │
│  │  (game.py)   │→ │  Engine     │→ │   Rules     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Models     │  │   State     │  │   Wombs     │     │
│  │  (dataclass) │  │ Management  │  │   Systems   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  Database: SQLite (in-process, WAL mode)                    │
└─────────────────────────────────────────────────────────────┘
```

### State Management

**Frontend:**
- Game state stored in `localStorage` (persistent across sessions)
- React hooks (`useState`, `useEffect`) for UI state
- State passed to backend in request body (not server-side storage)
- Backend returns updated state in response

**Backend:**
- Stateless API (no server-side session storage)
- State validation and transformation
- Deterministic RNG based on `self_name` + action context
- Event emission for telemetry/analytics

### Data Flow

1. **User Action** → Frontend calls API endpoint with current state
2. **Backend Processing** → Outcome Engine calculates deterministic result
3. **State Update** → Backend applies changes and returns new state
4. **Frontend Update** → React updates UI from returned state
5. **Persistence** → Frontend saves to localStorage

---

## Core Systems

### 1. Outcome Engine (`backend/engine/outcomes.py`)

**Purpose:** Deterministic, config-driven system for resolving all game actions.

**Key Components:**
- **`OutcomeContext`:** Encapsulates all inputs (clone, self_state, systems, config, seed_parts)
- **`Mod`:** Represents a modifier (target, operation, value, source)
- **`CanonicalStats`:** Aggregated game stats (time_mult, success_chance, death_chance, etc.)
- **`Outcome`:** Result of an action (result, deltas, rolls, terms, explanation)

**Resolvers:**
- `resolve_expedition()` - Expedition outcomes (death, loot, XP)
- `resolve_gather()` - Resource gathering (amount, time)
- `resolve_grow()` - Clone growth (cost, time, soul split)
- `resolve_upload()` - Clone upload (soul restore, XP gain)

**Features:**
- HMAC-seeded RNG for determinism
- Modifier aggregation (add before mult)
- Global invariants/clamping
- Explainability (debug mode with detailed breakdowns)

### 2. Attention System (`game/wombs.py`)

**Global Attention:** Single value in `GameState.global_attention` (0-100%)

**Attention Gain:**
- Gather: +6
- Grow: +6
- Expedition: +9
- Build Womb: +20

**Attention Decay:** 3.0 per minute when idle

**Feral Drone Attacks:**
- Yellow band (≥25%): 12% attack probability
- Red band (≥55%): 25% attack probability
- Attacks damage wombs (2-6% durability) and reduce attention (10% ± variance)
- Splash damage: 10-25% of primary damage propagates to other active wombs

### 3. Womb System (`game/wombs.py`)

**Womb Properties:**
- Durability: 0-100 (decays passively at 2.0 per minute)
- Max Durability: 100
- Functional: durability > 0

**Womb Operations:**
- **Build:** Requires resources (Tritanium, Metal Ore, Biomass)
- **Repair:** Restores 5 durability points (costs 3x build cost per point)
- **Parallel Processing:** Each functional womb enables one concurrent Grow task
- **Overload:** Each additional womb adds +4 attention and +3% time multiplier

**Heat Cross-link:** When any womb grows, all active wombs gain +2 attention

**Unlock Progression:**
- Womb 1: Always available
- Womb 2: Any Practice Level 4
- Womb 3: Any Practice Level 7
- Womb 4: Any Practice Level 10

### 4. Clone System (`game/rules.py`)

**Clone Types:**
- **BASIC:** Default clone type
- **MINER:** Unlocked at Constructive Level 4 (better for MINING expeditions)
- **VOLATILE:** Unlocked at Constructive Level 9 (better for COMBAT expeditions)

**Clone Properties:**
- `kind`: Clone type
- `traits`: Dict of trait values (PWC, SSC, MGC, DLT, ENF, ELK, FRK)
- `xp`: Dict of expedition XP (MINING, COMBAT, EXPLORATION)
- `survived_runs`: Number of successful expeditions
- `biological_days`: Age of clone (affects death chance on expeditions)
- `alive`: Boolean (false if died on expedition)
- `uploaded`: Boolean (true if uploaded to SELF)

**Clone Growth:**
- Consumes resources (Synthetic, Organic, Shilajit)
- Splits SELF integrity (base 5% + variance)
- Awards Constructive practice XP
- Gains attention (+6)

**Clone Upload:**
- Restores SELF integrity based on clone XP (uncapped, scales with XP)
- Awards SELF XP (soul_xp)
- Marks clone as uploaded
- Gains attention (+0, warning only for feral attacks)

### 5. Expedition System (`game/rules.py`, `backend/engine/outcomes.py`)

**Expedition Types:**
- **MINING:** Base death 6%, base XP 20, rewards Tritanium/Metal Ore
- **COMBAT:** Base death 8%, base XP 24, rewards Biomass/Synthetic
- **EXPLORATION:** Base death 6.5%, base XP 16, rewards mixed + 15% Shilajit chance

**Death Probability Factors:**
- Base death chance (from config)
- Clone XP (higher XP = lower death chance)
- Clone kind compatibility (MINER on MINING = 50% safer)
- Trait effects (DLT reduces incompatible expedition death)
- SELF level (higher level = lower death chance, capped)
- Attention level (yellow/red bands add death chance)
- Aging risk (clones >160 biological days get +death per day)

**Success Outcomes:**
- XP gain (scaled by clone kind compatibility)
- Resource rewards (randomized within ranges)
- Shilajit chance (EXPLORATION only)

### 6. Practices System (`core/game_logic.py`)

**Three Practices:**
- **Kinetic:** Gained from gathering resources
- **Cognitive:** Gained from expeditions (especially EXPLORATION)
- **Constructive:** Gained from building wombs and growing clones

**Practice Effects:**
- **Kinetic:** Reduces gathering time
- **Cognitive:** Reduces expedition time
- **Constructive:** Reduces clone growth costs, unlocks clone types and multiple wombs

**Unlocks:**
- MINER clone: Constructive Level 4
- VOLATILE clone: Constructive Level 9
- Womb 2: Any Practice Level 4
- Womb 3: Any Practice Level 7
- Womb 4: Any Practice Level 10

### 7. SELF System (`core/models.py`)

**SELF Properties:**
- `soul_percent`: Current integrity (0-100%)
- `soul_xp`: Total XP accumulated from uploaded clones
- `soul_level`: Calculated from soul_xp (level = sqrt(soul_xp / 100))
- `self_name`: Player identifier (used for RNG seeding)

**SELF Level Effects:**
- Reward multiplier: +0.2% per level (max 1.20x)
- Time multiplier: -0.2% per level (min 0.85x)
- Death chance reduction: -0.04% per level (max -0.08)

**Clone Cost Curve:**
- Piecewise breakpoint system
- Base multiplier: 1.0
- Per level add: 0.025
- Breakpoints at levels 4, 7, 10 (reducing slope)
- Max multiplier: 1.85

### 8. Trait System (`core/game_logic.py`)

**Seven Traits:**
- **PWC** (Physical Weakness Compensation)
- **SSC** (Sensory System Compensation)
- **MGC** (Metabolic Growth Compensation)
- **DLT** (Death-Linked Trait) - Reduces incompatible expedition death
- **ENF** (Energy Flux) - Randomly affects outcomes
- **ELK** (Elasticity) - Reduces death chance
- **FRK** (Fragility) - Increases death chance

**Trait Generation:**
- Deterministic based on `self_name` (normalized)
- Each trait: 0-10 points
- Neutral value: 5 (no effect)
- Effects scale linearly with deviation from neutral

### 9. Prayer System (`backend/routers/game.py`)

**"Pray to Trinary" Feature:**
- Random effects with 12-19 second cooldown
- 1% chance to kill active clone
- If active gather task: Reduces duration by 25-45%
- Otherwise: Stores expedition prayer bonus (death reduction, reward multiplier)
- Prayer bonus consumed on next expedition

---

## Key Features

### Deterministic RNG

All game outcomes use HMAC-seeded RNG for determinism:
- Seed parts: `self_name` (normalized), `womb_id`, `task_started_at`, `config_version`
- Ensures reproducible outcomes given same inputs
- Prevents cheating via outcome prediction

### Config-Driven Balance

All game parameters in `config/gameplay.json`:
- Expedition death rates, XP, rewards
- Attention bands, feral attack probabilities
- Trait effects, SELF level bonuses
- Womb costs, repair costs, parallel limits
- Clone cost curves, practice unlocks

**Config Version:** Included in RNG seed to ensure determinism across config changes

### CSRF Protection

- Backend middleware validates CSRF tokens on state-changing requests
- Frontend reads token from cookie and includes in headers
- Prevents cross-site request forgery attacks

### Rate Limiting

- Session-based rate limiting on backend endpoints
- Returns `429 Too Many Requests` with `Retry-After` header
- Keeper-style error messages with time estimates

### Anti-Cheat

- HMAC-signed expedition outcomes
- Timer validation (prevents early task completion)
- Anomaly detection (suspicious action rates, survival rates)
- Action rate tracking (per session, per action type)

---

## Project Structure

```
lineage/
├── backend/                    # FastAPI backend
│   ├── main.py                 # FastAPI app entry point
│   ├── routers/
│   │   ├── game.py             # Game action endpoints
│   │   ├── config.py           # Config serving endpoint
│   │   └── ...
│   ├── engine/
│   │   └── outcomes.py         # Outcome Engine (deterministic resolvers)
│   ├── middleware/
│   │   └── csrf.py             # CSRF protection
│   ├── tests/                  # Backend tests
│   │   ├── test_smoke.py       # Critical path tests
│   │   ├── test_csrf.py        # CSRF tests
│   │   ├── test_anticheat.py   # Anti-cheat tests
│   │   └── ...
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── screens/            # Main screens (Briefing, Loading, Simulation)
│   │   ├── components/         # React components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── stores/             # State management
│   │   ├── utils/              # Utility functions
│   │   ├── api/                # API client
│   │   └── types/              # TypeScript types
│   ├── package.json            # Node dependencies
│   └── vite.config.ts          # Vite configuration
│
├── core/                       # Core game logic (shared)
│   ├── models.py               # Dataclass models (GameState, Clone, Womb, etc.)
│   ├── config.py               # Config loading
│   ├── game_logic.py           # Helper functions (traits, practices, unlocks)
│   ├── csrf.py                 # CSRF token generation/validation
│   └── anticheat.py            # Anti-cheat mechanisms
│
├── game/                       # Game rules and state
│   ├── rules.py                # Core game rules (gather, grow, expedition, upload)
│   ├── state.py                # GameState class with RNG
│   ├── wombs.py                # Womb systems (attention, attacks, repair)
│   └── migrations/             # State migration scripts
│
├── config/                     # Game configuration
│   └── gameplay.json           # Single source of truth for all game parameters
│
├── data/                       # Game data files
│   ├── briefing_text.json     # Briefing screen text
│   ├── feral_drone_messages.json  # Feral attack messages
│   └── rate_limit_messages.json   # Rate limit error messages
│
├── .github/
│   └── workflows/
│       └── tests.yml           # CI/CD pipeline
│
├── README.md                   # Project overview
├── CONTRIBUTING.md             # Contribution guidelines
└── AGENT_ONBOARDING.md         # This file
```

---

## Development Workflow

### Branch Strategy

**Two-Branch Workflow:**
- **`staging` branch** → Staging environment (testing)
- **`web-version` branch** → Production environment (live)

**Workflow:**
1. Work directly on `staging` branch
2. Test changes in staging environment (Railway auto-deploys)
3. Merge `staging` → `web-version` when ready for production
4. Production auto-deploys from `web-version`

**No feature branches needed** - just commit to `staging`, test, then merge to production.

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

**Environment Variables:**
- Backend: `DATABASE_URL`, `ENVIRONMENT`, `ALLOWED_ORIGINS`, `HMAC_SECRET_KEY_V1`, `CSRF_SECRET_KEY`
- Frontend: `VITE_API_URL` (defaults to `http://localhost:8000`)

### Commit Guidelines

**Format:** `<type>: <description>`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Maintenance tasks

**Examples:**
```
feat: Add parallel grow slots for multiple wombs
fix: Resolve attention decay not updating in UI
docs: Update README with contribution guidelines
```

---

## Configuration System

### `config/gameplay.json`

**Single Source of Truth** for all game parameters.

**Structure:**
```json
{
  "config_version": "systems_v1_safer_expeditions",
  "attention": { ... },
  "expeditions": { ... },
  "clone_kind_compatibility": { ... },
  "traits": { ... },
  "traits_effects": { ... },
  "self": { ... },
  "practices": { ... },
  "aging": { ... },
  "wombs": { ... },
  "gather": { ... },
  "grow": { ... },
  "upload": { ... }
}
```

**Config Version:** Included in RNG seed to ensure determinism across config changes.

**Loading:**
- Backend: `core/config.py` loads and exports `GAMEPLAY_CONFIG`
- Frontend: Served via `/api/config/gameplay` endpoint (with ETag caching)

**Balance Changes:**
- Update `config/gameplay.json`
- Increment `config_version` (affects RNG seed)
- Test in staging
- Deploy to production

---

## Testing

### Test Structure

**Backend Tests (`backend/tests/`):**
- `test_smoke.py` - Critical path tests (golden path, variations)
- `test_csrf.py` - CSRF protection tests
- `test_anticheat.py` - Anti-cheat tests (HMAC, timers, anomaly detection)
- `test_bugfixes.py` - Regression tests
- `test_database.py` - Database schema and operations
- `test_property_timers.py` - Property-based tests for timer validation

**Frontend Tests (`frontend/src/__tests__/`):**
- Component tests (React Testing Library)
- Hook tests (useGameState, useEventFeed)
- Integration tests

### Running Tests

**Backend:**
```bash
# All tests
python3 -m pytest backend/tests/ -v

# Smoke tests (critical)
python3 -m pytest backend/tests/test_smoke.py -v

# Specific suite
python3 -m pytest backend/tests/test_anticheat.py -v
```

**Frontend:**
```bash
cd frontend
npm test
```

### Pre-commit Hook

**Automatic smoke tests** run before every commit (if installed):
```bash
./scripts/install-pre-commit-hook.sh
```

**Skip hook (emergency only):**
```bash
git commit --no-verify -m "emergency: skip smoke tests"
```

---

## Deployment

### Railway Services

**Production:**
- Backend: `lineage-production` (branch: `web-version`)
- Frontend: `wonderful-wisdom-production` (branch: `web-version`)
- URL: https://wonderful-wisdom-production.up.railway.app

**Staging:**
- Backend: `lineage-staging-backend` (branch: `staging`)
- Frontend: `lineage-staging-frontend` (branch: `staging`)

### Environment Variables

**Backend:**
- `ENVIRONMENT=production` or `staging`
- `ALLOWED_ORIGINS=<frontend-url>`
- `DATABASE_URL=<postgres-url>` (optional, uses SQLite if not set)
- `HMAC_SECRET_KEY_V1=<secret>` (for anti-cheat)
- `CSRF_SECRET_KEY=<secret>` (for CSRF protection)

**Frontend:**
- `VITE_API_URL=<backend-url>` (set at build time)

### CI/CD

**GitHub Actions** (`.github/workflows/tests.yml`):
- Runs on push to `staging` and `web-version` branches
- Installs dependencies from `requirements.txt` and `backend/requirements.txt`
- Runs pytest test suite
- Badge: https://github.com/saemihemma/lineage/actions/workflows/tests.yml/badge.svg?branch=web-version

---

## Common Patterns & Conventions

### State Management

**Frontend:**
- Use `useGameState` hook for game state
- State persisted in `localStorage` via `saveStateToLocalStorage()`
- State passed to backend in request body
- Backend returns updated state in response

**Backend:**
- Use `dict_to_game_state()` to deserialize request body
- Use `game_state_to_dict()` to serialize response
- Always validate state structure
- Apply migrations if state version is old

### Error Handling

**Frontend:**
- Network errors: Show user-friendly message
- API errors: Display error detail from response
- Validation errors: Show field-specific messages

**Backend:**
- Use `HTTPException` with appropriate status codes
- Include clear error messages in `detail`
- Log errors for debugging
- Never expose internal errors to frontend

### API Endpoints

**Pattern:** `/api/game/<action>`

**State-Changing Actions (POST):**
- Require CSRF token in `X-CSRF-Token` header
- Accept state in request body
- Return updated state in response
- Emit events for telemetry

**Read-Only Actions (GET):**
- No CSRF required
- Return current state or data
- Support ETag caching where appropriate

### RNG Seeding

**Always use deterministic seeding:**
```python
from backend.engine.outcomes import compute_rng_seed, _create_rng

seed_parts = {
    "self_name": state.self_name,
    "womb_id": womb_id,
    "task_started_at": task_started_at,
    "config_version": GAMEPLAY_CONFIG_VERSION
}
rng = _create_rng(seed_parts)
```

**Never use `random.random()` directly** - always use seeded RNG from Outcome Engine.

### Config Access

**Backend:**
```python
from core.config import GAMEPLAY_CONFIG, GAMEPLAY_CONFIG_VERSION

# Access config
death_prob = GAMEPLAY_CONFIG["expeditions"]["MINING"]["base_death_prob"]
```

**Frontend:**
```typescript
// Fetch config from API
const config = await fetch("/api/config/gameplay").then(r => r.json());
```

### Type Safety

**Backend:**
- Use type hints for all functions
- Use dataclasses for models (`@dataclass`)
- Validate types in API endpoints

**Frontend:**
- Use TypeScript interfaces for all types
- Define types in `frontend/src/types/game.ts`
- Use type guards for runtime validation

---

## Recent Changes & Current State

### Systems v1 Implementation

**Outcome Engine:**
- Deterministic, config-driven system for all game actions
- HMAC-seeded RNG for reproducibility
- Modifier aggregation and clamping
- Explainability (debug mode)

**Attention System:**
- Global attention (not per-womb)
- Decay: 3.0 per minute
- Feral attacks: Yellow (12%), Red (25%)
- Splash damage to other wombs

**Womb Overload Redesign:**
- Parallel grow slots (one per functional womb)
- Heat cross-link (+2 attention to all wombs when any grows)
- Overload penalties (+4 attention, +3% time per additional womb)
- Feral splash damage (10-25% propagation)

**Balance Changes:**
- Expedition death rates halved
- XP doubled
- Shilajit drops from EXPLORATION (15% chance)
- Repair costs: 3x build cost per durability point

### Test Cleanup

**Removed:**
- Tests using deprecated `/api/game/state` endpoint (410 Gone)
- Tests with database schema issues (telemetry, leaderboard)
- Property test edge cases

**Remaining:**
- Smoke tests (critical path)
- CSRF unit tests
- Anti-cheat tests
- Database tests (leaderboard only)
- Property tests (timer validation)

### Staging Environment

**Setup:**
- `staging` branch created
- Railway services configured
- CORS configured for staging frontend
- Environment variables set

**Workflow:**
- Work on `staging` branch
- Test in staging environment
- Merge to `web-version` for production

---

## Key Files to Know

### Backend

- `backend/main.py` - FastAPI app, CORS, middleware setup
- `backend/routers/game.py` - All game action endpoints
- `backend/engine/outcomes.py` - Outcome Engine (deterministic resolvers)
- `game/rules.py` - Core game rules (gather, grow, expedition, upload)
- `game/wombs.py` - Womb systems (attention, attacks, repair)
- `core/models.py` - Dataclass models (GameState, Clone, Womb)
- `core/config.py` - Config loading and exports

### Frontend

- `frontend/src/screens/SimulationScreen.tsx` - Main game screen
- `frontend/src/hooks/useGameState.ts` - Game state management hook
- `frontend/src/api/game.ts` - API client functions
- `frontend/src/types/game.ts` - TypeScript type definitions
- `frontend/src/utils/localStorage.ts` - State persistence

### Configuration

- `config/gameplay.json` - Single source of truth for all game parameters
- `data/feral_drone_messages.json` - Feral attack messages
- `data/rate_limit_messages.json` - Rate limit error messages

---

## Getting Help

### Documentation

- `README.md` - Project overview and quick start
- `CONTRIBUTING.md` - Development workflow and guidelines
- `TESTING.md` - Testing guide
- `AGENT_ONBOARDING.md` - This file

### Code Search

Use semantic search to find:
- "How does X work?" - Understand system behavior
- "Where is Y handled?" - Find implementation location
- "What happens when Z?" - Trace execution flow

### Common Questions

**Q: How do I change game balance?**  
A: Update `config/gameplay.json`, increment `config_version`, test in staging, deploy.

**Q: How do I add a new game action?**  
A: Add resolver in `backend/engine/outcomes.py`, add endpoint in `backend/routers/game.py`, add UI in `frontend/src/screens/SimulationScreen.tsx`.

**Q: How do I debug an outcome?**  
A: Set `DEBUG_OUTCOMES=true` environment variable, check `Outcome.explanation` field.

**Q: How do I test locally?**  
A: Run backend (`uvicorn main:app --reload`) and frontend (`npm run dev`) separately, ensure `VITE_API_URL` points to backend.

---

## Summary

LINEAGE is a strategic simulation game with:
- **Backend:** FastAPI + SQLite, deterministic Outcome Engine
- **Frontend:** React + TypeScript, localStorage state management
- **Deployment:** Railway (staging + production)
- **Key Systems:** Attention, Wombs, Clones, Expeditions, Practices, SELF
- **Architecture:** Stateless API, config-driven balance, deterministic RNG

**Current State:** Systems v1 implemented, staging environment set up, tests cleaned up, ready for game design iteration.

**Next Steps:** Balance tuning, new features, gameplay improvements - all config-driven via `config/gameplay.json`.

---

**For ChatGPT Agents:** Use this document as context when working on LINEAGE. Always check `config/gameplay.json` for current balance values, use semantic search to understand systems, and follow the development workflow (staging → production).

