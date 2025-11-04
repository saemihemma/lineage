"""Pure game rules functions - immutable state updates"""
import random
import uuid
from typing import Tuple, Dict, Optional, Any
from game.state import GameState
from core.models import Clone, CLONE_TYPES, TRAIT_LIST
from core.config import CONFIG
from core.game_logic import (
    inflate_costs, can_afford, format_resource_error,
    random_traits, soul_split_percent,
    award_practice_xp, perk_mining_xp_mult,
    perk_exploration_yield_mult, perk_constructive_cost_mult
)


def build_womb(state: GameState) -> Tuple[GameState, str]:
    """
    Build the Womb (assembler).
    Supports multiple wombs based on unlock conditions.
    Womb is actually created when task completes (see check_and_complete_tasks).
    This function only checks unlock conditions and deducts costs.
    
    Returns:
        Tuple of (new_state, message)
    """
    from game.wombs import get_unlocked_womb_count, create_womb
    from core.config import GAMEPLAY_CONFIG
    from core.game_logic import check_practice_unlock
    
    # Systems v1: Check multi_womb unlock if trying to build second+ womb
    current_count = len(state.wombs)
    if current_count >= 1:
        if not check_practice_unlock(state.practices_xp, "multi_womb", GAMEPLAY_CONFIG):
            practices_config = GAMEPLAY_CONFIG.get("practices", {})
            constructive_config = practices_config.get("Constructive", {})
            unlocks = constructive_config.get("unlocks", {})
            required_level = unlocks.get("multi_womb", 6)
            xp_per_level = CONFIG.get("PRACTICE_XP_PER_LEVEL", 100)
            current_level = state.practices_xp.get("Constructive", 0) // xp_per_level
            raise RuntimeError(
                f"Cannot build multiple wombs. "
                f"Requires Constructive practice level {required_level} (current: {current_level})."
            )
    
    # Check unlock conditions (existing system)
    unlocked_count = get_unlocked_womb_count(state)
    
    if current_count >= unlocked_count:
        raise RuntimeError(f"Cannot build more wombs. Unlocked: {unlocked_count}/{CONFIG.get('WOMB_MAX_COUNT', 4)}")
    
    level = state.soul_level()
    base_cost = inflate_costs(CONFIG["ASSEMBLER_COST"], level)
    cost_mult = perk_constructive_cost_mult(state)
    cost = {k: int(round(v * cost_mult)) for k, v in base_cost.items()}
    
    if not can_afford(state.resources, cost):
        raise RuntimeError(format_resource_error(state.resources, cost, "Womb"))
    
    # Create new state with immutable updates
    new_state = state.copy()
    
    # Deduct resources
    for k, v in cost.items():
        new_state.resources[k] = new_state.resources.get(k, 0) - v
    
    # Award practice XP (modifies practices_xp in place, but on copy)
    award_practice_xp(new_state, "Constructive", 10)
    
    # Gain attention when building womb (always, even for first womb)
    from game.wombs import gain_attention
    from core.config import GAMEPLAY_CONFIG
    attention_config = GAMEPLAY_CONFIG.get("attention", {})
    gain_config = attention_config.get("gain", {})
    attention_delta = gain_config.get("build_womb", 20.0)  # Default to 20 if not in config
    new_state = gain_attention(new_state, attention_delta=attention_delta)
    
    womb_num = current_count + 1
    return new_state, f"Building Womb {womb_num}..."


