# LINEAGE

A strategic simulation game about clone management, expeditions, and SELF evolution in the EVE Frontier universe.

## Overview

LINEAGE is a resource management and progression game where you build a Womb to grow clones, deploy them on dangerous expeditions, and evolve your SELF through accumulated experience and memory. Each decision matters—clones can die permanently, but successful expeditions and strategic uploads strengthen your core identity.

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

### Running the Game

**Mac/Linux:**
```bash
./run_mac_linux.sh
```

**Windows:**
```cmd
run_windows.bat
```

**Direct:**
```bash
python main.py
```

### Requirements

- Python 3.9+
- Tkinter (usually included with Python)
- PIL/Pillow (for image loading)

```bash
pip install -r requirements.txt
```

## Project Structure

```
├── core/          # Core game logic and models
├── game/          # Game rules, state, and telemetry
├── ui/            # User interface (Tkinter screens)
├── agents/        # Automated agent logic
├── backend/       # FastAPI backend for leaderboard/telemetry
├── data/          # Game data (JSON files)
└── scripts/       # Utility scripts (testing, verification)
```

## Testing

Run unit tests:
```bash
python scripts/verify.py --tests-only
```

Or manually:
```bash
python -m unittest discover -v
```

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow and testing
- [DEPLOYMENT.md](DEPLOYMENT.md) - Backend API deployment guide
- [backend/README.md](backend/README.md) - Backend API documentation

## License

[Add your license here]
