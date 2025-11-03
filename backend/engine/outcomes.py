"""
Outcome Engine - Deterministic outcome resolution system

Phase 2: Simple outcome resolver for expeditions to prove the pattern.
Phase 3: Uses outcomes_config.json for all expedition configuration.
"""
import random
import hmac
import hashlib
from typing import Dict, List, Any, Literal, Optional, Tuple
from dataclasses import dataclass
from core.models import Clone
from core.config import CONFIG, OUTCOMES_CONFIG, OUTCOMES_CONFIG_VERSION


@dataclass
class SeedParts:
    """Parts used to compute deterministic RNG seed via HMAC"""
    user_id: str  # session_id
    session_id: str
    action_id: str  # expedition_id or task_id
    config_version: str  # from config JSON (will be "legacy" until Phase 3)
    timestamp: float  # action start time


def compute_rng_seed(parts: SeedParts) -> int:
    """
    HMAC-based seed: user|session|action_id|config_version
    
    Returns deterministic integer seed for random.Random.
    """
    # Combine parts deterministically
    seed_str = f"{parts.user_id}|{parts.session_id}|{parts.action_id}|{parts.config_version}|{parts.timestamp}"
    
    # Use HMAC-SHA256 to generate seed
    h = hmac.new(b"outcome_engine_seed", seed_str.encode('utf-8'), hashlib.sha256)
    # Convert to integer (use first 8 bytes to fit in int64)
    seed_int = int.from_bytes(h.digest()[:8], byteorder='big')
    # Ensure positive (modulo max int32)
    return seed_int % (2**31 - 1)


@dataclass
class Mod:
    """Modifier applied to a canonical stat"""
    target: Literal['time_mult', 'success_chance', 'death_chance', 'reward_mult', 'xp_mult', 'cost_mult', 'attention_delta']
    op: Literal['add', 'mult']
    value: float
    source: str  # e.g., 'Trait:ELK', 'SELF:Level 5', 'Womb:Durability 80%'


@dataclass
class CanonicalStats:
    """All canonical stats enforced from day 1, even if not all used yet"""
    time_mult: float = 1.0
    success_chance: float = 1.0  # For expeditions, this is implicit (death or success)
    death_chance: float = 0.0
    reward_mult: float = 1.0
    xp_mult: float = 1.0
    cost_mult: float = 1.0
    attention_delta: float = 0.0


def aggregate(mods: List[Mod], base_stats: CanonicalStats) -> CanonicalStats:
    """
    Apply all mods in order: add first, then mult.
    Single helper reused across all actions.
    """
    stats = CanonicalStats(
        time_mult=base_stats.time_mult,
        success_chance=base_stats.success_chance,
        death_chance=base_stats.death_chance,
        reward_mult=base_stats.reward_mult,
        xp_mult=base_stats.xp_mult,
        cost_mult=base_stats.cost_mult,
        attention_delta=base_stats.attention_delta
    )
    
    # Separate add and mult mods by target
    add_mods = {target: [] for target in ['time_mult', 'success_chance', 'death_chance', 'reward_mult', 'xp_mult', 'cost_mult', 'attention_delta']}
    mult_mods = {target: [] for target in ['time_mult', 'success_chance', 'death_chance', 'reward_mult', 'xp_mult', 'cost_mult', 'attention_delta']}
    
    for mod in mods:
        if mod.op == 'add':
            add_mods[mod.target].append(mod.value)
        elif mod.op == 'mult':
            mult_mods[mod.target].append(mod.value)
    
    # Apply adds first, then mults
    stats.time_mult += sum(add_mods['time_mult'])
    for mult_val in mult_mods['time_mult']:
        stats.time_mult *= mult_val
    
    stats.success_chance += sum(add_mods['success_chance'])
    for mult_val in mult_mods['success_chance']:
        stats.success_chance *= mult_val
    
    stats.death_chance += sum(add_mods['death_chance'])
    for mult_val in mult_mods['death_chance']:
        stats.death_chance *= mult_val
    
    stats.reward_mult += sum(add_mods['reward_mult'])
    for mult_val in mult_mods['reward_mult']:
        stats.reward_mult *= mult_val
    
    stats.xp_mult += sum(add_mods['xp_mult'])
    for mult_val in mult_mods['xp_mult']:
        stats.xp_mult *= mult_val
    
    stats.cost_mult += sum(add_mods['cost_mult'])
    for mult_val in mult_mods['cost_mult']:
        stats.cost_mult *= mult_val
    
    stats.attention_delta += sum(add_mods['attention_delta'])
    for mult_val in mult_mods['attention_delta']:
        stats.attention_delta *= mult_val
    
    return stats


