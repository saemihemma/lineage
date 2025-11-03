# Outcome Engine Architecture - Complete Summary

## Overview

The Outcome Engine is a **deterministic, config-driven system** for resolving all game action outcomes. It replaces scattered logic with a single, predictable pipeline that ensures consistency, explainability, and easy tuning.

**Key Principle**: All randomness is deterministic via HMAC-seeded RNG. Same inputs (user, session, action, config version) → same outcome.

---

## Architecture

### Core Components

1. **`backend/engine/outcomes.py`** - Main outcome resolution module
2. **`data/outcomes_config.json`** - All game tuning in one JSON file
3. **Integration Points**: `game/rules.py` (handlers), `backend/routers/game.py` (endpoints)

### Data Contracts

#### `SeedParts`
```python
@dataclass
class SeedParts:
    user_id: str          # session_id
    session_id: str       # session_id
    action_id: str        # expedition_id or task_id
    config_version: str   # from outcomes_config.json ("expeditions_v1")
    timestamp: float      # action start time
```

#### `OutcomeContext`
```python
@dataclass
class OutcomeContext:
    action: Literal['expedition', 'gather', 'grow', 'upload']
    clone: Optional[Clone]              # Required for expedition/upload, None for gather/grow
    self_level: int                      # SELF soul level
    practices: Dict[str, int]            # Practice XP levels
    global_attention: float              # Global attention (0-100)
    womb_durability: float               # Best functional womb durability
    expedition_kind: Optional[str]       # For expeditions
    resource: Optional[str]              # For gather
    clone_kind: Optional[str]            # For grow
    soul_percent: Optional[float]        # For grow/upload
    config: Dict                         # Backward compat (practice levels, etc.)
    outcomes_config: Dict[str, Any]      # From outcomes_config.json
    seed_parts: SeedParts                # For deterministic RNG
```

#### `Mod`
```python
@dataclass
class Mod:
    target: Literal['time_mult', 'success_chance', 'death_chance', 'reward_mult', 'xp_mult', 'cost_mult', 'attention_delta']
    op: Literal['add', 'mult']
    value: float
    source: str  # e.g., "Trait:ELK(7)", "FeralAttack:YELLOW", "Practice:Kinetic_L2+"
```

#### `CanonicalStats`
```python
@dataclass
class CanonicalStats:
    """All 7 canonical stats enforced from day 1"""
    time_mult: float        # Duration multiplier (0.5-2.0)
    success_chance: float    # Success probability (0-1)
    death_chance: float      # Death probability (0-1)
    reward_mult: float       # Reward multiplier (0.5-3.0)
    xp_mult: float          # XP multiplier (0.5-3.0)
    cost_mult: float        # Cost multiplier (0.5-3.0)
    attention_delta: float   # Attention change on action
```

#### `Outcome`
```python
@dataclass
class Outcome:
    result: Literal['success', 'death', 'failure']
    stats: CanonicalStats                    # Final computed stats
    loot: Dict[str, int]                     # Resources gained
    xp_gained: Dict[str, int]                # XP gained (practice XP is separate)
    mods_applied: List[Mod]                 # All modifiers applied
    terms: Dict[str, Any]                    # Internal calculation breakdown
    explanation: Optional[Dict[str, Any]]    # Debug breakdown (DEBUG_OUTCOMES flag)
    # Action-specific fields:
    shilajit_found: bool = False
    feral_attack: Optional[Dict[str, Any]] = None
    time_seconds: Optional[float] = None
    cost: Optional[Dict[str, int]] = None
    soul_split_percent: Optional[float] = None
    soul_xp_gained: Optional[int] = None
    soul_restore_percent: Optional[float] = None
```

---

## Deterministic RNG

### HMAC-Seeded Recipe

```python
seed_string = f"{user_id}|{session_id}|{action_id}|{config_version}|{timestamp}"
seed_hash = HMAC-SHA256(secret_key, seed_string)
rng = random.Random(int(seed_hash[:16], 16))  # 64-bit seed
```

