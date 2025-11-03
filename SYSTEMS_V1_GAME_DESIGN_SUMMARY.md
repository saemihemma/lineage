# Systems v1 — Game Design & Implementation Summary

**Version:** systems_v1  
**Date:** 2025  
**Purpose:** Complete reference for product management and game design collaboration

---

## Table of Contents

1. [Core Systems Overview](#core-systems-overview)
2. [Resource Economy](#resource-economy)
3. [Clone System](#clone-system)
4. [Traits & Effects](#traits--effects)
5. [SELF Progression](#self-progression)
6. [Practices & Unlocks](#practices--unlocks)
7. [Womb System](#womb-system)
8. [Expedition System](#expedition-system)
9. [Attention & Feral Attacks](#attention--feral-attacks)
10. [Aging & Biological Days](#aging--biological-days)
11. [Deterministic RNG](#deterministic-rng)
12. [Configuration System](#configuration-system)

---

## Core Systems Overview

### Action Types

1. **Gather Resources** — Collect materials from environment
2. **Grow Clones** — Create new clones in wombs
3. **Run Expeditions** — Send clones on missions (MINING, COMBAT, EXPLORATION)
4. **Upload Clones** — Sacrifice clones to restore SELF soul and gain XP
5. **Build Wombs** — Construct assembly facilities
6. **Repair Wombs** — Restore womb durability

### Core Mechanics

- **Deterministic Outcomes**: All actions use HMAC-seeded RNG for reproducible results
- **Config-Driven**: All numerical values in `config/gameplay.json`
- **Modifier System**: Base stats + modifiers → clamped final stats → outcome
- **Canonical Stats**: 7 stats applied uniformly (time_mult, success_chance, death_chance, reward_mult, xp_mult, cost_mult, attention_delta)

---

## Resource Economy

### Resource Types

1. **Tritanium** — Metal alloy, primary construction material
2. **Metal Ore** — Raw metal, construction material
3. **Biomass** — Organic matter, biological cloning
4. **Synthetic** — Synthetic materials, clone growth
5. **Organic** — Organic compounds, clone growth & repair
6. **Shilajit** — Rare mineral, advanced cloning (rare drop)

### Resource Faucets (Sources)

#### Gathering
- **Base Amounts** (deterministic from seed):
  - Tritanium: 5-12 per gather
  - Metal Ore: 4-10 per gather
  - Biomass: 3-8 per gather
  - Synthetic: 2-6 per gather
  - Organic: 3-7 per gather
  - Shilajit: Always 1 (rare, long gather time)

- **Base Times** (deterministic):
  - Tritanium: 12-20 seconds
  - Metal Ore: 10-16 seconds
  - Biomass: 6-12 seconds
  - Synthetic: 16-24 seconds
  - Organic: 8-14 seconds
  - Shilajit: 58-73 seconds

- **Attention Gain**: +5 per gather action
- **Practice XP**: Kinetic +2 per gather

#### Expeditions (Rewards)
- **MINING**:
  - Tritanium: 8-16 (base, before reward_mult)
  - Metal Ore: 6-12 (base, before reward_mult)
  
- **COMBAT**:
  - Biomass: 3-7 (base, before reward_mult)
  - Synthetic: 2-5 (base, before reward_mult)
  
- **EXPLORATION**:
  - Tritanium: 2-6 (base, before reward_mult)
  - Metal Ore: 2-6 (base, before reward_mult)
  - Organic: 1-3 (base, before reward_mult)
  - Shilajit: 15% chance of +1 (bonus)

- **Reward Multipliers Apply**:
  - Trait effects (PWC, SSC, MGC, ENF can boost rewards)
  - SELF level givebacks (up to +25% at high levels)

### Resource Sinks (Costs)

#### Clone Growth Costs (Base)
- **BASIC Clone**:
  - Synthetic: 6
  - Organic: 4
  - Shilajit: 1

- **MINER Clone**:
  - Synthetic: 8
  - Metal Ore: 8
  - Organic: 5
  - Shilajit: 1

- **VOLATILE Clone**:
  - Synthetic: 10
  - Biomass: 8
  - Organic: 6
  - Shilajit: 3

- **Cost Multipliers**:
  - SELF level: Piecewise curve (L4: 0.5x slope, L7: 0.25x slope, L10: 0x slope, max 1.75x)
  - Constructive practice: 0.995^level (multiplicative reduction)
  - Feral attacks: +5% cost_mult (yellow/red band)

#### Womb Building
- **Base Cost**:
  - Tritanium: 30
  - Metal Ore: 20
  - Biomass: 5

- **Cost Multipliers**:
  - SELF level: Inflates with level
  - Constructive practice: Reduces cost

#### Womb Repair
- **Fixed Cost** (per repair):
  - Tritanium: 8
  - Organic: 6

- **Time**: 25 seconds base (reduced by Constructive practice)

---

## Clone System

### Clone Kinds

1. **BASIC** — Tier 1, always available
   - Base costs: 6 Synthetic, 4 Organic, 1 Shilajit
   - Time: 30-45 seconds
   - No special bonuses

2. **MINER** — Tier 2, requires Constructive L4
   - Base costs: 8 Synthetic, 8 Metal Ore, 5 Organic, 1 Shilajit
   - Time: 35-50 seconds
   - **Bonus**: +25% XP on MINING expeditions
   - **Compatibility**: 50% safer on MINING, 30% more dangerous on COMBAT

3. **VOLATILE** — Tier 3, requires Constructive L9
   - Base costs: 10 Synthetic, 8 Biomass, 6 Organic, 3 Shilajit
   - Time: 40-55 seconds
   - **Compatibility**: 60% safer on COMBAT, 50% more dangerous on MINING

### Clone Growth

- **Soul Split**: 8% base ± 2% variance (deterministic from seed)
- **Success Check**: Always succeeds (1.0 base), but can fail if insufficient soul
- **Attention Gain**: +5 per clone grown
- **Practice XP**: Constructive +6 per clone

### Clone Death

- **Death Probability**: See [Expedition System](#expedition-system)
- **XP Loss on Death**: 25-75% of total XP (random, non-deterministic)
- **Clone Marked**: `alive = False`, removed from spaceship if applied

### Clone Upload

- **SELF XP Retention**: 60-90% of clone's total XP (deterministic from seed)
- **Soul Restoration**: 
  - Base: `total_xp * 0.5 / 100` (0.5% per 100 XP)
  - **Uncapped** — Can exceed 100% for high-XP clones
  - **Age Bonus**: `min(bio_days * 0.02, 4.0)` additional %
    - Example: 100 bio_days = +2% bonus, capped at +4%
- **Attention Gain**: 0 (no attention from uploads)
- **Practice XP**: None (upload doesn't award practice XP)

---

## Traits & Effects

### Trait List

All traits use neutral value of **5** (no effect at neutral).

1. **PWC (Pilot-Wave Coupling)**
   - Effect: Faster temporal harmonics
   - Death: -0.008 per point (cap: -0.04)
   - Reward: +0.02 per point (cap: +0.10)
   - Example: PWC 8 = -0.024 death, +0.06 reward

2. **SSC (Static Shear Cohesion)**
   - Effect: Stronger frame integrity
   - Death: -0.012 per point (cap: -0.06)
   - Reward: +0.01 per point (cap: +0.05)
   - Example: SSC 10 = -0.06 death, +0.05 reward

3. **MGC (Morphogenetic Cohesion)**
   - Effect: Stable growth channels
   - Death: -0.010 per point (cap: -0.05)
   - Reward: +0.015 per point (cap: +0.075)
   - Example: MGC 7 = -0.02 death, +0.03 reward

4. **DLT (Differential-Drift Tolerance)**
   - Effect: Coherence in unstable zones
   - Death: -0.005 per point **only on incompatible missions** (cap: -0.025)
   - Incompatible: VOLATILE on MINING, MINER on COMBAT
   - Example: DLT 8 on incompatible = -0.015 death

5. **ENF (Exotronic Noise Floor)**
   - Effect: Predictable low, volatile high
   - Death: +0.008 per point (cap: +0.04)
   - Reward: +0.03 per point (cap: +0.15)
   - High risk, high reward trait
   - Example: ENF 10 = +0.04 death, +0.15 reward

6. **ELK (Entropic Luck)**
   - Effect: Fortune favors bold
   - Death: -0.010 per point (cap: -0.05)
   - Example: ELK 9 = -0.04 death

7. **FRK (Feralization Risk)**
   - Effect: Tendency to go rogue
   - Death: +0.010 per point (cap: +0.05)
   - Example: FRK 10 = +0.05 death

### Trait Generation

- **Deterministic**: Uses HMAC-seeded RNG based on:
  - `self_name` (normalized)
  - `womb_id`
  - `clone_id`
  - `timestamp`
- **Range**: 0-10 per trait
- **Default**: 5 (neutral) if trait missing

---

## SELF Progression

### SELF Level Calculation

- **XP per Level**: 100 XP
- **Level Formula**: `soul_xp // 100`
- **Soul XP Sources**: Upload clones (60-90% retention)

### SELF Level Effects (Givebacks)

Per level above 1:

1. **Reward Multiplier**: +0.0025 per level (additive, cap: +25% total)
   - Example: Level 10 = +0.0225 = +2.25% rewards
   - Example: Level 50 = +0.1225 = +12.25% rewards (capped at 25%)

2. **Time Multiplier**: 0.997^level (multiplicative, min: 0.80)
   - Example: Level 10 = 0.997^10 = 0.970 = 3% faster
   - Example: Level 50 = 0.997^50 = 0.860 = 14% faster (capped at 20%)

3. **Death Chance Reduction**: -0.0005 per level (additive, floor: -0.10)
   - Example: Level 10 = -0.0045 = -0.45% death
   - Example: Level 20 = -0.0095 = -0.95% death (capped at -10%)

### Clone Cost Curve (Piecewise)

- **Base Multiplier**: 1.0
- **Per Level Add**: 0.02
- **Breakpoints**:
  - Level 4: Slope × 0.5 (halves growth rate)
  - Level 7: Slope × 0.25 (quarters growth rate)
  - Level 10: Slope × 0.0 (stops growing)
- **Max Multiplier**: 1.75

**Example Progression**:
- Level 1: 1.00x
- Level 4: ~1.06x (before breakpoint)
- Level 5: ~1.07x (after L4 breakpoint, slower growth)
- Level 7: ~1.10x (before L7 breakpoint)
- Level 8: ~1.11x (after L7 breakpoint, very slow)
- Level 10: ~1.14x (before L10 breakpoint)
- Level 11+: 1.14x (no growth after L10, capped at 1.75)

---

## Practices & Unlocks

### Practice Tracks

1. **Kinetic** — Physical actions
2. **Cognitive** — Mental tasks
3. **Constructive** — Building/creation

### Practice XP Sources

- **Kinetic**: +2 per gather, +5 per MINING/COMBAT expedition
- **Cognitive**: +5 per EXPLORATION expedition
- **Constructive**: +6 per clone grown, +10 per womb built
- **XP per Level**: 100 XP

### Practice Effects

#### Kinetic (Level 1+)
- **Success Chance**: +0.002 per level (for expeditions)
  - Example: Level 10 = +0.02 = +2% success
- **Reward Multiplier**: +0.002 per level (for expeditions)
  - Example: Level 10 = +0.02 = +2% rewards
- **Applies to**: MINING, COMBAT expeditions

#### Cognitive (Level 1+)
- **Time Multiplier**: 0.997^level (multiplicative)
  - Example: Level 10 = 0.997^10 = 0.970 = 3% faster
  - Applies to all actions (global)

#### Constructive (Level 1+)
- **Cost Multiplier**: 0.995^level (multiplicative)
  - Example: Level 10 = 0.995^10 = 0.951 = 4.9% cost reduction
  - Applies to all actions (global)

### Practice Unlocks

#### Tier 2 Clones (MINER)
- **Requirement**: Constructive Level 4
- **Error**: "Cannot grow MINER. Requires Constructive practice level 4 (current: X)"

#### Tier 3 Clones (VOLATILE)
- **Requirement**: Constructive Level 9
- **Error**: "Cannot grow VOLATILE. Requires Constructive practice level 9 (current: X)"

#### Multiple Wombs
- **Requirement**: Constructive Level 6
- **Error**: "Cannot build multiple wombs. Requires Constructive practice level 6 (current: X)"
- **Note**: First womb has no requirement

---

## Womb System

### Womb Properties

- **Max Durability**: 100.0
- **Initial Durability**: 100.0
- **Attention**: Global (shared across all wombs), not per-womb

### Womb Durability Effects

- **Time Penalty**: `time_mult *= (1.0 + (100 - durability) / 10 * 0.02)`
  - Example: 80 durability = +4% time (1.04x)
  - Example: 50 durability = +10% time (1.10x)
  - Example: 20 durability = +16% time (1.16x)

### Womb Overload

When multiple wombs are active:

- **Attention Gain**: +3 per active womb over 1
  - Example: 2 wombs = +3 attention delta
  - Example: 3 wombs = +6 attention delta
- **Time Multiplier**: 1.02^(active_wombs - 1)
  - Example: 2 wombs = 1.02x time
  - Example: 3 wombs = 1.0404x time

### Womb Repair

- **Cost**: Fixed {Tritanium: 8, Organic: 6}
- **Time**: 25 seconds base (reduced by Constructive practice)
- **Restore Amount**: Random 15-30% of max durability
  - Example: 20% restore = +20 durability on 100 max
  - Example: 30% restore = +30 durability on 100 max
- **Restore Source**: Deterministic from RNG seed

### Womb Unlocks (Existing System)

- **Base**: 1 womb always available
- **L4 Any Practice**: +1 womb
- **L7 Any Practice**: +1 womb
- **L9 Two Practices**: +1 womb
- **Max**: 4 wombs total

### Womb Building

- **Cost**: Inflates with SELF level
- **Time**: 30-45 seconds base
- **Practice XP**: Constructive +10
- **Attention Gain**: +5 (if wombs exist)

---

## Expedition System

### Expedition Types

1. **MINING**
   - Base Death: 10%
   - Base XP: 10
   - Rewards: Tritanium 8-16, Metal Ore 6-12
   - Practice XP: Kinetic +5
   - Attention Gain: +8

2. **COMBAT**
   - Base Death: 14%
   - Base XP: 12
   - Rewards: Biomass 3-7, Synthetic 2-5
   - Practice XP: Kinetic +5
   - Attention Gain: +8

3. **EXPLORATION**
   - Base Death: 12%
   - Base XP: 8
   - Rewards: Tritanium 2-6, Metal Ore 2-6, Organic 1-3
   - Shilajit: 15% chance of +1
   - Practice XP: Cognitive +5
   - Attention Gain: +8

### Death Probability Calculation

**Base Formula**:
```
final_death = base_death_prob
  - XP_reduction (max -10%)
  + trait_mods (with caps)
  + SELF_level_mods (with caps)
  + clone_kind_compatibility (mult)
  + feral_attack_penalty (if applicable)
```

**XP Reduction**:
- Each 100 XP = -2% death (max -10%)
- Example: 500 XP = -10% death
- Example: 100 XP = -2% death

**Clamping**:
- Final death chance: 0.5% minimum, 50% maximum
- Ensures some risk remains, but never guaranteed death

### Clone Kind Compatibility

- **MINER on MINING**: 50% safer (death × 0.5)
- **MINER on COMBAT**: 30% more dangerous (death × 1.3)
- **VOLATILE on COMBAT**: 40% safer (death × 0.6)
- **VOLATILE on MINING**: 50% more dangerous (death × 1.5)
- **BASIC on EXPLORATION**: 20% safer (death × 0.8)

### XP Gained

- **Base XP**: Per expedition type (10, 12, or 8)
- **MINER Bonus**: +25% XP on MINING expeditions
- **XP Multiplier**: From practices and traits
- **Final**: `base_xp * kind_mult * xp_mult`

---

## Attention & Feral Attacks

### Attention System

- **Type**: Global (shared across all wombs)
- **Initial**: 0%
- **Max**: 100%
- **Decay**: 1.0 per hour (idle)

### Attention Bands

- **Yellow**: 30-59% attention
- **Red**: 60-100% attention

### Attention Gain (Per Action)

- **Gather**: +5
- **Grow Clone**: +5
- **Expedition**: +8
- **Upload**: +0
- **Build Womb**: +5 (if wombs exist)
- **Womb Overload**: +3 per active womb over 1

### Feral Attack Probabilities

- **Yellow Band**: 8% chance per action
- **Red Band**: 18% chance per action
- **Roll**: Determined after mod aggregation, before final outcome

### Feral Attack Effects (Per Action)

#### Gather/Grow
- **Time Multiplier**: ×1.10 (+10% time)
- **Cost Multiplier**: ×1.05 (+5% cost)

#### Expedition
- **Death Add**: 
  - Yellow: +0.02 (+2%)
  - Red: +0.05 (+5%)

#### Upload
- **Effect**: Warning only (no mechanical change)

### Womb Damage (Feral Attacks)

- **Enabled**: Yes
- **Damage Range**: 1-5% of max durability
  - Example: 100 max = 1-5 durability damage
- **Applied to**: Active womb(s) during feral attack

### Attention Reduction (After Attack)

- **Base Reduction**: 10% ± 2% (random)
- **Range**: 8-12% reduction
- **Applied**: After attack occurs

---

## Aging & Biological Days

### Biological Days Calculation

- **Rate**: 20 biological days per 1 real day
- **Formula**: `elapsed_seconds * (20 / 86400)`
- **Example**: 1 real day = 20 bio days
- **Example**: 1 real hour = ~0.83 bio days

### Upload Age Bonus

- **Formula**: `min(bio_days * 0.02, 4.0)`
- **Example**: 100 bio days = +2% soul restore
- **Example**: 200+ bio days = +4% soul restore (capped)
- **Applied**: Additional to base soul restoration

### Aging Risk (Future)

- **Enabled**: false (disabled)
- **Threshold**: 120 biological days
- **Effect**: +0.0001 death per day (if enabled)

---

## Deterministic RNG

### Seed Components

All actions use deterministic RNG seeded from:

1. **self_name** (normalized: trimmed, lowercased)
2. **womb_id** (active womb ID, or 0)
3. **task_started_at** (timestamp when task queued)
4. **config_version** (from gameplay.json, currently "systems_v1")

### Seed Format

```
HMAC-SHA256(
  key = "outcome_engine_seed",
  message = "{self_name}|{womb_id}|{task_started_at}|{config_version}"
)
```

### Determinism Guarantee

- **Same inputs** → **Same outputs**
- Changing config_version changes all outcomes (prevents stale config)
- Changing self_name changes outcomes (per-player variance)
- Task timestamp ensures different outcomes per action

### Non-Deterministic Elements

- **XP Loss on Death**: 25-75% random (acceptable per design)
- **Trait Generation**: Uses deterministic seed, but different seed components

---

## Configuration System

### Config File

**Location**: `config/gameplay.json`

### Config Version

- **Current**: `"systems_v1"`
- **Included in RNG seed**: Yes (ensures config changes invalidate old outcomes)

### Config Structure

```json
{
  "config_version": "systems_v1",
  "attention": { ... },
  "expeditions": { ... },
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

### Config Endpoint

- **URL**: `/api/config/gameplay`
- **Method**: GET
- **ETag Support**: Yes (caching)
- **Returns**: Full gameplay.json merged with computed values

---

## System Interactions

### Complete Flow Example: Expedition

1. **Player sends clone on MINING expedition**
   - Clone: MINER, 200 XP, traits: PWC 8, SSC 6
   - SELF: Level 5
   - Attention: 45% (yellow band)
   - Practices: Kinetic L3, Cognitive L2

2. **Base Stats**:
   - Death: 10% (MINING base)
   - XP: 10 base
   - Rewards: 8-16 Tritanium, 6-12 Metal Ore

3. **Modifiers Applied**:
   - XP reduction: -4% (200 XP / 100 * 0.02)
   - PWC trait: -0.024 death, +0.06 reward
   - SSC trait: -0.012 death, +0.01 reward
   - Clone kind: MINER on MINING = death × 0.5
   - SELF level: -0.002 death, +0.01 reward, 0.985 time
   - Kinetic practice: +0.006 success, +0.006 reward
   - Cognitive practice: 0.994 time

4. **Feral Attack Check**:
   - Attention: 45% (yellow band)
   - Roll: 8% chance
   - If attack: +2% death

5. **Final Stats** (after aggregation & clamping):
   - Death: ~3.5% (after all reductions)
   - Rewards: ~1.08x multiplier
   - XP: ~12.5 (with MINER bonus)

6. **Roll for Death**:
   - Random roll: 0.0-1.0
   - If roll < 0.035: Clone dies
   - Else: Clone survives, gains rewards & XP

7. **Outcome**:
   - Success: Resources added, XP gained, attention +8
   - Death: Clone marked dead, loses 25-75% XP, attention +8 (attack info returned)

---

## Key Design Principles

1. **Deterministic but Varied**: Same inputs = same outputs, but different players/actions = different outcomes
2. **Config-Driven**: All numbers in JSON, easy to tune
3. **Risk/Reward Balance**: High-risk builds (ENF) get high rewards, safe builds (PWC/SSC) get moderate rewards
4. **Progression Gates**: Practices unlock features, SELF level gives bonuses
5. **Attention Management**: High attention = more risk (feral attacks), creates tension
6. **Resource Constraints**: Costs scale with SELF level (piecewise), encourages resource management
7. **Clone Investment**: High-XP clones are safer, but losing them is costly
8. **Age Matters**: Older clones give better upload bonuses, encourages keeping clones alive

---

## Quick Reference: All Percentages

### Death Probabilities
- MINING base: 10%
- COMBAT base: 14%
- EXPLORATION base: 12%
- XP reduction: -2% per 100 XP (max -10%)
- Minimum death: 0.5%
- Maximum death: 50%

### Reward Multipliers
- PWC cap: +10%
- SSC cap: +5%
- MGC cap: +7.5%
- ENF cap: +15%
- SELF level cap: +25%

### Time Multipliers
- Cognitive practice: 0.997^level (min 0.80)
- SELF level: 0.997^level (min 0.80)
- Womb durability: +2% per 10 missing durability
- Womb overload: 1.02^(wombs - 1)
- Feral attack: ×1.10

### Cost Multipliers
- Constructive practice: 0.995^level
- SELF level: Piecewise (max 1.75x)
- Feral attack: ×1.05

### Attention
- Gain per gather: +5
- Gain per grow: +5
- Gain per expedition: +8
- Decay per hour: -1.0
- Overload per womb: +3
- Reduction after attack: -8 to -12%

### Soul Restoration
- Base: 0.5% per 100 XP (uncapped)
- Age bonus: 0.02% per bio day (max +4%)
- Example: 1000 XP, 100 bio days = 5% + 2% = 7% restore

---

## Implementation Notes

### Files Modified
- `config/gameplay.json` — All game parameters
- `backend/engine/outcomes.py` — Outcome resolution engine
- `game/rules.py` — Action handlers
- `backend/routers/game.py` — API endpoints
- `core/config.py` — Config loading
- `core/game_logic.py` — Unlock checks
- `game/wombs.py` — Womb system
- `core/models.py` — Biological days

### Testing Recommendations
1. Test death probabilities with low-XP clones
2. Verify trait caps don't exceed limits
3. Test practice unlocks block features correctly
4. Verify deterministic outcomes (same seed = same result)
5. Test attention bands trigger feral attacks
6. Verify upload age bonus scales correctly
7. Test womb repair restores correct amount
8. Verify piecewise cost curve matches expected values

---

**End of Summary**