def clamp_stats(stats: CanonicalStats) -> CanonicalStats:
    """
    Apply global invariants:
    - 0 ≤ success_chance + death_chance ≤ 1
    - time_mult ∈ [0.5, 2.0]
    - reward_mult, xp_mult, cost_mult ∈ [0.5, 3.0]
    """
    # Clamp multipliers
    stats.time_mult = max(0.5, min(2.0, stats.time_mult))
    stats.reward_mult = max(0.5, min(3.0, stats.reward_mult))
    stats.xp_mult = max(0.5, min(3.0, stats.xp_mult))
    stats.cost_mult = max(0.5, min(3.0, stats.cost_mult))
    
    # Clamp death_chance
    stats.death_chance = max(0.0, min(1.0, stats.death_chance))
    
    # Ensure success + death ≤ 1 (death has priority)
    if stats.success_chance + stats.death_chance > 1.0:
        stats.success_chance = max(0.0, 1.0 - stats.death_chance)
    
    # Clamp success_chance
    stats.success_chance = max(0.0, min(1.0, stats.success_chance))
    
    return stats


@dataclass
class Outcome:
    """Result of outcome resolution"""
    result: Literal['success', 'death']
    stats: CanonicalStats  # Final computed stats
    loot: Dict[str, int]
    xp_gained: Dict[str, int]
    mods_applied: List[Mod]  # For explainability (Phase 7)
    terms: Dict[str, Any]  # Internal structure for Phase 7 explainability
    shilajit_found: bool = False


@dataclass
class OutcomeContext:
    """Context for resolving an outcome"""
    action: Literal['expedition']  # Start with just expeditions
    clone: Clone
    self_level: int
    practices: Dict[str, int]  # Kinetic, Cognitive, Constructive levels
    global_attention: float
    womb_durability: float  # Best womb durability
    expedition_kind: str
    config: Dict  # From CONFIG (for backward compat, practice levels, etc.)
    outcomes_config: Dict[str, Any]  # Phase 3: From outcomes_config.json
    seed_parts: SeedParts  # For deterministic RNG


def trait_mods(clone: Clone, expedition_kind: str, outcomes_config: Dict[str, Any]) -> List[Mod]:
    """
    Generate mods from clone traits.
    Phase 3: Reads trait effects from outcomes_config.json.
    """
    mods = []
    traits = clone.traits or {}
    
    # Get expedition config for trait effects
    expedition_config = outcomes_config.get("expeditions", {}).get(expedition_kind, {})
    trait_effects = expedition_config.get("trait_effects", {})
    
    # Process each trait effect from config
    for trait_code, trait_config in trait_effects.items():
        trait_value = traits.get(trait_code, 5)  # Default 5 = neutral
        
        # Get effect config (death_chance, reward_mult, etc.)
        for target, effect_config in trait_config.items():
            op = effect_config.get("op", "add")
            value_per_point = effect_config.get("value_per_point", 0.0)
            
            # Calculate effect: (trait_value - 5) * value_per_point
            # This makes trait value 5 = neutral (0 effect)
            trait_offset = trait_value - 5
            total_value = trait_offset * value_per_point
            
            # Special handling for DLT - only applies to incompatible missions
            if trait_code == "DLT" and target == "death_chance":
                incompatible = False
                if expedition_kind == "MINING" and clone.kind == "VOLATILE":
                    incompatible = True
                elif expedition_kind == "COMBAT" and clone.kind == "MINER":
                    incompatible = True
                if incompatible:
                    mods.append(Mod(target=target, op=op, value=total_value, source=f'Trait:{trait_code}({trait_value})_IncompatibleMission'))
            else:
                mods.append(Mod(target=target, op=op, value=total_value, source=f'Trait:{trait_code}({trait_value})'))
    
    return mods


