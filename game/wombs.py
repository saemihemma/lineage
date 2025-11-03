"""
Womb (Assembler) management functions
Handles womb creation, attacks, attention decay, repair, and unlock conditions
"""
from typing import List, Optional, Tuple
import time
from core.models import Womb
from core.config import CONFIG
from game.state import GameState


def get_unlocked_womb_count(state: GameState) -> int:
    """
    Calculate how many wombs the player has unlocked based on practice levels.
    
    Unlock conditions:
    - Start with 0 wombs (must build first)
    - +1 when any Practice reaches Level 4
    - +1 when any Practice reaches Level 7
    - +1 when two Practices reach Level 9
    - Cap at WOMB_MAX_COUNT
    """
    max_count = CONFIG.get("WOMB_MAX_COUNT", 4)
    unlocked = 0
    
    # Get practice levels
    kinetic_level = state.practice_level("Kinetic")
    cognitive_level = state.practice_level("Cognitive")
    constructive_level = state.practice_level("Constructive")
    
    levels = [kinetic_level, cognitive_level, constructive_level]
    max_level = max(levels) if levels else 0
    
    # Count practices at L9
    practices_at_l9 = sum(1 for level in levels if level >= 9)
    
    # Apply unlock conditions
    if CONFIG.get("WOMB_UNLOCK_ANY_PRACTICE_L4", True) and max_level >= 4:
        unlocked += 1
    if CONFIG.get("WOMB_UNLOCK_ANY_PRACTICE_L7", True) and max_level >= 7:
        unlocked += 1
    if CONFIG.get("WOMB_UNLOCK_TWO_PRACTICES_L9", True) and practices_at_l9 >= 2:
        unlocked += 1
    
    # Clamp to max count (minimum 1 if player already has wombs built)
    existing_count = len(state.wombs)
    if existing_count > 0 and unlocked == 0:
        unlocked = 1  # At least one if they've built any
    
    return min(unlocked + existing_count, max_count) if unlocked > 0 else max(0, existing_count)


def find_active_womb(state: GameState) -> Optional[Womb]:
    """
    Find an active (functional) womb with highest attention.
    Returns None if no functional womb exists.
    """
    functional_wombs = [w for w in state.wombs if w.is_functional()]
    if not functional_wombs:
        return None
    
    # Return womb with highest attention
    return max(functional_wombs, key=lambda w: w.attention)


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
    Gain attention on a womb (typically called after actions like grow_clone, build_womb).
    If womb_id is None, applies to highest attention functional womb.
    
    Returns new state with updated attention.
    """
    new_state = state.copy()
    
    # Find target womb
    if womb_id is not None:
        target_womb = next((w for w in new_state.wombs if w.id == womb_id), None)
    else:
        target_womb = find_active_womb(new_state)
    
    if target_womb is None:
        return new_state
    
    # Calculate attention gain with synergy
    base_gain = CONFIG.get("WOMB_ATTENTION_GAIN_ON_ACTION", 5.0)
    mult = get_attention_gain_multiplier(new_state)
    gain = base_gain * mult
    
    # Increase attention (cap at max)
    target_womb.attention = min(
        target_womb.max_attention,
        target_womb.attention + gain
    )
    
    return new_state


def decay_attention(state: GameState) -> GameState:
    """
    Apply attention decay based on idle time.
    Called on state changes to simulate idle decay.
    
    Returns new state with decayed attention.
    """
    new_state = state.copy()
    
    if not new_state.wombs:
        return new_state
    
    # Calculate hours since last save (or use a fixed decay per check)
    current_time = time.time()
    hours_elapsed = max(0.0, (current_time - new_state.last_saved_ts) / 3600.0)
    
    # Decay per hour
    decay_per_hour = CONFIG.get("WOMB_ATTENTION_DECAY_PER_HOUR", 1.0)
    total_decay = decay_per_hour * hours_elapsed
    
    # Apply decay to all wombs
    for womb in new_state.wombs:
        if womb.is_functional():
            # Cognitive synergy reduces decay
            mult = get_attention_gain_multiplier(new_state)
            # Inverse: if mult < 1.0, decay is reduced
            decay_mult = 2.0 - mult  # If mult=0.95, decay_mult=1.05 (reduced decay)
            actual_decay = total_decay * decay_mult
            womb.attention = max(0.0, womb.attention - actual_decay)
    
    return new_state


def attack_womb(state: GameState) -> Tuple[GameState, Optional[int], Optional[str]]:
    """
    Randomly attack a womb (called on state changes).
    
    Returns:
        (new_state, attacked_womb_id, message)
        If no attack occurs, returns (state, None, None)
    """
    new_state = state.copy()
    
    if not new_state.wombs:
        return new_state, None, None
    
    # Check attack chance with Kinetic synergy
    base_chance = CONFIG.get("WOMB_ATTACK_CHANCE", 0.15)
    mult = get_attack_chance_multiplier(new_state)
    attack_chance = base_chance * mult
    
    if new_state.rng.random() >= attack_chance:
        return new_state, None, None  # No attack
    
    # Select random womb to attack
    functional_wombs = [w for w in new_state.wombs if w.is_functional()]
    if not functional_wombs:
        return new_state, None, None
    
    attacked_womb = new_state.rng.choice(functional_wombs)
    
    # Calculate damage with Kinetic synergy
    damage_min = CONFIG.get("WOMB_ATTACK_DAMAGE_MIN", 5.0)
    damage_max = CONFIG.get("WOMB_ATTACK_DAMAGE_MAX", 15.0)
    base_damage = new_state.rng.uniform(damage_min, damage_max)
    damage = base_damage * mult  # Kinetic reduces damage
    
    # Apply damage
    attacked_womb.durability = max(0.0, attacked_womb.durability - damage)
    
    message = f"Womb {attacked_womb.id} took {damage:.1f} damage! Durability: {attacked_womb.durability:.1f}/{attacked_womb.max_durability:.1f}"
    
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
    """Create a new womb with max durability and attention"""
    max_durability = CONFIG.get("WOMB_MAX_DURABILITY", 100.0)
    max_attention = CONFIG.get("WOMB_MAX_ATTENTION", 100.0)
    
    return Womb(
        id=womb_id,
        durability=max_durability,
        attention=max_attention,
        max_durability=max_durability,
        max_attention=max_attention
    )


def check_and_apply_womb_systems(state: GameState) -> GameState:
    """
    Check and apply womb systems on state changes:
    - Decay attention
    - Random attacks
    
    This should be called after state-changing operations.
    """
    new_state = decay_attention(state)
    new_state, attacked_id, attack_msg = attack_womb(new_state)
    
    # Note: Attack message can be logged/emitted by caller if needed
    return new_state

