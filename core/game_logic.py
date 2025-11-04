"""Core game logic functions"""
import random
from typing import Dict, List, Tuple, Optional
from core.models import Clone, CLONE_TYPES, TRAIT_LIST
from core.config import CONFIG, GAMEPLAY_CONFIG


def check_practice_unlock(practices_xp: Dict[str, int], unlock_key: str, gameplay_config: Optional[Dict] = None) -> bool:
    """
    Check if a practice unlock is available.
    
    Systems v1: Checks Constructive practice unlocks from gameplay_config.
    
    Args:
        practices_xp: Dictionary of practice XP values
        unlock_key: One of 'tier2', 'tier3', 'multi_womb'
        gameplay_config: Optional config (uses GAMEPLAY_CONFIG if None)
    
    Returns:
        True if unlock is available, False otherwise
    """
    if gameplay_config is None:
        gameplay_config = GAMEPLAY_CONFIG
    
    practices_config = gameplay_config.get("practices", {})
    constructive_config = practices_config.get("Constructive", {})
    unlocks = constructive_config.get("unlocks", {})
    
    required_level = unlocks.get(unlock_key)
    if required_level is None:
        return True  # No unlock requirement
    
    xp_per_level = CONFIG.get("PRACTICE_XP_PER_LEVEL", 100)
    constructive_level = practices_xp.get("Constructive", 0) // xp_per_level
    
    return constructive_level >= required_level


def get_clone_kind_tier(clone_kind: str) -> Optional[str]:
    """
    Get the tier unlock key for a clone kind.
    
    Systems v1: Maps clone kinds to unlock keys.
    - BASIC: None (tier1, always available)
    - MINER: "tier2" (requires Constructive L4)
    - VOLATILE: "tier3" (requires Constructive L9)
    """
    if clone_kind == "BASIC":
        return None  # Always available
    elif clone_kind == "MINER":
        return "tier2"
    elif clone_kind == "VOLATILE":
        return "tier3"
    else:
        return None  # Unknown kind, default to available


def random_traits(rng: random.Random) -> Dict[str, int]:
    """Generate random traits for a clone"""
    traits = {}
    for trait in TRAIT_LIST:
        # Roll 0-10, default to 5
        traits[trait.code] = rng.randint(0, 10)
    return traits


def soul_split_percent(rng: random.Random) -> float:
    """Calculate soul split percentage"""
    base = CONFIG.get("SOUL_SPLIT_BASE", 0.10)
    variance = CONFIG.get("SOUL_SPLIT_VARIANCE", 0.03)
    return max(0.01, base + rng.uniform(-variance, variance))


def award_practice_xp(state, track: str, amount: int):
    """Award practice XP to a track"""
    if track not in state.practices_xp:
        state.practices_xp[track] = 0
    state.practices_xp[track] += amount


def perk_mining_xp_mult(state) -> float:
    """Calculate mining XP multiplier from practices"""
    kinetic_level = state.practices_xp.get("Kinetic", 0) // CONFIG.get("PRACTICE_XP_PER_LEVEL", 100)
    if kinetic_level >= 2:
        return 1.10
    return 1.0


def perk_exploration_yield_mult(state) -> float:
    """Calculate exploration yield multiplier from practices"""
    cognitive_level = state.practices_xp.get("Cognitive", 0) // CONFIG.get("PRACTICE_XP_PER_LEVEL", 100)
    if cognitive_level >= 2:
        return 1.10
    return 1.0


def perk_constructive_cost_mult(state) -> float:
    """Calculate constructive cost multiplier from practices"""
    constructive_level = state.practices_xp.get("Constructive", 0) // CONFIG.get("PRACTICE_XP_PER_LEVEL", 100)
    if constructive_level >= 2:
        return 0.85
    return 1.0


def perk_constructive_craft_time_mult(state) -> float:
    """Calculate constructive craft time multiplier from practices"""
    # For now, return 1.0 (no time reduction from practices)
    # Can be implemented later if needed
    return 1.0


def inflate_costs(costs: Dict[str, int], level: int) -> Dict[str, int]:
    """Inflate costs based on SELF level"""
    if level <= 1:
        return costs.copy()
    # Simple linear inflation (will be replaced by piecewise in outcome engine)
    mult = 1.0 + (level - 1) * 0.05
    return {k: int(round(v * mult)) for k, v in costs.items()}


def can_afford(resources: Dict[str, int], cost: Dict[str, int]) -> bool:
    """Check if resources are sufficient for cost"""
    for resource, amount in cost.items():
        if resources.get(resource, 0) < amount:
            return False
    return True


def spend(resources: Dict[str, int], cost: Dict[str, int]) -> None:
    """Deduct cost from resources (modifies resources in-place)"""
    for resource, amount in cost.items():
        resources[resource] = resources.get(resource, 0) - amount


def format_resource_error(resources: Dict[str, int], cost: Dict[str, int], item_name: str) -> str:
    """Format a resource error message"""
    missing = []
    for resource, amount in cost.items():
        available = resources.get(resource, 0)
        if available < amount:
            missing.append(f"{resource}: {available}/{amount}")
    return f"Not enough resources to {item_name.lower()}. Missing: {', '.join(missing)}"


def generate_deterministic_traits(self_name: str, womb_id: int, clone_id: str, timestamp: float) -> Dict[str, int]:
    """
    Generate deterministic traits using HMAC-seeded RNG.
    
    Uses the same seeding approach as outcome engine for consistency.
    """
    import hmac
    import hashlib
    
    # Normalize self_name
    self_name_normalized = (self_name or "").strip().lower()
    
    # Create seed string
    seed_string = f"{self_name_normalized}|{womb_id}|{clone_id}|{timestamp}"
    
    # Use HMAC-SHA256 for deterministic seed
    hmac_key = b"trait_generation_seed"
    hashed_seed = hmac.new(hmac_key, seed_string.encode('utf-8'), hashlib.sha256).hexdigest()
    
    # Convert to int for random.Random seed
    seed_int = int(hashed_seed[:16], 16)
    
    # Generate traits
    rng = random.Random(seed_int)
    return random_traits(rng)