def self_mods(self_level: int, practices: Dict[str, int], expedition_kind: str, clone_kind: str, outcomes_config: Dict[str, Any]) -> List[Mod]:
    """
    Generate mods from SELF level and practices.
    Phase 3: Reads clone kind compatibility from outcomes_config.json.
    """
    mods = []
    
    # XP reduces death chance (each 100 XP = -2% death probability, capped at -10%)
    # This is handled per-clone in resolve_expedition, so we don't handle it here
    
    # Clone kind vs expedition compatibility (from config)
    clone_compat = outcomes_config.get("clone_kind_compatibility", {}).get(expedition_kind, {})
    clone_kind_config = clone_compat.get(clone_kind)
    
    if clone_kind_config:
        mult = clone_kind_config.get("death_chance_mult", 1.0)
        notes = clone_kind_config.get("notes", "")
        # Determine if it's a match or mismatch based on mult value
        if mult < 1.0:
            mods.append(Mod(target='death_chance', op='mult', value=mult, source=f'KindMatch:{clone_kind}_on_{expedition_kind}'))
        elif mult > 1.0:
            mods.append(Mod(target='death_chance', op='mult', value=mult, source=f'KindMismatch:{clone_kind}_on_{expedition_kind}'))
    
    # Practice bonuses (still use CONFIG for practice levels as they're not in outcomes config yet)
    kinetic_level = practices.get("Kinetic", 0) // CONFIG["PRACTICE_XP_PER_LEVEL"]
    if expedition_kind in ["MINING", "COMBAT"] and kinetic_level >= 2:
        # Mining/combat XP multiplier (from perk_mining_xp_mult)
        mods.append(Mod(target='xp_mult', op='mult', value=1.10, source='Practice:Kinetic_L2+'))
    
    cognitive_level = practices.get("Cognitive", 0) // CONFIG["PRACTICE_XP_PER_LEVEL"]
    if expedition_kind == "EXPLORATION" and cognitive_level >= 2:
        # Exploration yield multiplier (from perk_exploration_yield_mult)
        mods.append(Mod(target='reward_mult', op='mult', value=1.10, source='Practice:Cognitive_L2+'))
    
    # SELF level small buffs (not yet in current system, but prepare for it)
    # For now, minimal effect
    
    return mods


def womb_mods(womb_durability: float) -> List[Mod]:
    """Generate mods from womb durability"""
    mods = []
    
    # Durability affects time (lower durability = slower)
    # For now, expeditions don't use time_mult, but we compute it anyway
    if womb_durability < 50.0:
        # Severely damaged womb slows operations
        mods.append(Mod(target='time_mult', op='mult', value=1.1, source='Womb:LowDurability'))
    
    return mods


def attention_mods(global_attention: float) -> List[Mod]:
    """Generate mods from global attention"""
    mods = []
    
    # High attention increases death chance
    # For expeditions, attention band effects will be added in Phase 4
    # For now, minimal effect
    
    return mods


