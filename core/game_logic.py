"""Core game logic functions"""
import random
import uuid
from typing import Dict
from .models import PlayerState, Clone, CLONE_TYPES, TRAIT_LIST
from .config import CONFIG

def inflate_costs(base: Dict[str, int], level: int) -> Dict[str, int]:
    """Calculate cost inflation based on level"""
    if level <= 1:
        return dict(base)
    mult = (1.0 + CONFIG["COST_INFLATE_PER_LEVEL"]) ** (level - 1)
    return {k: max(1, int(round(v * mult))) for k, v in base.items()}


def can_afford(resources: Dict[str, int], cost: Dict[str, int]) -> bool:
    """Check if player can afford a cost"""
    return all(resources.get(k, 0) >= v for k, v in cost.items())


def format_resource_error(resources: Dict[str, int], cost: Dict[str, int], item_name: str) -> str:
    """Format an error message showing what you have vs what you need"""
    missing = []
    for res, needed in cost.items():
        have = resources.get(res, 0)
        if have < needed:
            missing.append(f"{res}: {have}/{needed}")
    
    if missing:
        return f"Insufficient resources for {item_name}.\nMissing: {', '.join(missing)}"
    return f"Insufficient resources for {item_name}."


def spend(resources: Dict[str, int], cost: Dict[str, int]):
    """Deduct resources for a cost"""
    for k, v in cost.items():
        resources[k] = resources.get(k, 0) - v


def random_traits(level: int, rng: random.Random) -> Dict[str, int]:
    """Generate random traits for a clone based on level"""
    base_bonus = (level - 1) * CONFIG["TRAIT_BASELINE_PER_LEVEL"]
    out = {}
    for t in TRAIT_LIST:
        val = rng.randint(1, 10) + base_bonus
        out[t.code] = max(1, min(10, val))
    return out


def soul_split_percent(rng: random.Random) -> float:
    """Calculate soul split percentage for clone crafting"""
    base = CONFIG["SOUL_SPLIT_BASE"]
    var = CONFIG["SOUL_SPLIT_VARIANCE"]
    return max(0.01, base + rng.uniform(-var, var))


# Practice XP and perk functions (defined before craft functions that use them)
def award_practice_xp(p: PlayerState, primary: str, amount: int):
    """Award practice XP to primary track, with cross-pollination to other tracks"""
    spill = int(round(amount * CONFIG["CROSS_POLL_FRACTION"]))
    p.practices_xp[primary] += amount
    for t in CONFIG["PRACTICE_TRACKS"]:
        if t != primary:
            p.practices_xp[t] += spill


def perk_mining_xp_mult(p: PlayerState) -> float:
    """+10% XP if Kinetic Level 2+"""
    return 1.10 if p.practice_level("Kinetic") >= 2 else 1.0


def perk_exploration_yield_mult(p: PlayerState) -> float:
    """+10% yield if Cognitive Level 2+"""
    return 1.10 if p.practice_level("Cognitive") >= 2 else 1.0


def perk_constructive_craft_time_mult(p: PlayerState) -> float:
    """10% faster crafting if Constructive Level 2+"""
    return 0.90 if p.practice_level("Constructive") >= 2 else 1.0


def perk_constructive_cost_mult(p: PlayerState) -> float:
    """5% cheaper costs if Constructive Level 3+"""
    return 0.95 if p.practice_level("Constructive") >= 3 else 1.0


def craft_assembler(p: PlayerState, rng: random.Random):
    """Build the Womb (assembler)"""
    level = p.soul_level()
    base_cost = inflate_costs(CONFIG["ASSEMBLER_COST"], level)
    # Apply cost reduction perk
    cost_mult = perk_constructive_cost_mult(p)
    cost = {k: int(round(v * cost_mult)) for k, v in base_cost.items()}
    if not can_afford(p.resources, cost):
        raise RuntimeError(format_resource_error(p.resources, cost, "Womb"))
    spend(p.resources, cost)
    p.assembler_built = True
    award_practice_xp(p, "Constructive", 10)


def craft_clone(p: PlayerState, kind: str, rng: random.Random):
    """Craft a new clone"""
    if not p.assembler_built:
        raise RuntimeError("Build the Womb first.")
    level = p.soul_level()
    base_cost = inflate_costs(CONFIG["CLONE_COSTS"][kind], level)
    # Apply cost reduction perk
    cost_mult = perk_constructive_cost_mult(p)
    cost = {k: int(round(v * cost_mult)) for k, v in base_cost.items()}
    if not can_afford(p.resources, cost):
        raise RuntimeError(format_resource_error(p.resources, cost, CLONE_TYPES[kind].display))
    split = soul_split_percent(rng)
    if p.soul_percent - 100.0 * split < 0:
        raise RuntimeError("Insufficient soul integrity for clone crafting.")
    p.soul_percent -= 100.0 * split
    spend(p.resources, cost)
    traits = random_traits(level, rng)
    clone = Clone(
        id=str(uuid.uuid4())[:8],
        kind=kind,
        traits=traits,
        xp={"MINING": 0, "COMBAT": 0, "EXPLORATION": 0}
    )
    p.clones[clone.id] = clone
    award_practice_xp(p, "Constructive", 6)
    return clone, split


