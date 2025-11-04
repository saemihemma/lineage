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


def get_available_grow_slots(state: GameState, active_tasks: dict) -> int:
    """
    Calculate available grow slots based on functional wombs and parallel grow limit.
    
    Returns the number of concurrent grow tasks that can run.
    """
    from core.config import GAMEPLAY_CONFIG
    
    # Count functional wombs
    functional_wombs = [w for w in state.wombs if w.is_functional()]
    functional_count = len(functional_wombs)
    
    if functional_count == 0:
        return 0
    
    # Get parallel grow limit from config
    womb_config = GAMEPLAY_CONFIG.get("wombs", {})
    parallel_limit = womb_config.get("parallel_grow_limit", 4)
    
    # Count active grow tasks
    active_grow_tasks = sum(1 for task_data in active_tasks.values() 
                           if task_data.get('type') == 'grow_clone')
    
    # Available slots = min(functional_wombs, parallel_limit) - active_grow_tasks
    max_slots = min(functional_count, parallel_limit)
    available = max(0, max_slots - active_grow_tasks)
    
    return available


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


def gain_attention(state: GameState, attention_delta: Optional[float] = None, womb_id: Optional[int] = None) -> GameState:
    """
    Gain global attention (typically called after actions like grow_clone, build_womb, expeditions).
    Attention is global (shared across all wombs), not per-womb.
    
    Args:
        state: Current game state
        attention_delta: Amount of attention to gain (if None, uses config default)
        womb_id: Unused (kept for backward compat)
    
    Returns new state with updated global attention.
    """
    new_state = state.copy()
    
    # Initialize global_attention if not present (migration)
    if not hasattr(new_state, 'global_attention'):
        new_state.global_attention = CONFIG.get("WOMB_GLOBAL_ATTENTION_INITIAL", 0.0)
    
    # Use provided attention_delta or fall back to config
    if attention_delta is None:
        # Fallback to old config for backward compat
        base_gain = CONFIG.get("WOMB_ATTENTION_GAIN_ON_ACTION", 5.0)
        mult = get_attention_gain_multiplier(new_state)
        gain = base_gain * mult
    else:
        # Use outcome's attention_delta (from gameplay.json)
        mult = get_attention_gain_multiplier(new_state)
        gain = attention_delta * mult
    
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
    Systems v1: Uses gameplay.json attention bands and probabilities.
    
    Returns:
        (new_state, attacked_womb_id, message)
        If no attack occurs, returns (state, None, None)
    """
    from core.config import GAMEPLAY_CONFIG
    
    new_state = state.copy()
    
    if not new_state.wombs:
        return new_state, None, None
    
    # Initialize global_attention if not present (migration)
    if not hasattr(new_state, 'global_attention'):
        new_state.global_attention = CONFIG.get("WOMB_GLOBAL_ATTENTION_INITIAL", 0.0)
    
    # Get attention config from gameplay.json
    attention_config = GAMEPLAY_CONFIG.get("attention", {})
    womb_damage_config = attention_config.get("womb_damage", {})
    
    # Check if womb damage is enabled
    if not womb_damage_config.get("enabled", True):
        return new_state, None, None
    
    # Get attention bands from config
    bands = attention_config.get("bands", {})
    yellow_threshold = bands.get("yellow", 25)
    red_threshold = bands.get("red", 55)
    
    # Determine attention band
    attention_band = None
    if new_state.global_attention >= red_threshold:
        attention_band = "red"
    elif new_state.global_attention >= yellow_threshold:
        attention_band = "yellow"
    
    # Only attack if in yellow or red band
    if not attention_band:
        return new_state, None, None
    
    # Get attack probability for this band
    feral_attack_probs = attention_config.get("feral_attack_prob", {})
    attack_prob = feral_attack_probs.get(attention_band, 0.0)
    
    # Apply Kinetic synergy (reduces attack chance)
    mult = get_attack_chance_multiplier(new_state)
    attack_chance = attack_prob * mult
    
    # Roll for attack
    if attack_chance <= 0 or new_state.rng.random() >= attack_chance:
        return new_state, None, None  # No attack
    
    # Select random functional womb to attack
    functional_wombs = [w for w in new_state.wombs if w.is_functional()]
    if not functional_wombs:
        return new_state, None, None
    
    attacked_womb = new_state.rng.choice(functional_wombs)
    
    # Calculate damage as percentage of max durability (from gameplay.json)
    damage_min_pct = womb_damage_config.get("min", 0.02)  # 2% of max
    damage_max_pct = womb_damage_config.get("max", 0.06)  # 6% of max
    
    # Apply Kinetic synergy to damage (reduces damage)
    base_damage_pct = new_state.rng.uniform(damage_min_pct, damage_max_pct)
    damage_pct = base_damage_pct * mult  # Kinetic reduces damage
    
    # Calculate absolute damage
    primary_damage = attacked_womb.max_durability * damage_pct
    
    # Apply damage to primary womb
    attacked_womb.durability = max(0.0, attacked_womb.durability - primary_damage)
    
    # Apply splash damage to other functional wombs (10-25% of primary damage)
    womb_config = GAMEPLAY_CONFIG.get("wombs", {})
    splash_range = womb_config.get("feral_splash_damage_mult", [0.10, 0.25])
    splash_min, splash_max = splash_range[0], splash_range[1]
    
    splash_damages = []
    other_wombs = [w for w in functional_wombs if w.id != attacked_womb.id]
    if other_wombs:
        splash_mult = new_state.rng.uniform(splash_min, splash_max)
        splash_damage = primary_damage * splash_mult
        for other_womb in other_wombs:
            other_womb.durability = max(0.0, other_womb.durability - splash_damage)
            splash_damages.append((other_womb.id, splash_damage))
    
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
    
    # Add primary damage info to message
    message += f" Womb {attacked_womb.id + 1} took {primary_damage:.1f} damage ({damage_pct*100:.1f}%). Durability: {attacked_womb.durability:.1f}/{attacked_womb.max_durability:.1f}"
    
    # Add splash damage info if any
    if splash_damages:
        splash_womb_ids = [f"Womb {wid + 1}" for wid, _ in splash_damages]
        splash_msg = f" Splash damage ({splash_mult*100:.1f}%) to {', '.join(splash_womb_ids)}."
        message += splash_msg
    
    return new_state, attacked_womb.id, message


def calculate_repair_cost(womb: Womb, state: GameState) -> dict:
    """
    Calculate resource cost to repair womb.
    
    Cost is 10x per durability point compared to building a new womb.
    Building cost: {"Tritanium": 30, "Metal Ore": 20, "Biomass": 5} for 100 durability
    Per durability: 0.3 Tritanium, 0.2 Metal Ore, 0.05 Biomass
    10x per durability: 3.0 Tritanium, 2.0 Metal Ore, 0.5 Biomass per point
    
    Charges for maximum possible restore amount (30% = 30 durability points).
    """
    from core.config import GAMEPLAY_CONFIG, CONFIG
    from core.game_logic import inflate_costs
    
    # Get base building cost (before inflation)
    base_build_cost = CONFIG["ASSEMBLER_COST"]  # {"Tritanium": 30, "Metal Ore": 20, "Biomass": 5}
    max_durability = womb.max_durability  # Typically 100.0
    
    # Calculate cost per durability point (10x building cost)
    cost_per_durability = {}
    for resource, amount in base_build_cost.items():
        cost_per_durability[resource] = (amount / max_durability) * 10.0
    
    # Get repair config for restore range
    repair_config = GAMEPLAY_CONFIG.get("wombs", {}).get("repair", {})
    restore_range = repair_config.get("restore_range", [0.15, 0.30])
    max_restore_percent = restore_range[1]  # Maximum restore (30%)
    max_restore_durability = max_durability * max_restore_percent  # 30 durability points
    
    # Calculate cost for maximum possible restore
    repair_cost = {}
    for resource, per_point_cost in cost_per_durability.items():
        repair_cost[resource] = int(round(per_point_cost * max_restore_durability))
    
    # Apply SELF level inflation (same as building)
    level = state.soul_level()
    inflated_cost = inflate_costs(repair_cost, level)
    
    return inflated_cost


def calculate_repair_time(state: GameState, womb: Womb) -> int:
    """
    Calculate repair time in seconds.
    
    Systems v1: Uses fixed time from gameplay_config.wombs.repair.time_seconds.
    """
    from core.config import GAMEPLAY_CONFIG
    
    repair_config = GAMEPLAY_CONFIG.get("wombs", {}).get("repair", {})
    base_time = repair_config.get("time_seconds", 25)
    
    # Apply Constructive synergy (reduces time)
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


def apply_passive_durability_decay(state: GameState) -> GameState:
    """
    Apply passive durability decay to wombs over time.
    Wombs naturally degrade at a fixed rate per minute.
    
    Returns new state with decayed womb durability.
    """
    from core.config import GAMEPLAY_CONFIG
    
    new_state = state.copy()
    
    if not new_state.wombs:
        return new_state
    
    # Get passive decay config from gameplay.json
    womb_config = GAMEPLAY_CONFIG.get("wombs", {})
    passive_decay = womb_config.get("passive_decay", {})
    
    if not passive_decay.get("enabled", True):
        return new_state
    
    # Calculate minutes since last save
    current_time = time.time()
    minutes_elapsed = max(0.0, (current_time - new_state.last_saved_ts) / 60.0)
    
    # Decay per minute (fixed rate)
    decay_per_minute = passive_decay.get("damage_per_minute", 2.0)  # 2.0 durability per minute
    
    # Apply decay to each womb
    for womb in new_state.wombs:
        if womb.durability > 0:
            total_damage = decay_per_minute * minutes_elapsed
            
            # Apply damage (but don't let it go below 0)
            womb.durability = max(0.0, womb.durability - total_damage)
    
    return new_state


def check_and_apply_womb_systems(state: GameState) -> Tuple[GameState, Optional[str]]:
    """
    Check and apply womb systems on state changes:
    - Decay attention
    - Passive durability decay
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
    
    # Apply decay, passive durability decay, and attacks
    new_state = decay_attention(new_state)
    new_state = apply_passive_durability_decay(new_state)
    new_state, attacked_id, attack_msg = attack_womb(new_state)
    
    return new_state, attack_msg