def resolve_expedition(ctx: OutcomeContext) -> Outcome:
    """
    Resolve expedition outcome using deterministic, canonical stats system.
    
    Phase 2: Proves the pattern for expeditions only.
    Phase 3: Reads all expedition config from outcomes_config.json.
    """
    # 1. Compute RNG from seed_parts (HMAC recipe)
    rng = random.Random(compute_rng_seed(ctx.seed_parts))
    
    # 2. Compute base stats from outcomes_config (all 7 canonical stats)
    expedition_config = ctx.outcomes_config.get("expeditions", {}).get(ctx.expedition_kind, {})
    base_death_prob = expedition_config.get("base_death_prob", 0.12)
    base_xp = expedition_config.get("base_xp", 10)
    
    base_stats = CanonicalStats(
        time_mult=1.0,  # Expeditions complete immediately, but compute anyway
        success_chance=1.0,  # Implicit: either death or success
        death_chance=base_death_prob,
        reward_mult=1.0,
        xp_mult=1.0,
        cost_mult=1.0,
        attention_delta=5.0  # Gain attention on successful expedition
    )
    
    # XP reduces death chance (each 100 XP = -2% death probability, capped at -10%)
    total_xp = ctx.clone.total_xp()
    xp_reduction = min(0.10, total_xp / 100.0 * 0.02)
    base_stats.death_chance -= xp_reduction
    
    # 3. Build mods list (Phase 3: reads from outcomes_config):
    mods = []
    mods.extend(trait_mods(ctx.clone, ctx.expedition_kind, ctx.outcomes_config))
    mods.extend(self_mods(ctx.self_level, ctx.practices, ctx.expedition_kind, ctx.clone.kind, ctx.outcomes_config))
    mods.extend(womb_mods(ctx.womb_durability))
    mods.extend(attention_mods(ctx.global_attention))
    
    # 4. Aggregate mods using single helper
    final_stats = aggregate(mods, base_stats)
    
    # 5. Apply global invariants (clamps)
    final_stats = clamp_stats(final_stats)
    
    # Final clamp: death probability between 0.5% and 50%
    final_stats.death_chance = max(0.005, min(0.50, final_stats.death_chance))
    
    # 6. Roll for death/success
    roll = rng.random()
    if roll < final_stats.death_chance:
        result = 'death'
    else:
        result = 'success'
    
    # 7. Calculate rewards with reward_mult (from outcomes_config)
    loot = {}
    yield_mult = final_stats.reward_mult
    
    rewards_config = expedition_config.get("rewards", {})
    for res, reward_range in rewards_config.items():
        a, b = reward_range[0], reward_range[1]  # Convert list to tuple-like
        base_amt = rng.randint(a, b)
        loot[res] = int(round(base_amt * yield_mult))
    
    # Calculate XP with xp_mult (from outcomes_config)
    # Clone kind bonus (MINER on MINING gets bonus)
    xp_modifiers = ctx.outcomes_config.get("xp_modifiers", {})
    base_xp_mult = xp_modifiers.get("MINER_XP_MULT", 1.25) if (ctx.expedition_kind == "MINING" and ctx.clone.kind == "MINER") else 1.0
    
    gained = int(round(base_xp * base_xp_mult * final_stats.xp_mult))
    xp_gained = {ctx.expedition_kind: gained}
    
    # Shilajit chance (from outcomes_config)
    shilajit_found = False
    if ctx.expedition_kind == "EXPLORATION":
        shilajit_chance = expedition_config.get("shilajit_chance", 0.15)
        if rng.random() < shilajit_chance:
            shilajit_found = True
            loot["Shilajit"] = loot.get("Shilajit", 0) + 1
    
    # Build terms structure for Phase 7 explainability
    terms = {
        "death_chance": {
            "base": base_death_prob,
            "xp_reduction": -xp_reduction,
            "mods": [{"source": m.source, "op": m.op, "value": m.value} for m in mods if m.target == 'death_chance'],
            "final": final_stats.death_chance
        },
        "reward_mult": {
            "base": 1.0,
            "mods": [{"source": m.source, "op": m.op, "value": m.value} for m in mods if m.target == 'reward_mult'],
            "final": final_stats.reward_mult
        },
        "xp_mult": {
            "base": 1.0,
            "mods": [{"source": m.source, "op": m.op, "value": m.value} for m in mods if m.target == 'xp_mult'],
            "final": final_stats.xp_mult
        }
    }
    
    return Outcome(
        result=result,
        stats=final_stats,
        loot=loot,
        xp_gained=xp_gained,
        mods_applied=mods,
        terms=terms,
        shilajit_found=shilajit_found
    )

