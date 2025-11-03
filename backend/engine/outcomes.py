"""
Outcome Engine - Deterministic outcome resolution system

Phase 2: Simple outcome resolver for expeditions to prove the pattern.
"""
import random
import hmac
import hashlib
from typing import Dict, List, Any, Literal, Optional, Tuple
from dataclasses import dataclass
from core.models import Clone
from core.config import CONFIG


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
    config: Dict  # From CONFIG
    seed_parts: SeedParts  # For deterministic RNG


def trait_mods(clone: Clone, expedition_kind: str) -> List[Mod]:
    """Generate mods from clone traits"""
    mods = []
    traits = clone.traits or {}
    
    elk = traits.get("ELK", 5)  # Entropic Luck (default 5 = neutral)
    frk = traits.get("FRK", 5)  # Feralization Risk (default 5 = neutral)
    dlt = traits.get("DLT", 5)  # Differential-Drift Tolerance (default 5 = neutral)
    
    # ELK reduces death (each point above 5 = -1% probability per point)
    elk_bonus = (elk - 5) / 100.0
    mods.append(Mod(target='death_chance', op='add', value=-elk_bonus, source=f'Trait:ELK({elk})'))
    
    # FRK increases death (each point above 5 = +1% probability per point)
    frk_penalty = (frk - 5) / 100.0
    mods.append(Mod(target='death_chance', op='add', value=frk_penalty, source=f'Trait:FRK({frk})'))
    
    # DLT helps with incompatible missions (reduces penalty)
    incompatible = False
    if expedition_kind == "MINING" and clone.kind == "VOLATILE":
        incompatible = True
    elif expedition_kind == "COMBAT" and clone.kind == "MINER":
        incompatible = True
    
    if incompatible:
        dlt_bonus = (dlt - 5) / 200.0  # Range: -2.5% to +2.5%
        mods.append(Mod(target='death_chance', op='add', value=-dlt_bonus, source=f'Trait:DLT({dlt})_IncompatibleMission'))
    
    return mods


def self_mods(self_level: int, practices: Dict[str, int], expedition_kind: str, clone_kind: str) -> List[Mod]:
    """Generate mods from SELF level and practices"""
    mods = []
    
    # XP reduces death chance (each 100 XP = -2% death probability, capped at -10%)
    # This is handled per-clone, so we'll pass it differently
    
    # Clone kind vs expedition compatibility
    if expedition_kind == "MINING" and clone_kind == "MINER":
        mods.append(Mod(target='death_chance', op='mult', value=0.5, source='KindMatch:MINER_on_MINING'))
    elif expedition_kind == "COMBAT" and clone_kind == "VOLATILE":
        mods.append(Mod(target='death_chance', op='mult', value=0.6, source='KindMatch:VOLATILE_on_COMBAT'))
    elif expedition_kind == "EXPLORATION" and clone_kind == "BASIC":
        mods.append(Mod(target='death_chance', op='mult', value=0.8, source='KindMatch:BASIC_on_EXPLORATION'))
    
    # Incompatible missions are more dangerous
    if expedition_kind == "MINING" and clone_kind == "VOLATILE":
        mods.append(Mod(target='death_chance', op='mult', value=1.5, source='KindMismatch:VOLATILE_on_MINING'))
    elif expedition_kind == "COMBAT" and clone_kind == "MINER":
        mods.append(Mod(target='death_chance', op='mult', value=1.3, source='KindMismatch:MINER_on_COMBAT'))
    
    # Practice bonuses
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
    """
    # 1. Compute RNG from seed_parts (HMAC recipe)
    rng = random.Random(compute_rng_seed(ctx.seed_parts))
    
    # 2. Compute base stats from config (all 7 canonical stats)
    base_death_prob = ctx.config.get("DEATH_PROB", 0.12)
    base_xp = {"MINING": 10, "COMBAT": 12, "EXPLORATION": 8}.get(ctx.expedition_kind, 10)
    
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
    
    # 3. Build mods list (hardcoded sources for now):
    mods = []
    mods.extend(trait_mods(ctx.clone, ctx.expedition_kind))
    mods.extend(self_mods(ctx.self_level, ctx.practices, ctx.expedition_kind, ctx.clone.kind))
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
    
    # 7. Calculate rewards with reward_mult
    loot = {}
    yield_mult = final_stats.reward_mult
    
    rewards_config = ctx.config.get("REWARDS", {}).get(ctx.expedition_kind, {})
    for res, (a, b) in rewards_config.items():
        base_amt = rng.randint(a, b)
        loot[res] = int(round(base_amt * yield_mult))
    
    # Calculate XP with xp_mult
    base_xp = {"MINING": 10, "COMBAT": 12, "EXPLORATION": 8}.get(ctx.expedition_kind, 10)
    
    # Clone kind bonus (MINER on MINING gets bonus)
    if ctx.expedition_kind == "MINING" and ctx.clone.kind == "MINER":
        base_xp_mult = ctx.config.get("MINER_XP_MULT", 1.25)
    else:
        base_xp_mult = 1.0
    
    gained = int(round(base_xp * base_xp_mult * final_stats.xp_mult))
    xp_gained = {ctx.expedition_kind: gained}
    
    # Shilajit chance (EXPLORATION only)
    shilajit_found = False
    if ctx.expedition_kind == "EXPLORATION":
        if rng.random() < 0.15:
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

