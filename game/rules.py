"""Pure game rules functions - immutable state updates"""
import random
import uuid
from typing import Tuple, Dict
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
    
    Returns:
        Tuple of (new_state, message)
    """
    level = state.soul_level()
    base_cost = inflate_costs(CONFIG["ASSEMBLER_COST"], level)
    cost_mult = perk_constructive_cost_mult(state)
    cost = {k: int(round(v * cost_mult)) for k, v in base_cost.items()}
    
    if not can_afford(state.resources, cost):
        raise RuntimeError(format_resource_error(state.resources, cost, "Womb"))
    
    # Create new state with immutable updates
    new_state = state.copy()
    new_state.assembler_built = True
    
    # Deduct resources
    for k, v in cost.items():
        new_state.resources[k] = new_state.resources.get(k, 0) - v
    
    # Award practice XP (modifies practices_xp in place, but on copy)
    award_practice_xp(new_state, "Constructive", 10)
    
    return new_state, "Womb built successfully."


def grow_clone(state: GameState, kind: str) -> Tuple[GameState, Clone, float, str, Dict]:
    """
    Grow a new clone.
    
    Returns:
        Tuple of (new_state, clone, soul_split_percent, message)
    """
    if not state.assembler_built:
        raise RuntimeError("Build the Womb first.")
    
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
    traits = random_traits(level, state.rng)
    clone_data = {
        "id": str(uuid.uuid4())[:8],
        "kind": kind,
        "traits": traits,
        "xp": {"MINING": 0, "COMBAT": 0, "EXPLORATION": 0},
        "survived_runs": 0,
        "alive": True,
        "uploaded": False,
        "created_at": 0.0  # Will be set when task completes
    }
    
    # Award practice XP
    award_practice_xp(new_state, "Constructive", 6)
    
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


def run_expedition(state: GameState, kind: str) -> Tuple[GameState, str]:
    """
    Run an expedition with the applied clone.
    
    Returns:
        Tuple of (new_state, message)
    """
    cid = state.applied_clone_id
    if not cid or cid not in state.clones or not state.clones[cid].alive:
        return state, "No clone applied to the spaceship. Apply one first."
    
    c = state.clones[cid]
    new_state = state.copy()
    new_clone = new_state.clones[cid]
    
    loot = {}
    yield_mult = perk_exploration_yield_mult(state) if kind == "EXPLORATION" else 1.0
    for res, (a, b) in CONFIG["REWARDS"][kind].items():
        base_amt = state.rng.randint(a, b)
        loot[res] = int(round(base_amt * yield_mult))
        new_state.resources[res] = new_state.resources.get(res, 0) + loot[res]
    
    base_xp = {"MINING": 10, "COMBAT": 12, "EXPLORATION": 8}[kind]
    mult = 1.0
    if kind == "MINING" and c.kind == "MINER":
        mult *= CONFIG["MINER_XP_MULT"]
    if kind in ["MINING", "COMBAT"]:
        mult *= perk_mining_xp_mult(state)
    
    gained = int(round(base_xp * mult))
    new_clone.xp[kind] += gained
    
    # Award practice XP
    if kind in ["MINING", "COMBAT"]:
        award_practice_xp(new_state, "Kinetic", 5)
    elif kind == "EXPLORATION":
        award_practice_xp(new_state, "Cognitive", 5)
    
    new_clone.survived_runs += 1
    
    shilajit_found = False
    if kind == "EXPLORATION":
        if state.rng.random() < 0.15:
            new_state.resources["Shilajit"] = new_state.resources.get("Shilajit", 0) + 1
            shilajit_found = True
    
    if state.rng.random() < CONFIG["DEATH_PROB"]:
        frac = state.rng.uniform(0.25, 0.75)
        for k in new_clone.xp:
            new_clone.xp[k] = int(new_clone.xp[k] * (1.0 - frac))
        new_clone.alive = False
        if new_state.applied_clone_id == cid:
            new_state.applied_clone_id = ""
        return new_state, f"Your clone was lost on the {kind.lower()} expedition. A portion of its learned skill erodes."
    
    loot_str = ", ".join([f"{k}+{v}" for k, v in loot.items()])
    msg = f"{kind.title()} expedition complete: {loot_str}. {kind.title()} XP +{gained}. Survived runs: {new_clone.survived_runs}."
    if shilajit_found:
        msg += " Recovered Shilajit fragment from exploration site."
    return new_state, msg


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
    percent_restore = min(5.0, total * 0.05)
    new_state.soul_percent = min(100.0, new_state.soul_percent + percent_restore)
    
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

