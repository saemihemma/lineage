"""
Womb (Assembler) management functions
Handles womb creation, attacks, attention decay, repair, and unlock conditions
"""
from typing import List, Optional, Tuple
import time
import random
import json
from pathlib import Path
from core.models import Womb
from core.config import CONFIG
from data.loader import load_data
from game.state import GameState

# Load feral drone messages
_feral_messages_data = load_data().get("feral_drone_messages", {})
_FERAL_DRONE_MESSAGES = _feral_messages_data.get("messages", [
    "Feral drone swarm detected. Womb integrity compromised."
])


def get_unlocked_womb_count(state: GameState) -> int:
    """
    Calculate how many wombs the player has unlocked based on practice levels.
    
    Unlock conditions:
    - Start with 1 womb available (can build first womb without requirements)
    - +1 when any Practice reaches Level 4
    - +1 when any Practice reaches Level 7
    - +1 when two Practices reach Level 9
    - Cap at WOMB_MAX_COUNT
    """
    max_count = CONFIG.get("WOMB_MAX_COUNT", 4)
    existing_count = len(state.wombs)
    
    # Always start with 1 womb available (first womb has no requirements)
    base_unlocked = 1
    
    # Get practice levels
    kinetic_level = state.practice_level("Kinetic")
    cognitive_level = state.practice_level("Cognitive")
    constructive_level = state.practice_level("Constructive")
    
    levels = [kinetic_level, cognitive_level, constructive_level]
    max_level = max(levels) if levels else 0
    
    # Count practices at L9
    practices_at_l9 = sum(1 for level in levels if level >= 9)
    
    # Apply unlock conditions for additional wombs
    additional_unlocks = 0
    if CONFIG.get("WOMB_UNLOCK_ANY_PRACTICE_L4", True) and max_level >= 4:
        additional_unlocks += 1
    if CONFIG.get("WOMB_UNLOCK_ANY_PRACTICE_L7", True) and max_level >= 7:
        additional_unlocks += 1
    if CONFIG.get("WOMB_UNLOCK_TWO_PRACTICES_L9", True) and practices_at_l9 >= 2:
        additional_unlocks += 1
    
    # Total unlocked = base (1) + additional unlocks
    total_unlocked = base_unlocked + additional_unlocks
    
    # Cap at max count
    return min(total_unlocked, max_count)


def find_active_womb(state: GameState) -> Optional[Womb]:
    """
    Find an active (functional) womb.
    Returns the first functional womb (or None if none exist).
    Note: Attention is now global, so we just need any functional womb.
    """
    functional_wombs = [w for w in state.wombs if w.is_functional()]
    if not functional_wombs:
        return None
    
    # Return first functional womb (attention is global, not per-womb)
    return functional_wombs[0]


def check_womb_available(state: GameState) -> bool:
    """Check if at least one functional womb is available"""
    return find_active_womb(state) is not None


def get_attention_gain_multiplier(state: GameState) -> float:
    """
    Calculate attention gain multiplier based on Cognitive practice level.
    Cognitive L3+ reduces attention decay (increases gain efficiency).
    """
    threshold = CONFIG.get("WOMB_SYNERGY_THRESHOLD", 3)
    mult = CONFIG.get("WOMB_SYNERGY_COGNITIVE_ATTENTION_MULT", 0.95)
    
    if state.practice_level("Cognitive") >= threshold:
        return mult
    return 1.0


def get_attack_chance_multiplier(state: GameState) -> float:
    """
    Calculate attack chance/damage multiplier based on Kinetic practice level.
    Kinetic L3+ reduces attack chance and severity.
    """
    threshold = CONFIG.get("WOMB_SYNERGY_THRESHOLD", 3)
    mult = CONFIG.get("WOMB_SYNERGY_KINETIC_ATTACK_MULT", 0.90)
    
    if state.practice_level("Kinetic") >= threshold:
        return mult
    return 1.0