def grow_clone(state: GameState, kind: str) -> Tuple[GameState, Clone, float, str, Dict]:
    """
    Grow a new clone.
    Requires at least one functional womb with sufficient durability/attention.
    
    Phase 6: Uses outcome engine for deterministic resolution.
    Keeps backward-compatible signature.
    
    Returns:
        Tuple of (new_state, clone, soul_split_percent, message, clone_data)
    """
    from game.wombs import check_womb_available, find_active_womb
    import time
    import uuid
    from backend.engine.outcomes import (
        OutcomeContext, SeedParts, resolve_grow
    )
    from core.config import GAMEPLAY_CONFIG, GAMEPLAY_CONFIG_VERSION
    from core.game_logic import check_practice_unlock, get_clone_kind_tier
    
    # Systems v1: Check practice unlocks for clone kind
    tier_key = get_clone_kind_tier(kind)
    if tier_key and not check_practice_unlock(state.practices_xp, tier_key, GAMEPLAY_CONFIG):
        practices_config = GAMEPLAY_CONFIG.get("practices", {})
        constructive_config = practices_config.get("Constructive", {})
        unlocks = constructive_config.get("unlocks", {})
        required_level = unlocks.get(tier_key, 0)
        xp_per_level = CONFIG.get("PRACTICE_XP_PER_LEVEL", 100)
        current_level = state.practices_xp.get("Constructive", 0) // xp_per_level
        raise RuntimeError(
            f"Cannot grow {CLONE_TYPES[kind].display}. "
            f"Requires Constructive practice level {required_level} (current: {current_level})."
        )
    
    # Check if womb is available (using new womb system)
    if not check_womb_available(state):
        # Check if we have wombs but they're all broken
        if state.wombs and len(state.wombs) > 0:
            raise RuntimeError("No functional wombs available. Repair or build a new womb first.")
        else:
            raise RuntimeError("Build the Womb first.")
    
    # Check if active womb is functional (attention is now global, not per-womb)
    active_womb = find_active_womb(state)
    if not active_womb:
        # Should not reach here if check_womb_available passed, but safety check
        raise RuntimeError("No functional wombs available. Repair or build a new womb first.")
    
    # Womb must be functional (durability > 0)
    if not active_womb.is_functional():
        raise RuntimeError(f"Womb {active_womb.id} is not functional. Durability: {active_womb.durability:.1f}/{active_womb.max_durability:.1f}. Repair it first.")
    
    # Capture womb_id for deterministic trait generation and RNG seeding
    womb_id = active_womb.id
    
    # Systems v1: Capture task_started_at when task is queued (will be persisted with task)
    task_started_at = time.time()
    
    # Systems v1: Build outcome context for deterministic resolution
    grow_id = str(uuid.uuid4())
    seed_parts = SeedParts(
        self_name=state.self_name or "",
        womb_id=womb_id,
        task_started_at=task_started_at,
        config_version=GAMEPLAY_CONFIG_VERSION,
        action_id=grow_id
    )
    
    # Get best womb durability
    womb_durability = 100.0  # Default
    if active_womb:
        womb_durability = active_womb.durability
    
    # Count active wombs for overload calculation
    active_wombs_count = len([w for w in state.wombs if w.is_functional()])
    
    ctx = OutcomeContext(
        action='grow',
        clone=None,  # No clone yet - we're creating one
        self_level=state.soul_level(),
        practices=state.practices_xp,
        global_attention=getattr(state, 'global_attention', 0.0),
        womb_durability=womb_durability,
        clone_kind=kind,
        soul_percent=state.soul_percent,
        config=CONFIG,
        gameplay_config=GAMEPLAY_CONFIG,
        seed_parts=seed_parts,
        active_wombs_count=active_wombs_count
    )
    
    # Resolve outcome using deterministic engine
    outcome = resolve_grow(ctx)
    
    # Check if outcome failed (insufficient soul)
    if outcome.result == 'failure':
        raise RuntimeError("Insufficient soul integrity for clone crafting.")
    
    # Check if can afford cost
    if not can_afford(state.resources, outcome.cost):
        raise RuntimeError(format_resource_error(state.resources, outcome.cost, CLONE_TYPES[kind].display))
    
    # Create new state
    new_state = state.copy()
    new_state.soul_percent -= 100.0 * outcome.soul_split_percent
    
    # Deduct resources
    for k, v in outcome.cost.items():
        new_state.resources[k] = new_state.resources.get(k, 0) - v
    
    # Prepare clone data (but don't add to state yet - will be added when task completes)
    # Capture deterministic timestamp for trait generation
    deterministic_timestamp = time.time()
    # Generate clone ID first (needed for trait generation)
    clone_id = str(uuid.uuid4())[:8]
    
    # Generate deterministic traits using HMAC-seeded RNG
    from core.game_logic import generate_deterministic_traits
    traits = generate_deterministic_traits(
        self_name=state.self_name or "",
        womb_id=womb_id,
        clone_id=clone_id,
        timestamp=deterministic_timestamp
    )
    
    clone_data = {
        "id": clone_id,
        "kind": kind,
        "traits": traits,
        "xp": {"MINING": 0, "COMBAT": 0, "EXPLORATION": 0},
        "survived_runs": 0,
        "alive": True,
        "uploaded": False,
        "created_at": 0.0,  # Will be set when task completes
        # Store trait generation metadata for persistence/debugging
        "trait_generation_metadata": {
            "womb_id": womb_id,
            "timestamp": deterministic_timestamp,
            "self_name": state.self_name or ""
        },
        # Phase 6: Store outcome info for completion handler
        "outcome": {
            "feral_attack": outcome.feral_attack,
            "attention_delta": outcome.stats.attention_delta,
            "time_seconds": outcome.time_seconds
        }
    }
    
    # Award practice XP (from config)
    from core.config import GAMEPLAY_CONFIG
    grow_config = GAMEPLAY_CONFIG.get("grow", {})
    practice_xp = grow_config.get("practice_xp", {}).get("constructive", 6)
    award_practice_xp(new_state, "Constructive", practice_xp)
    
    # Gain attention on active womb (if any) - use outcome's attention_delta
    if new_state.wombs:
        from game.wombs import gain_attention
        attention_delta = outcome.stats.attention_delta
        new_state = gain_attention(new_state, attention_delta=attention_delta)
        
        # Apply heat cross-link: when any womb grows, all active wombs gain +2 attention
        from core.config import GAMEPLAY_CONFIG
        womb_config = GAMEPLAY_CONFIG.get("wombs", {})
        heat_crosslink = womb_config.get("heat_crosslink_add", 2)
        active_wombs_count = len([w for w in new_state.wombs if w.is_functional()])
        if active_wombs_count > 1:
            crosslink_attention = heat_crosslink * (active_wombs_count - 1)
            new_state = gain_attention(new_state, attention_delta=crosslink_attention)
    
    # Format message with flavor text using state's RNG
    from backend.routers.game import format_clone_crafted_message
    msg = format_clone_crafted_message(
        clone_kind=kind,
        clone_id=clone_data["id"],
        traits=clone_data["traits"],
        rng=new_state.rng
    )
    # Create a Clone object for return (but don't add to state yet)
    clone = Clone(
        id=clone_data["id"],
        kind=clone_data["kind"],
        traits=clone_data["traits"],
        xp=clone_data["xp"],
        created_at=0.0
    )
    return new_state, clone, outcome.soul_split_percent, msg, clone_data


