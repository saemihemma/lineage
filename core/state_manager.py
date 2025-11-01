"""Save and load game state"""
import os
import json
import time
from .models import PlayerState, Clone
from .config import CONFIG
from game.migrations.migrate import migrate, get_latest_version

SAVE_FILE = "frontier_save.json"


def save_state(p):
    """Save state (accepts PlayerState or GameState)"""
    # Ensure version is set to current and seed is initialized
    latest_version = get_latest_version()
    # Generate seed if not set
    if p.rng_seed is None:
        import random
        p.rng_seed = random.randint(0, 2**31 - 1)
    
    data = {
        "version": latest_version,  # Always save with current version
        "rng_seed": p.rng_seed,
        "soul_percent": p.soul_percent,
        "soul_xp": p.soul_xp,
        "assembler_built": p.assembler_built,
        "resources": p.resources,
        "applied_clone_id": p.applied_clone_id,
        "practices_xp": p.practices_xp,
        "last_saved_ts": time.time(),
        "self_name": p.self_name,
        "active_tasks": getattr(p, "active_tasks", {}),
        "ui_layout": getattr(p, "ui_layout", {}),
        "clones": {
            cid: {
                "id": c.id,
                "kind": c.kind,
                "traits": c.traits,
                "xp": c.xp,
                "survived_runs": c.survived_runs,
                "alive": c.alive,
                "uploaded": c.uploaded
            }
            for cid, c in p.clones.items()
        }
    }
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_state() -> PlayerState:
    """Load player state from file, creating new if missing"""
    if not os.path.exists(SAVE_FILE):
        p = PlayerState()
        p.assembler_built = False  # Explicitly ensure assembler starts not built
        p.last_saved_ts = time.time()
        p.version = get_latest_version()  # Set to current version
        return p
    
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        d = json.load(f)
    
    # Check version and migrate if needed
    saved_version = d.get("version", 0)  # 0 means pre-versioned save
    latest_version = get_latest_version()
    
    if saved_version < latest_version:
        # Run migrations
        d = migrate(d, saved_version, latest_version)
    
    # Now load the (possibly migrated) state
    p = PlayerState()
    p.version = d.get("version", latest_version)
    p.rng_seed = d.get("rng_seed", None)  # Will be generated on first get_rng() call if None
    p.soul_percent = d.get("soul_percent", CONFIG["SOUL_START"])
    p.soul_xp = d.get("soul_xp", 0)
    p.assembler_built = d.get("assembler_built", False)  # Explicitly default to False if missing
    p.resources = d.get("resources", p.resources)
    p.applied_clone_id = d.get("applied_clone_id", "")
    p.self_name = d.get("self_name", "")
    
    # Load active tasks if GameState
    if hasattr(p, "active_tasks"):
        p.active_tasks = d.get("active_tasks", {})
    
    # Load UI layout if GameState
    if hasattr(p, "ui_layout"):
        p.ui_layout = d.get("ui_layout", {})
    
    # Initialize practices_xp, ensuring all tracks exist
    saved_practices = d.get("practices_xp", {})
    for track in CONFIG["PRACTICE_TRACKS"]:
        p.practices_xp[track] = saved_practices.get(track, 0)
    
    p.last_saved_ts = d.get("last_saved_ts", time.time())
    
    # Calculate offline passive XP
    hours = max(0.0, (time.time() - p.last_saved_ts) / 3600.0)
    passive = int(hours * CONFIG["PASSIVE_XP_PER_HOUR"])
    if passive > 0:
        for track in CONFIG["PRACTICE_TRACKS"]:
            p.practices_xp[track] += passive
    
    # Load clones
    for cid, c in d.get("clones", {}).items():
        p.clones[cid] = Clone(
            id=c["id"],
            kind=c["kind"],
            traits=c["traits"],
            xp=c["xp"],
            survived_runs=c.get("survived_runs", 0),
            alive=c.get("alive", True),
            uploaded=c.get("uploaded", False)
        )
    
    return p