def get_repair_cost_multiplier(state: GameState) -> float:
    """
    Calculate repair cost/time multiplier based on Constructive practice level.
    Constructive L3+ reduces repair costs and time.
    """
    threshold = CONFIG.get("WOMB_SYNERGY_THRESHOLD", 3)
    mult = CONFIG.get("WOMB_SYNERGY_CONSTRUCTIVE_REPAIR_MULT", 0.85)
    
    if state.practice_level("Constructive") >= threshold:
        return mult
    return 1.0


def gain_attention(state: GameState, womb_id: Optional[int] = None) -> GameState:
    """
    Gain global attention (typically called after actions like grow_clone, build_womb, expeditions).
    Attention is global (shared across all wombs), not per-womb.
    
    Returns new state with updated global attention.
    """
    new_state = state.copy()
    
    # Initialize global_attention if not present (migration)
    if not hasattr(new_state, 'global_attention'):
        new_state.global_attention = CONFIG.get("WOMB_GLOBAL_ATTENTION_INITIAL", 0.0)
    
    # Calculate attention gain with synergy
    base_gain = CONFIG.get("WOMB_ATTENTION_GAIN_ON_ACTION", 5.0)
    mult = get_attention_gain_multiplier(new_state)
    gain = base_gain * mult
    
    # Increase global attention (cap at max)
    max_attention = CONFIG.get("WOMB_GLOBAL_ATTENTION_MAX", 100.0)
    new_state.global_attention = min(
        max_attention,
        new_state.global_attention + gain
    )
    
    return new_state


def decay_attention(state: GameState) -> GameState:
    """
    Apply global attention decay based on idle time.
    Called on state changes to simulate idle decay.
    
    Returns new state with decayed global attention.
    """
    new_state = state.copy()
    
    # Initialize global_attention if not present (migration)
    if not hasattr(new_state, 'global_attention'):
        new_state.global_attention = CONFIG.get("WOMB_GLOBAL_ATTENTION_INITIAL", 0.0)
    
    # Calculate hours since last save
    current_time = time.time()
    hours_elapsed = max(0.0, (current_time - new_state.last_saved_ts) / 3600.0)
    
    # Decay per hour
    decay_per_hour = CONFIG.get("WOMB_ATTENTION_DECAY_PER_HOUR", 1.0)
    total_decay = decay_per_hour * hours_elapsed
    
    # Cognitive synergy reduces decay
    mult = get_attention_gain_multiplier(new_state)
    # Inverse: if mult < 1.0, decay is reduced
    decay_mult = 2.0 - mult  # If mult=0.95, decay_mult=1.05 (reduced decay)
    actual_decay = total_decay * decay_mult
    
    # Apply decay to global attention
    new_state.global_attention = max(0.0, new_state.global_attention - actual_decay)
    
    return new_state