def apply_clone(state: GameState, cid: str) -> Tuple[GameState, str]:
    """
    Apply a clone to the spaceship.
    
    Returns:
        Tuple of (new_state, message)
    """
    c = state.clones.get(cid)
    if not c:
        raise RuntimeError("Clone unavailable.")
    if not c.alive:
        raise RuntimeError("Clone unavailable.")
    if c.uploaded:
        raise RuntimeError("Cannot apply an uploaded clone.")
    
    new_state = state.copy()
    new_state.applied_clone_id = cid
    
    return new_state, f"Applied clone {cid} to spaceship."


def run_expedition(state: GameState, kind: str) -> Tuple[GameState, str, Optional[Dict[str, Any]]]:
    """
    Run an expedition with the applied clone.
    
    Phase 2: Uses new outcome engine for deterministic resolution.
    Phase 4: Returns feral attack info if occurred.
    Keeps backward-compatible signature (returns 3-tuple now).
    
    Returns:
        Tuple of (new_state, message, feral_attack_info)
        feral_attack_info is None if no attack occurred
    """
    import time
    import uuid
    from backend.engine.outcomes import (
        OutcomeContext, SeedParts, resolve_expedition as resolve_expedition_outcome
    )
    
    cid = state.applied_clone_id
    if not cid or cid not in state.clones or not state.clones[cid].alive:
        return state, "No clone applied to the spaceship. Apply one first."
    
    c = state.clones[cid]
    new_state = state.copy()
    new_clone = new_state.clones[cid]
    
    # Systems v1: Build outcome context for deterministic resolution
    from core.config import GAMEPLAY_CONFIG, GAMEPLAY_CONFIG_VERSION
    from game.wombs import find_active_womb
    
    # Capture womb_id and task_started_at for deterministic seeding
    active_womb = find_active_womb(new_state)
    womb_id = active_womb.id if active_womb else 0
    task_started_at = time.time()
    
    expedition_id = str(uuid.uuid4())
    seed_parts = SeedParts(
        self_name=state.self_name or "",
        womb_id=womb_id,
        task_started_at=task_started_at,
        config_version=GAMEPLAY_CONFIG_VERSION,
        action_id=expedition_id
    )
    
    # Get best womb durability
    womb_durability = 100.0  # Default
    if new_state.wombs:
        functional_wombs = [w for w in new_state.wombs if w.is_functional()]
        if functional_wombs:
            womb_durability = functional_wombs[0].durability
    
    # Count active wombs for overload calculation
    active_wombs_count = len(functional_wombs) if new_state.wombs else 0
    
    # Check for prayer bonus (clear after use)
    prayer_bonus = getattr(state, 'last_pray_effect', None)
    if prayer_bonus and prayer_bonus.get("type") == "expedition":
        # Clear prayer bonus after use
        new_state.last_pray_effect = None
    
    ctx = OutcomeContext(
        action='expedition',
        clone=c,
        self_level=state.soul_level(),
        practices=state.practices_xp,
        global_attention=getattr(state, 'global_attention', 0.0),
        womb_durability=womb_durability,
        expedition_kind=kind,
        config=CONFIG,  # For backward compat (practice levels, etc.)
        gameplay_config=GAMEPLAY_CONFIG,
        seed_parts=seed_parts,
        active_wombs_count=active_wombs_count,
        prayer_bonus=prayer_bonus  # Pass prayer bonus to outcome engine
    )
    
    # Resolve outcome using deterministic engine
    outcome = resolve_expedition_outcome(ctx)
    
    # Phase 4: Handle feral attack info from outcome
    # (event emission will be done in endpoint)
    
    # Apply outcome to state
    if outcome.result == 'death':
        # Clone died - reduce XP and mark as dead
        # Note: XP loss fraction uses non-deterministic random (acceptable per plan)
        # In future phases, we can make this deterministic if needed
        import random
        frac = random.uniform(0.25, 0.75)
        for k in new_clone.xp:
            new_clone.xp[k] = int(new_clone.xp[k] * (1.0 - frac))
        new_clone.alive = False
        if new_state.applied_clone_id == cid:
            new_state.applied_clone_id = ""
        # Do NOT increment survived_runs - clone died
        # Phase 4: Return feral attack info even on death (attack happened before death roll)
        # Format death message with flavor text
        from backend.routers.game import format_expedition_failure_message
        death_message = f"Your clone was lost on the {kind.lower()} expedition. A portion of its learned skill erodes."
        msg = format_expedition_failure_message(kind, death_message, new_state.rng)
        return new_state, msg, outcome.feral_attack
    
    # Clone survived - apply rewards and XP
    for res, amount in outcome.loot.items():
        new_state.resources[res] = new_state.resources.get(res, 0) + amount
    
    for xp_kind, xp_amount in outcome.xp_gained.items():
        new_clone.xp[xp_kind] = new_clone.xp.get(xp_kind, 0) + xp_amount
    
    # Increment survived_runs
    new_clone.survived_runs += 1
    
    # Award practice XP
    if kind in ["MINING", "COMBAT"]:
        award_practice_xp(new_state, "Kinetic", 5)
    elif kind == "EXPLORATION":
        award_practice_xp(new_state, "Cognitive", 5)
    
    # Gain attention on active womb after successful expedition - use outcome's attention_delta
    if new_state.wombs:
        from game.wombs import gain_attention
        attention_delta = outcome.stats.attention_delta
        new_state = gain_attention(new_state, attention_delta=attention_delta)
    
    # Format success message with flavor text
    from backend.routers.game import format_expedition_message
    gained = outcome.xp_gained.get(kind, 0)
    msg = format_expedition_message(
        expedition_kind=kind,
        success=True,
        loot=outcome.loot,
        xp_gained=gained,
        survived_runs=new_clone.survived_runs,
        shilajit_found=outcome.shilajit_found,
        rng=new_state.rng
    )
    
    # Phase 4: Return feral attack info if occurred
    return new_state, msg, outcome.feral_attack