def apply_clone(p: PlayerState, cid: str):
    """Apply a clone to the spaceship"""
    c = p.clones.get(cid)
    if not c:
        raise RuntimeError("Clone unavailable.")
    if not c.alive:
        raise RuntimeError("Clone unavailable.")
    if c.uploaded:
        raise RuntimeError("Cannot apply an uploaded clone.")
    p.applied_clone_id = cid


def expedition(p: PlayerState, kind: str, rng: random.Random) -> str:
    """Run an expedition with the applied clone"""
    cid = p.applied_clone_id
    if not cid or cid not in p.clones or not p.clones[cid].alive:
        return "No clone applied to the spaceship. Apply one first."
    c = p.clones[cid]
    loot = {}
    # Apply exploration yield perk if applicable
    yield_mult = perk_exploration_yield_mult(p) if kind == "EXPLORATION" else 1.0
    for res, (a, b) in CONFIG["REWARDS"][kind].items():
        base_amt = rng.randint(a, b)
        loot[res] = int(round(base_amt * yield_mult))
        p.resources[res] = p.resources.get(res, 0) + loot[res]
    base_xp = {"MINING": 10, "COMBAT": 12, "EXPLORATION": 8}[kind]
    mult = 1.0
    if kind == "MINING" and c.kind == "MINER":
        mult *= CONFIG["MINER_XP_MULT"]
    # Apply mining/combat XP perk if applicable
    if kind in ["MINING", "COMBAT"]:
        mult *= perk_mining_xp_mult(p)
    gained = int(round(base_xp * mult))
    c.xp[kind] += gained
    # Award practice XP
    if kind in ["MINING", "COMBAT"]:
        award_practice_xp(p, "Kinetic", 5)
    elif kind == "EXPLORATION":
        award_practice_xp(p, "Cognitive", 5)
    c.survived_runs += 1
    shilajit_found = False
    if kind == "EXPLORATION":
        # 15% chance to find Shilajit on exploration expeditions
        if rng.random() < 0.15:
            p.resources["Shilajit"] = p.resources.get("Shilajit", 0) + 1
            shilajit_found = True
    if rng.random() < CONFIG["DEATH_PROB"]:
        frac = rng.uniform(0.25, 0.75)
        for k in c.xp:
            c.xp[k] = int(c.xp[k] * (1.0 - frac))
        c.alive = False
        if p.applied_clone_id == c.id:
            p.applied_clone_id = ""
        return f"Your clone was lost on the {kind.lower()} expedition. A portion of its learned skill erodes."
    loot_str = ", ".join([f"{k}+{v}" for k, v in loot.items()])
    expedition_msg = f"{kind.title()} expedition complete: {loot_str}. {kind.title()} XP +{gained}. Survived runs: {c.survived_runs}."
    if shilajit_found:
        expedition_msg += " Recovered Shilajit fragment from exploration site."
    return expedition_msg


def upload_clone_to_soul(p: PlayerState, cid: str, rng: random.Random) -> str:
    """Upload a clone to SELF to gain XP"""
    c = p.clones.get(cid)
    if not c:
        return "Clone not found."
    if not c.alive:
        return "Cannot upload a destroyed clone."
    if c.uploaded:
        return "Clone has already been uploaded."
    total = sum(c.xp.values())
    lo, hi = CONFIG["SOUL_XP_RETAIN_RANGE"]
    retain = rng.uniform(lo, hi)
    gained = int(total * retain)
    p.soul_xp += gained
    
    # Restore soul_percent based on clone quality
    # Higher XP clones restore more percentage (e.g., every 10 XP = ~0.5% restoration, max 5%)
    percent_restore = min(5.0, total * 0.05)
    p.soul_percent = min(100.0, p.soul_percent + percent_restore)
    
    # Mark clone as uploaded instead of deleting it
    c.uploaded = True
    c.alive = False  # Also mark as not alive so it can't be used
    if p.applied_clone_id == cid:
        p.applied_clone_id = ""
    new_level = 1 + (p.soul_xp // CONFIG['SOUL_LEVEL_STEP'])
    return f"Uploaded clone to SELF. Retained ~{int(retain*100)}% (+{gained} SELF XP). SELF restored by {percent_restore:.1f}%. SELF Level now {new_level}."