**Key Properties**:
- Same inputs → same outcome (deterministic)
- Config version changes → outcomes change (controlled by config)
- Server-controlled (can't be manipulated by client)
- Includes `config_version` in seed so config changes affect outcomes

---

## Resolution Pipeline

### Order of Operations (Fixed Sequence)

1. **Compute RNG** from `SeedParts` (HMAC-seeded)
2. **Compute Base Stats** from config (all 7 canonical stats)
3. **Build Mods List** from:
   - Clone traits (from `trait_mods()`)
   - SELF level & practices (from `self_mods()`)
   - Womb durability (from `womb_mods()`)
   - Global attention (from `attention_mods()`)
4. **Aggregate Mods** using `aggregate()` helper:
   - Apply all 'add' operations first
   - Then apply all 'mult' operations
5. **Apply Global Invariants** using `clamp_stats()`:
   - `0 ≤ success_chance + death_chance ≤ 1`
   - `time_mult ∈ [0.5, 2.0]`
   - `reward_mult, xp_mult, cost_mult ∈ [0.5, 3.0]`
6. **Check Feral Attacks** (if attention ≥ yellow/red threshold):
   - Roll for attack probability
   - Apply feral effects as additional mods
   - Re-clamp stats
7. **Final Roll** (death/success/failure)
8. **Calculate Rewards** (loot, XP, etc.)
9. **Build Terms** (for explainability)
10. **Return Outcome**

---

## Configuration Schema

### `data/outcomes_config.json`

```json
{
  "config_version": "expeditions_v1",
  
  "expeditions": {
    "MINING": {
      "base_death_prob": 0.12,
      "base_xp": 10,
      "rewards": {
        "Tritanium": [8, 16],
        "Metal Ore": [6, 12]
      },
      "trait_effects": {
        "PWC": {
          "death_chance": {
            "op": "add",
            "value_per_point": -0.008
          },
          "reward_mult": {
            "op": "add",
            "value_per_point": 0.02
          }
        },
        // ... other traits (SSC, MGC, DLT, ENF, ELK, FRK)
      }
    },
    // ... COMBAT, EXPLORATION
  },
  
  "clone_kind_compatibility": {
    "MINING": {
      "MINER": {
        "death_chance_mult": 0.5,
        "notes": "MINER on MINING = 50% safer"
      },
      "VOLATILE": {
        "death_chance_mult": 1.5,
        "notes": "VOLATILE on MINING = 50% more dangerous"
      }
    }
    // ... COMBAT, EXPLORATION
  },
  
  "xp_modifiers": {
    "MINER_XP_MULT": 1.25
  },
  
  "attention": {
    "bands": {
      "yellow": 30,
      "red": 60
    },
    "feral_attack_prob": {
      "yellow": 0.08,
      "red": 0.18
    },
    "effects": {
      "expedition": {
        "death_add": {
          "yellow": 0.02,
          "red": 0.05
        }
      },
      "gather": {
        "time_mult": 1.10,
        "cost_mult": 1.05
      },
      "grow": {
        "time_mult": 1.10,
        "cost_mult": 1.05
      },
      "upload": {
        "notes": "Warning only, no mechanical change"
      }
    }
  },
  
  "gather": {
    "resources": {
      "Tritanium": {
        "base_amount": [5, 12],
        "base_time": [12, 20],
        "attention_delta": 5.0
      }
      // ... other resources
    },
    "practice_xp": {
      "kinetic": 2
    }
  },
  
  "grow": {
    "base_costs": {
      "BASIC": {
        "Synthetic": 6,
        "Organic": 4,
        "Shilajit": 1
      }
      // ... MINER, VOLATILE
    },
    "cost_inflate_per_level": 0.05,
    "soul_split_base": 0.08,
    "soul_split_variance": 0.02,
    "attention_delta": 5.0,
    "practice_xp": {
      "constructive": 6
    },
    "time_base": {
      "BASIC": [30, 45]
      // ... MINER, VOLATILE
    }
  },
  
  "upload": {
    "soul_xp_retain_range": [0.6, 0.9],
    "soul_restore_per_100_xp": 0.5,
    "attention_delta": 0.0
  }
}
```

---

## Trait System Integration

### Clone Traits (7 Traits)

- **PWC** (Pilot-Wave Coupling): Faster execution, safer
- **SSC** (Static Shear Cohesion): Stronger structure, safer
- **MGC** (Morphogenetic Cohesion): Stable growth, safer
- **DLT** (Differential-Drift Tolerance): Helps with incompatible missions
- **ENF** (Exotronic Noise Floor): Low noise = safer, high noise = riskier but higher rewards
- **ELK** (Entropic Luck): Reduces death chance
- **FRK** (Feralization Risk): Increases death chance

### Trait Effects

**Formula**: `(trait_value - 5) * value_per_point`

- Trait value 5 = neutral (0 effect)
- Values 0-4 = negative offset → reduces positive effects, increases negative effects
- Values 6-10 = positive offset → increases positive effects, increases negative effects
- Per-point effects configured in `outcomes_config.json`

**Example**: ELK with value 7 on MINING expedition:
- `(7 - 5) * (-0.01) = -0.02` → death_chance reduced by 2%

**Special Case: ENF (Exotronic Noise Floor)**
- Low ENF (0-4): Negative offset → reduces death_chance (safer) but also reduces reward_mult (less rewards)
- High ENF (6-10): Positive offset → increases death_chance (riskier) but increases reward_mult (more rewards)
- The linear model automatically handles this without special-case logic

### Deterministic Trait Generation

Traits are generated deterministically using HMAC:
```python
seed = HMAC-SHA256(secret_key, f"{self_name}|{womb_id}|{clone_id}|{timestamp}")
rng = random.Random(seed)
traits = {trait_code: rng.randint(0, 10) for trait in TRAIT_LIST}
```

**Integration**: Traits are read by `trait_mods()` in the outcome engine, which converts trait values to modifiers based on config.

---

## Action Resolvers

### `resolve_expedition(ctx: OutcomeContext) -> Outcome`

**Inputs**: Clone, expedition kind (MINING/COMBAT/EXPLORATION), SELF level, practices, attention, womb durability

**Process**:
1. Base death probability from config
2. XP reduces death chance (each 100 XP = -2%, capped at -10%)
3. Trait mods (PWC, SSC, MGC, ENF, ELK, FRK, DLT)
4. Clone kind compatibility mods (MINER on MINING = 50% safer)
5. Practice mods (Kinetic L2+ = +10% XP on MINING/COMBAT)
6. Feral attack check (if attention ≥ yellow/red)
7. Roll for death/success
8. Calculate rewards with `reward_mult`
9. Calculate XP with `xp_mult`

**Output**: `Outcome` with result, loot, xp_gained, feral_attack (if occurred)

---

### `resolve_gather(ctx: OutcomeContext) -> Outcome`

**Inputs**: Resource type, womb durability, attention

**Process**:
1. Base amount range from config
2. Base time range from config
3. Womb durability affects time (lower = slower)
4. Feral attack check (affects time_mult and cost_mult)
5. Deterministic amount and time from RNG

**Output**: `Outcome` with loot (resource amount), time_seconds, feral_attack (if occurred)

---

### `resolve_grow(ctx: OutcomeContext) -> Outcome`

**Inputs**: Clone kind, SELF level, soul_percent, womb durability, attention

**Process**:
1. Base costs from config
2. **SELF tapering**: `cost_mult = (1.0 + cost_inflate_per_level) ^ (level - 1)`
3. Practice cost reduction (Constructive L2+ = 15% cheaper)
4. Feral attack check (affects time_mult and cost_mult)
5. Deterministic soul split percentage
6. Check sufficient soul
7. Deterministic time calculation

**Output**: `Outcome` with cost, soul_split_percent, time_seconds, feral_attack (if occurred)

**Note**: Cost calculation uses exponential scaling with SELF level, making high-level clones more expensive.

---

### `resolve_upload(ctx: OutcomeContext) -> Outcome`

**Inputs**: Clone (with XP), current soul_percent

**Process**:
1. Calculate total clone XP
2. Deterministic SELF XP retention (60-90% range)
3. **Quality-based soul restoration**: `total_xp * 0.5% per 100 XP` (uncapped, can exceed 100%)
4. Feral attack check (warning only, no mechanical change)

**Output**: `Outcome` with soul_xp_gained, soul_restore_percent, feral_attack (warning only)

**Note**: High-quality clones (high XP) can restore soul above 100%, rewarding quality over quantity.

---

## Feral Attack System

### Attention Bands

- **Yellow**: ≥30 attention (8% attack probability)
- **Red**: ≥60 attention (18% attack probability)

### Per-Action Effects

- **Expedition**: `death_chance += 0.02` (Yellow) / `+0.05` (Red)
- **Gather**: `time_mult *= 1.10`, `cost_mult *= 1.05`
- **Grow**: `time_mult *= 1.10`, `cost_mult *= 1.05`
- **Upload**: Warning only (no mechanical change)

### Integration

Feral attacks are checked **after aggregate+clamp, before final roll**. Effects are applied as additional mods so they appear in the explanation breakdown.

---

## Explainability

### Debug Mode

Set `DEBUG_OUTCOMES=true` environment variable to enable explanation breakdown.

### Explanation Structure

```python
{
  "death_chance": {
    "base": 0.12,
    "mods": [
      {"source": "Trait:ELK(7)", "op": "add", "value": -0.02},
      {"source": "KindMatch:MINER_on_MINING", "op": "mult", "value": 0.5},
      {"source": "FeralAttack:YELLOW", "op": "add", "value": 0.02}
    ],
    "final": 0.05
  },
  "reward_mult": {
    "base": 1.0,
    "mods": [
      {"source": "Trait:PWC(8)", "op": "add", "value": 0.06},
      {"source": "Practice:Cognitive_L2+", "op": "mult", "value": 1.10}
    ],
    "final": 1.16
  },
  // ... other stats
  "amount": {...},  // Action-specific terms
  "time": {...}
}
```

---

## Integration Points

### Handlers (`game/rules.py`)

Handlers build `OutcomeContext`, call resolver, apply side-effects:

```python
# Example: run_expedition()
ctx = OutcomeContext(
    action='expedition',
    clone=c,
    self_level=state.soul_level(),
    practices=state.practices_xp,
    global_attention=state.global_attention,
    womb_durability=womb_durability,
    expedition_kind=kind,
    config=CONFIG,
    outcomes_config=OUTCOMES_CONFIG,
    seed_parts=seed_parts
)

outcome = resolve_expedition(ctx)

# Apply outcome to state
if outcome.result == 'death':
    # Handle death
else:
    # Apply rewards and XP
```

### Endpoints (`backend/routers/game.py`)

Endpoints:
1. Store `session_id` in state temporarily for seed generation
2. Call handler (which uses outcome engine)
3. Emit `feral.attack` event if attack occurred
4. Include attack message in API response
5. Clean up temporary state attribute

---

## Hardening & Validation

### Seed Validation

- All seed parts must be non-empty
- `config_version` required for deterministic seeding
- Consistent encoding (UTF-8)

### Context Validation

- Required fields validated before resolution
- Clone required for expedition/upload
- Resource/kind required for gather/grow

### Global Invariants

- All probabilities clamped to [0, 1]
- All multipliers clamped to reasonable ranges
- `success_chance + death_chance ≤ 1` enforced

---

## Testing Strategy

### Property Tests

1. **Fixed seed → fixed outcome**: Same `SeedParts` → identical outcome
2. **Success/death bands**: Within expected ranges per tier/risk
3. **Config version changes**: Changing `config_version` changes outcomes deterministically

### Golden Tests

- Snapshot outcomes for canonical contexts
- Alert on drift (config change? bug?)

### Replay Tests

- Recompute from stored inputs → matches persisted outcome

---

## Design Decisions

### Why HMAC-Seeded RNG?

- Deterministic: Same inputs → same outcome
- Server-controlled: Can't be manipulated by client
- Config version included: Config changes affect outcomes
- Reproducible: Can replay outcomes for debugging

### Why Canonical Stats?

- Single source of truth for all game mechanics
- Easy to reason about: All modifiers target same stats
- Enforced from day 1: Prevents future refactors
- Clear separation: Base stats vs. modifiers

### Why Config in JSON?

- Easy to tweak: No code changes needed
- Versioned: Config version in RNG seed
- Per-trait per-point: Linear math, easy tuning
- Single file: All game tuning in one place

### Why Mod Aggregation?

- Clear order: Add first, then mult
- Single helper: Reused across all actions
- Transparent: Can see all modifiers in explanation

### Why Feral Attacks After Aggregate+Clamp?

- Ensures base stats are valid before attack
- Attack effects are clearly visible in breakdown
- Can be re-clamped after attack

---

## Usage for Game Design

### Tuning Expedition Difficulty

Edit `data/outcomes_config.json`:

```json
{
  "expeditions": {
    "MINING": {
      "base_death_prob": 0.15,  // Increase base difficulty
      "trait_effects": {
        "ELK": {
          "death_chance": {
            "value_per_point": -0.015  // Make ELK more powerful
          }
        }
      }
    }
  }
}
```

**Important**: Change `config_version` to `"expeditions_v2"` so outcomes change deterministically.

### Adding New Trait Effects

1. Add trait to `trait_effects` in config
2. Specify `op` ("add" or "mult")
3. Specify `value_per_point` (effect per point above/below 5)
4. Trait system automatically applies it

### Adjusting Feral Attack Rates

```json
{
  "attention": {
    "feral_attack_prob": {
      "yellow": 0.10,  // Increase from 0.08
      "red": 0.25      // Increase from 0.18
    }
  }
}
```

### Modifying Clone Costs

```json
{
  "grow": {
    "cost_inflate_per_level": 0.08,  // Increase from 0.05 (steeper scaling)
    "base_costs": {
      "BASIC": {
        "Synthetic": 8,  // Increase base cost
        "Organic": 5
      }
    }
  }
}
```

---

## Key Files

- **`backend/engine/outcomes.py`** - Core outcome resolution logic
- **`data/outcomes_config.json`** - All game tuning
- **`game/rules.py`** - Handlers that use outcome engine
- **`backend/routers/game.py`** - Endpoints that integrate outcome engine
- **`core/config.py`** - Loads outcomes_config.json, exports `OUTCOMES_CONFIG`

---

## Success Criteria

✅ All critical dependencies fixed  
✅ Expeditions deterministic and explainable  
✅ Config in JSON (easy to tweak)  
✅ Feral attacks integrated  
✅ All actions migrated (expedition, gather, grow, upload)  
✅ Tests pass  
✅ No performance regression  
✅ Can roll back any phase independently  
✅ Explanation breakdown available (DEBUG_OUTCOMES flag)  
✅ Trait system fully integrated  

---

## Next Steps for Game Design

1. **Tune base probabilities**: Adjust `base_death_prob` in config
2. **Balance trait effects**: Modify `value_per_point` for each trait
3. **Adjust feral attack rates**: Change `feral_attack_prob` in config
4. **Test scenarios**: Use `DEBUG_OUTCOMES=true` to see calculation breakdown
5. **Iterate quickly**: Change config → bump `config_version` → test outcomes

---

## Example: Designing a New Expedition Type

1. Add to `expeditions` in `outcomes_config.json`:
```json
"ARCHAEOLOGY": {
  "base_death_prob": 0.10,
  "base_xp": 15,
  "rewards": {
    "Shilajit": [1, 3],
    "Organic": [2, 5]
  },
  "trait_effects": {
    // Copy from EXPLORATION or customize
  }
}
```

2. Update `VALID_EXPEDITION_KINDS` in `backend/routers/game.py`

3. Bump `config_version` to `"expeditions_v2"`

4. Test with `DEBUG_OUTCOMES=true` to verify calculations

---

## Trait System Compatibility

✅ **Fully Compatible**: All 7 traits (PWC, SSC, MGC, DLT, ENF, ELK, FRK) are configured in `outcomes_config.json`  
✅ **Deterministic Generation**: Traits generated via HMAC (same inputs → same traits)  
✅ **Per-Point Effects**: Linear formula `(trait_value - 5) * value_per_point`  
✅ **Special Cases**: DLT only applies to incompatible missions, ENF uses linear model (low/high handled by config values)  
✅ **Integration**: `trait_mods()` reads from config and converts to modifiers  

**No additional work needed** - trait system is fully integrated with outcome engine.

---

## Summary

The Outcome Engine provides:
- **Deterministic outcomes** via HMAC-seeded RNG
- **Config-driven tuning** via JSON (no code changes)
- **Transparent calculations** via explanation breakdown
- **Consistent pipeline** for all game actions
- **Easy iteration** for game design and balancing

All game actions (expeditions, gather, grow, upload) now use the same deterministic, canonical stats pipeline with proper trait integration, feral attack handling, and explainability.

