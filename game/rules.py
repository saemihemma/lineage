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
    
    # Check unlock conditions
    unlocked_count = get_unlocked_womb_count(state)
    current_count = len(state.wombs)
    
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
    
    # Gain attention on existing wombs (if any)
    if new_state.wombs:
        from game.wombs import gain_attention
        new_state = gain_attention(new_state)
    
    womb_num = current_count + 1
    return new_state, f"Building Womb {womb_num}..."


def grow_clone(state: GameState, kind: str) -> Tuple[GameState, Clone, float, str, Dict]:
    """
    Grow a new clone.
    Requires at least one functional womb with sufficient durability/attention.
    
    Returns:
        Tuple of (new_state, clone, soul_split_percent, message)
    """
    from game.wombs import check_womb_available, find_active_womb
    
    # Check if womb is available (using new womb system or fallback to assembler_built)
    if not check_womb_available(state) and not state.assembler_built:
        raise RuntimeError("Build the Womb first.")
    
    # Check if active womb is functional (attention is now global, not per-womb)
    active_womb = find_active_womb(state)
    if active_womb:
        # Womb must be functional (durability > 0)
        if not active_womb.is_functional():
            raise RuntimeError(f"Womb {active_womb.id} is not functional. Durability: {active_womb.durability:.1f}/{active_womb.max_durability:.1f}")
    
    # Capture womb_id for deterministic trait generation
    womb_id = active_womb.id if active_womb else 0
    
    level = state.soul_level()
    base_cost = inflate_costs(CONFIG["CLONE_COSTS"][kind], level)
    cost_mult = perk_constructive_cost_mult(state)
    cost = {k: int(round(v * cost_mult)) for k, v in base_cost.items()}
    
    if not can_afford(state.resources, cost):
        raise RuntimeError(format_resource_error(state.resources, cost, CLONE_TYPES[kind].display))
    
    split = soul_split_percent(state.rng)
    if state.soul_percent - 100.0 * split < 0:
        raise RuntimeError("Insufficient soul integrity for clone crafting.")
    
    # Create new state
    new_state = state.copy()
    new_state.soul_percent -= 100.0 * split
    
    # Deduct resources
    for k, v in cost.items():
        new_state.resources[k] = new_state.resources.get(k, 0) - v
    
    # Prepare clone data (but don't add to state yet - will be added when task completes)
    import time
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
        }
    }
    
    # Award practice XP
    award_practice_xp(new_state, "Constructive", 6)
    
    # Gain attention on active womb (if any)
    if new_state.wombs:
        from game.wombs import gain_attention
        new_state = gain_attention(new_state)
    
    msg = f"{CLONE_TYPES[kind].display} growing... SELF now {new_state.soul_percent:.1f}% (consumed ~{int(split * 100)}%)."
    # Create a Clone object for return (but don't add to state yet)
    clone = Clone(
        id=clone_data["id"],
        kind=clone_data["kind"],
        traits=clone_data["traits"],
        xp=clone_data["xp"],
        created_at=0.0
    )
    return new_state, clone, split, msg, clone_data


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
    
    # Phase 2/3: Build outcome context for deterministic resolution
    # Phase 3: Use config_version from outcomes_config.json
    from core.config import OUTCOMES_CONFIG, OUTCOMES_CONFIG_VERSION
    expedition_id = str(uuid.uuid4())
    seed_parts = SeedParts(
        user_id=getattr(state, '_session_id', state.applied_clone_id or "unknown"),
        session_id=getattr(state, '_session_id', state.applied_clone_id or "unknown"),
        action_id=expedition_id,
        config_version=OUTCOMES_CONFIG_VERSION,  # Phase 3: From outcomes_config.json
        timestamp=time.time()
    )
    
    # Get best womb durability
    womb_durability = 100.0  # Default
    if new_state.wombs:
        functional_wombs = [w for w in new_state.wombs if w.is_functional()]
        if functional_wombs:
            womb_durability = functional_wombs[0].durability
    
    ctx = OutcomeContext(
        action='expedition',
        clone=c,
        self_level=state.soul_level(),
        practices=state.practices_xp,
        global_attention=getattr(state, 'global_attention', 0.0),
        womb_durability=womb_durability,
        expedition_kind=kind,
        config=CONFIG,  # For backward compat (practice levels, etc.)
        outcomes_config=OUTCOMES_CONFIG,  # Phase 3: From outcomes_config.json
        seed_parts=seed_parts
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
        return new_state, f"Your clone was lost on the {kind.lower()} expedition. A portion of its learned skill erodes.", outcome.feral_attack
    
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
    
    # Gain attention on active womb after successful expedition
    if new_state.wombs:
        from game.wombs import gain_attention
        new_state = gain_attention(new_state)
    
    # Build message
    loot_str = ", ".join([f"{k}+{v}" for k, v in outcome.loot.items()])
    gained = outcome.xp_gained.get(kind, 0)
    msg = f"{kind.title()} expedition complete: {loot_str}. {kind.title()} XP +{gained}. Survived runs: {new_clone.survived_runs}."
    if outcome.shilajit_found:
        msg += " Recovered Shilajit fragment from exploration site."
    
    # Phase 4: Return feral attack info if occurred
    return new_state, msg, outcome.feral_attack


def upload_clone(state: GameState, cid: str) -> Tuple[GameState, str]:
    """
    Upload a clone to SELF to gain XP.
    
    Returns:
        Tuple of (new_state, message)
    """
    c = state.clones.get(cid)
    if not c:
        return state, "Clone not found."
    if not c.alive:
        return state, "Cannot upload a destroyed clone."
    if c.uploaded:
        return state, "Clone has already been uploaded."
    
    total = sum(c.xp.values())
    lo, hi = CONFIG["SOUL_XP_RETAIN_RANGE"]
    retain = state.rng.uniform(lo, hi)
    gained = int(total * retain)
    
    new_state = state.copy()
    new_state.soul_xp += gained
    
    # Restore soul_percent based on clone quality
    # Higher XP clones restore more (every 100 XP = 0.5% restoration, uncapped)
    # So 1000 XP = 5%, 2000 XP = 10%, etc. - can exceed 100%
    percent_restore = total * 0.005
    new_state.soul_percent = new_state.soul_percent + percent_restore
    
    # Mark clone as uploaded
    new_clone = new_state.clones[cid]
    new_clone.uploaded = True
    new_clone.alive = False
    if new_state.applied_clone_id == cid:
        new_state.applied_clone_id = ""
    
    new_level = 1 + (new_state.soul_xp // CONFIG['SOUL_LEVEL_STEP'])
    msg = f"Uploaded clone to SELF. Retained ~{int(retain*100)}% (+{gained} SELF XP). SELF restored by {percent_restore:.1f}%. SELF Level now {new_level}."
    return new_state, msg


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
    
    if resource == "Shilajit":
        new_state.resources[resource] = new_state.resources.get(resource, 0) + 1
        msg = "Shilajit sample extracted. Resource +1."
        amount = 1
    else:
        new_state.resources[resource] = new_state.resources.get(resource, 0) + amount
        msg = f"Gathered {amount} {resource}. Total: {new_state.resources[resource]}"
    
    # Award practice XP
    award_practice_xp(new_state, "Kinetic", 2)
    
    return new_state, amount, msg