def upload_clone(state: GameState, cid: str) -> Tuple[GameState, str, Optional[str], Optional[Dict[str, Any]]]:
    """
    Upload a clone to SELF to gain XP.
    
    Phase 6: Uses outcome engine for deterministic resolution.
    Keeps backward-compatible signature (returns 3-tuple now).
    
    Returns:
        Tuple of (new_state, message, feral_attack_info)
        feral_attack_info is None if no attack occurred
    """
    import time
    import uuid
    from backend.engine.outcomes import (
        OutcomeContext, SeedParts, resolve_upload
    )
    from core.config import GAMEPLAY_CONFIG, GAMEPLAY_CONFIG_VERSION
    from game.wombs import find_active_womb
    
    c = state.clones.get(cid)
    if not c:
        return state, "Clone not found.", None
    if not c.alive:
        return state, "Cannot upload a destroyed clone.", None
    if c.uploaded:
        return state, "Clone has already been uploaded.", None
    
    # Systems v1: Build outcome context for deterministic resolution
    # Capture womb_id and task_started_at for deterministic seeding
    active_womb = find_active_womb(state)
    womb_id = active_womb.id if active_womb else 0
    task_started_at = time.time()
    
    upload_id = str(uuid.uuid4())
    seed_parts = SeedParts(
        self_name=state.self_name or "",
        womb_id=womb_id,
        task_started_at=task_started_at,
        config_version=GAMEPLAY_CONFIG_VERSION,
        action_id=upload_id
    )
    
    # Get best womb durability (for context, but upload doesn't use it)
    womb_durability = 100.0  # Default
    if state.wombs:
        functional_wombs = [w for w in state.wombs if w.is_functional()]
        if functional_wombs:
            womb_durability = functional_wombs[0].durability
    
    # Count active wombs for overload calculation
    active_wombs_count = len(functional_wombs) if state.wombs else 0
    
    ctx = OutcomeContext(
        action='upload',
        clone=c,
        self_level=state.soul_level(),
        practices=state.practices_xp,
        global_attention=getattr(state, 'global_attention', 0.0),
        womb_durability=womb_durability,
        soul_percent=state.soul_percent,
        config=CONFIG,
        gameplay_config=GAMEPLAY_CONFIG,
        seed_parts=seed_parts,
        active_wombs_count=active_wombs_count
    )
    
    # Resolve outcome using deterministic engine
    outcome = resolve_upload(ctx)
    
    # Apply outcome to state
    old_level = state.soul_level()  # Capture old level before state changes
    new_state = state.copy()
    new_state.soul_xp += outcome.soul_xp_gained
    new_state.soul_percent = new_state.soul_percent + outcome.soul_restore_percent
    
    # Mark clone as uploaded
    new_clone = new_state.clones[cid]
    new_clone.uploaded = True
    new_clone.alive = False
    if new_state.applied_clone_id == cid:
        new_state.applied_clone_id = ""
    
    new_level = 1 + (new_state.soul_xp // CONFIG['SOUL_LEVEL_STEP'])
    
    # Format upload message with flavor text (without level info)
    from backend.routers.game import format_upload_message, format_level_up_message
    retained_pct = int(outcome.terms['soul_xp']['retain'] * 100)
    upload_msg = format_upload_message(
        retained_pct=retained_pct,
        soul_xp_gained=outcome.soul_xp_gained,
        soul_restore=outcome.soul_restore_percent,
        new_level=new_level,
        rng=new_state.rng
    )
    
    # Check if level increased and format level up message
    level_up_msg = None
    if new_level > old_level:
        level_up_msg = format_level_up_message(new_level, new_state.rng)
    
    # Phase 6: Return feral attack info if occurred
    return new_state, upload_msg, level_up_msg, outcome.feral_attack


def gather_resource(state: GameState, resource: str) -> Tuple[GameState, int, str]:
    """
    Gather a resource (without timer - timer handled by scheduler).
    
    Returns:
        Tuple of (new_state, amount_gathered, message)
    """
    if resource not in CONFIG["GATHER_TIME"]:
        raise ValueError(f"Unknown resource: {resource}")
    
    t_min, t_max = CONFIG["GATHER_TIME"][resource]
    amount_min, amount_max = CONFIG["GATHER_AMOUNT"][resource]
    
    new_state = state.copy()
    amount = state.rng.randint(amount_min, amount_max)
    
    # Format message with flavor text
    from backend.routers.game import format_resource_gathering_message
    if resource == "Shilajit":
        new_state.resources[resource] = new_state.resources.get(resource, 0) + 1
        amount = 1
    else:
        new_state.resources[resource] = new_state.resources.get(resource, 0) + amount
    
    msg = format_resource_gathering_message(
        resource=resource,
        amount=amount,
        total=new_state.resources[resource],
        rng=new_state.rng
    )
    
    # Award practice XP
    award_practice_xp(new_state, "Kinetic", 2)
    
    return new_state, amount, msg