def attack_womb(state: GameState) -> Tuple[GameState, Optional[int], Optional[str]]:
    """
    Check for feral drone attack based on global attention level.
    Attack probability scales linearly with attention (0% attention = 0% chance, 100% attention = max_chance).
    
    Returns:
        (new_state, attacked_womb_id, message)
        If no attack occurs, returns (state, None, None)
    """
    new_state = state.copy()
    
    if not new_state.wombs:
        return new_state, None, None
    
    # Initialize global_attention if not present (migration)
    if not hasattr(new_state, 'global_attention'):
        new_state.global_attention = CONFIG.get("WOMB_GLOBAL_ATTENTION_INITIAL", 0.0)
    
    # Calculate attack probability based on global attention
    # Linear scaling: 0% attention = 0% chance, 100% attention = max_chance
    max_attention = CONFIG.get("WOMB_GLOBAL_ATTENTION_MAX", 100.0)
    max_attack_chance = CONFIG.get("WOMB_FERAL_ATTACK_CHANCE_AT_MAX", 0.25)
    
    if max_attention <= 0:
        return new_state, None, None
    
    # Calculate attack chance based on attention percentage
    attention_percent = new_state.global_attention / max_attention
    base_attack_chance = attention_percent * max_attack_chance
    
    # Apply Kinetic synergy (reduces attack chance)
    mult = get_attack_chance_multiplier(new_state)
    attack_chance = base_attack_chance * mult
    
    # Roll for attack
    if new_state.rng.random() >= attack_chance:
        return new_state, None, None  # No attack
    
    # Select random functional womb to attack
    functional_wombs = [w for w in new_state.wombs if w.is_functional()]
    if not functional_wombs:
        return new_state, None, None
    
    attacked_womb = new_state.rng.choice(functional_wombs)
    
    # Calculate damage with Kinetic synergy
    damage_min = CONFIG.get("WOMB_ATTACK_DAMAGE_MIN", 5.0)
    damage_max = CONFIG.get("WOMB_ATTACK_DAMAGE_MAX", 15.0)
    base_damage = new_state.rng.uniform(damage_min, damage_max)
    damage = base_damage * mult  # Kinetic reduces damage
    
    # Apply damage to womb
    attacked_womb.durability = max(0.0, attacked_womb.durability - damage)
    
    # Reduce global attention after attack (10% ± variance)
    reduction_base = CONFIG.get("WOMB_ATTACK_ATTENTION_REDUCTION_BASE", 10.0)
    reduction_variance = CONFIG.get("WOMB_ATTACK_ATTENTION_REDUCTION_VARIANCE", 2.0)
    reduction = reduction_base + new_state.rng.uniform(-reduction_variance, reduction_variance)
    new_state.global_attention = max(0.0, new_state.global_attention - reduction)
    
    # Select random thematic message
    if _FERAL_DRONE_MESSAGES:
        message = new_state.rng.choice(_FERAL_DRONE_MESSAGES)
    else:
        message = "Feral drone swarm detected. Womb integrity compromised."
    
    # Add damage info to message
    message += f" Womb {attacked_womb.id} took {damage:.1f} damage. Durability: {attacked_womb.durability:.1f}/{attacked_womb.max_durability:.1f}"
    
    return new_state, attacked_womb.id, message


def calculate_repair_cost(womb: Womb) -> dict:
    """
    Calculate resource cost to repair womb to full durability.
    Returns dict of resource costs.
    """
    missing_durability = womb.max_durability - womb.durability
    cost_per_point = CONFIG.get("WOMB_REPAIR_COST_PER_DURABILITY", {"Tritanium": 0.5, "Metal Ore": 0.3})
    
    cost = {}
    for resource, per_point in cost_per_point.items():
        cost[resource] = int(missing_durability * per_point)
    
    return cost


def calculate_repair_time(state: GameState, womb: Womb) -> int:
    """
    Calculate repair time in seconds based on missing durability and Constructive synergy.
    """
    missing_durability = womb.max_durability - womb.durability
    max_durability = womb.max_durability
    
    if max_durability == 0:
        return 0
    
    # Base time scales with percentage missing
    time_min = CONFIG.get("WOMB_REPAIR_TIME_MIN", 20)
    time_max = CONFIG.get("WOMB_REPAIR_TIME_MAX", 40)
    
    # Scale time based on damage percentage
    damage_percent = missing_durability / max_durability
    base_time = time_min + (time_max - time_min) * damage_percent
    
    # Apply Constructive synergy
    mult = get_repair_cost_multiplier(state)
    repair_time = int(base_time * mult)
    
    return max(1, repair_time)  # At least 1 second


def create_womb(womb_id: int) -> Womb:
    """Create a new womb with max durability (attention is global, not per-womb)"""
    max_durability = CONFIG.get("WOMB_MAX_DURABILITY", 100.0)
    
    return Womb(
        id=womb_id,
        durability=max_durability,
        max_durability=max_durability
    )


def check_and_apply_womb_systems(state: GameState) -> Tuple[GameState, Optional[str]]:
    """
    Check and apply womb systems on state changes:
    - Decay attention
    - Random attacks
    
    This should be called after state-changing operations.
    Updates last_saved_ts to current time for accurate decay calculation.
    
    Returns:
        (new_state, attack_message)
        attack_message is None if no attack occurred, otherwise contains the thematic message
    """
    import time
    # Update last_saved_ts to current time so decay is calculated from now
    new_state = state.copy()
    new_state.last_saved_ts = time.time()
    
    # Apply decay and attacks
    new_state = decay_attention(new_state)
    new_state, attacked_id, attack_msg = attack_womb(new_state)
    
    return new_state, attack_msg

