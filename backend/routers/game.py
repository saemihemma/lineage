"""
Game API endpoints - handles game actions and state management
"""
import sys
from pathlib import Path

# Add project root to path (needed when running from backend/ directory)
# This is already done in backend/main.py, but doing it here too for safety
_backend_dir = Path(__file__).parent.parent
_project_root = _backend_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import uuid
import time
import logging
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Cookie, Request
from fastapi.responses import JSONResponse
from database import get_db, DatabaseConnection, execute_query
from game.state import GameState
from game.rules import (
    build_womb, grow_clone, apply_clone, run_expedition,
    upload_clone, gather_resource
)
from core.models import Clone
from core.config import CONFIG, RESOURCE_TYPES
from core.state_manager import get_latest_version
from core.game_logic import perk_constructive_craft_time_mult

router = APIRouter(prefix="/api/game", tags=["game"])
logger = logging.getLogger(__name__)

# Environment check
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"

# Rate limiting storage - session-based (more accurate than IP)
_rate_limit_store: Dict[str, Dict[str, list[float]]] = {}

# Session expiration time (24 hours)
SESSION_EXPIRY = 24 * 60 * 60

# Rate limit configurations (requests per minute)
RATE_LIMITS = {
    "get_state": 60,
    "save_state": 30,
    "task_status": 120,
    "gather_resource": 20,
    "build_womb": 5,
    "grow_clone": 10,
    "apply_clone": 10,
    "run_expedition": 10,
    "upload_clone": 10,
}

# Valid input values
VALID_RESOURCES = set(RESOURCE_TYPES)
VALID_CLONE_KINDS = {"BASIC", "MINER", "VOLATILE"}
VALID_EXPEDITION_KINDS = {"MINING", "COMBAT", "EXPLORATION"}


def check_rate_limit(session_id: str, endpoint: str, limit: int) -> tuple[bool, Optional[int]]:
    """
    Check if session is within rate limit for endpoint.
    Returns (is_allowed, retry_after_seconds).
    """
    now = time.time()
    window = 60  # 1 minute window

    # Initialize session storage
    if session_id not in _rate_limit_store:
        _rate_limit_store[session_id] = {}

    # Initialize endpoint storage
    if endpoint not in _rate_limit_store[session_id]:
        _rate_limit_store[session_id][endpoint] = []

    # Clean old entries
    _rate_limit_store[session_id][endpoint] = [
        t for t in _rate_limit_store[session_id][endpoint]
        if now - t < window
    ]

    # Check limit
    if len(_rate_limit_store[session_id][endpoint]) >= limit:
        # Calculate retry-after based on oldest request
        oldest = _rate_limit_store[session_id][endpoint][0]
        retry_after = int(window - (now - oldest)) + 1
        logger.warning(f"Rate limit exceeded for session {session_id[:8]}... on {endpoint}")
        return False, retry_after

    # Record request
    _rate_limit_store[session_id][endpoint].append(now)
    return True, None


def enforce_rate_limit(session_id: str, endpoint: str):
    """Enforce rate limit, raise HTTPException if exceeded."""
    limit = RATE_LIMITS.get(endpoint, 60)
    allowed, retry_after = check_rate_limit(session_id, endpoint, limit)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )


def validate_resource(resource: str) -> str:
    """Validate and sanitize resource input."""
    if not resource or not isinstance(resource, str):
        raise ValueError("Resource must be a non-empty string")

    resource = resource.strip()

    if resource not in VALID_RESOURCES:
        raise ValueError(f"Invalid resource. Must be one of: {', '.join(VALID_RESOURCES)}")

    return resource


def validate_clone_kind(kind: str) -> str:
    """Validate and sanitize clone kind input."""
    if not kind or not isinstance(kind, str):
        raise ValueError("Clone kind must be a non-empty string")

    kind = kind.strip().upper()

    if kind not in VALID_CLONE_KINDS:
        raise ValueError(f"Invalid clone kind. Must be one of: {', '.join(VALID_CLONE_KINDS)}")

    return kind


def validate_expedition_kind(kind: str) -> str:
    """Validate and sanitize expedition kind input."""
    if not kind or not isinstance(kind, str):
        raise ValueError("Expedition kind must be a non-empty string")

    kind = kind.strip().upper()

    if kind not in VALID_EXPEDITION_KINDS:
        raise ValueError(f"Invalid expedition kind. Must be one of: {', '.join(VALID_EXPEDITION_KINDS)}")

    return kind


def validate_clone_id(clone_id: str) -> str:
    """Validate and sanitize clone ID input."""
    if not clone_id or not isinstance(clone_id, str):
        raise ValueError("Clone ID must be a non-empty string")

    clone_id = clone_id.strip()

    # Check for basic sanity (alphanumeric, dashes, underscores)
    if not all(c.isalnum() or c in '-_' for c in clone_id):
        raise ValueError("Invalid clone ID format")

    if len(clone_id) > 100:
        raise ValueError("Clone ID too long")

    return clone_id


def sanitize_error_message(error: Exception) -> str:
    """Sanitize error messages for production, but preserve resource error details."""
    error_str = str(error)
    
    # Always preserve resource error messages (they contain useful info about missing materials)
    # These messages come from format_resource_error() and look like:
    # "Insufficient resources for Womb.\nMissing: Tritanium: 50/100, Metal Ore: 20/40"
    if "Insufficient resources" in error_str or "Missing:" in error_str:
        return error_str
    
    # Always preserve other game logic errors that are user-friendly
    if any(phrase in error_str for phrase in [
        "Build the Womb first",
        "Insufficient soul integrity",
        "Clone unavailable",
        "Cannot apply an uploaded clone",
        "No clone applied to the spaceship",
        "A task is already in progress"
    ]):
        return error_str
    
    if IS_PRODUCTION:
        # Generic error messages in production for unknown errors
        if isinstance(error, ValueError):
            return "Invalid input provided"
        elif isinstance(error, RuntimeError):
            return "Operation failed. Please try again"
        else:
            return "An error occurred"
    else:
        # Detailed errors in development
        return error_str


def check_session_expiry(db: DatabaseConnection, session_id: str) -> bool:
    """Check if session has expired. Returns True if valid, False if expired."""
    cursor = execute_query(
        db,
        "SELECT updated_at FROM game_states WHERE session_id = ?",
        (session_id,)
    )
    row = cursor.fetchone()

    if row is None:
        return True  # New session is valid

    # Parse updated_at timestamp
    updated_at_str = row[0]
    try:
        from datetime import datetime
        updated_at = datetime.fromisoformat(updated_at_str)
        now = datetime.utcnow()
        age_seconds = (now - updated_at).total_seconds()

        if age_seconds > SESSION_EXPIRY:
            # Session expired, clean it up
            execute_query(db, "DELETE FROM game_states WHERE session_id = ?", (session_id,))
            db.commit()
            logger.info(f"Cleaned up expired session {session_id[:8]}...")
            return False

        return True
    except Exception as e:
        logger.error(f"Error checking session expiry: {e}")
        return True  # Allow on error


def get_session_id(session_id: Optional[str] = Cookie(None)) -> str:
    """Get or create session ID from cookie"""
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


def check_and_complete_tasks(state: GameState) -> GameState:
    """
    Check for completed tasks and auto-complete them.
    Returns updated state if any tasks completed, otherwise original state.
    """
    if not state.active_tasks:
        return state
    
    current_time = time.time()
    new_state = state.copy()
    completed_tasks = []
    
    for task_id, task_data in list(new_state.active_tasks.items()):
        start_time = task_data.get('start_time', 0)
        duration = task_data.get('duration', 0)
        
        if current_time >= start_time + duration:
            # Task is complete
            task_type = task_data.get('type')
            
            # Apply resource gathering if this was a gather task
            if task_type == "gather_resource":
                resource = task_data.get('resource')
                pending_amount = task_data.get('pending_amount', 0)
                if resource and pending_amount > 0:
                    new_state.resources[resource] = new_state.resources.get(resource, 0) + pending_amount
                    # Award practice XP
                    from core.game_logic import award_practice_xp
                    award_practice_xp(new_state, "Kinetic", 2)
                    # Store completion message in task data for frontend to retrieve
                    if resource == "Shilajit":
                        task_data['completion_message'] = f"Shilajit sample extracted. Resource +1. Total: {new_state.resources[resource]}"
                    else:
                        task_data['completion_message'] = f"Gathered {pending_amount} {resource}. Total: {new_state.resources[resource]}"
            
            # Complete build_womb if this was a build task
            if task_type == "build_womb":
                new_state.assembler_built = True
                task_data['completion_message'] = "Womb built successfully. You can now grow clones."
            
            # Create clone if this was a grow_clone task
            if task_type == "grow_clone":
                from core.models import Clone
                clone_data = task_data.get('pending_clone_data')
                if clone_data:
                    # Set creation timestamp
                    clone_data['created_at'] = current_time
                    # Create clone and add to state
                    clone = Clone(
                        id=clone_data["id"],
                        kind=clone_data["kind"],
                        traits=clone_data["traits"],
                        xp=clone_data["xp"],
                        survived_runs=clone_data.get("survived_runs", 0),
                        alive=clone_data.get("alive", True),
                        uploaded=clone_data.get("uploaded", False),
                        created_at=clone_data["created_at"]
                    )
                    new_state.clones[clone.id] = clone
                    # Store completion message
                    task_data['completion_message'] = f"{clone_data['kind']} clone grown successfully. id={clone.id}"
            
            completed_tasks.append((task_id, task_type, task_data))
            del new_state.active_tasks[task_id]
    
    return new_state


def calculate_task_duration(task_type: str, state: GameState) -> int:
    """Calculate task duration in seconds"""
    if task_type == "build_womb":
        t_min, t_max = CONFIG["ASSEMBLER_TIME"]
        base_seconds = state.rng.randint(t_min, t_max)
        time_mult = perk_constructive_craft_time_mult(state)
        return int(round(base_seconds * time_mult))
    elif task_type == "grow_clone":
        kind = state.active_tasks.get(list(state.active_tasks.keys())[0] if state.active_tasks else None, {}).get('clone_kind', 'BASIC')
        t_min, t_max = CONFIG["CLONE_TIME"].get(kind, (30, 45))
        base_seconds = state.rng.randint(t_min, t_max)
        time_mult = perk_constructive_craft_time_mult(state)
        return int(round(base_seconds * time_mult))
    elif task_type == "gather_resource":
        resource = state.active_tasks.get(list(state.active_tasks.keys())[0] if state.active_tasks else None, {}).get('resource', 'Tritanium')
        t_min, t_max = CONFIG["GATHER_TIME"].get(resource, (12, 20))
        return state.rng.randint(t_min, t_max)
    return 30  # Default fallback


def start_task(state: GameState, task_type: str, **task_params) -> tuple[GameState, str]:
    """
    Start a timed task. Returns (new_state, task_id).
    Task is stored in active_tasks with start_time and duration.
    
    Task blocking rules:
    - build_womb and grow_clone: Block if ANY task is active (exclusive)
    - gather_resource: Can run alongside expeditions, but only one gather per resource type
    - expeditions: Don't use task system (complete immediately)
    """
    new_state = state.copy()
    
    # Check for conflicting tasks
    if new_state.active_tasks:
        if task_type in ["build_womb", "grow_clone"]:
            # Building/growing blocks on ANY active task
            raise RuntimeError("A task is already in progress. Please wait.")
        elif task_type == "gather_resource":
            # Gathering can run alongside expeditions, but check for duplicate resource gathering
            resource = task_params.get('resource', 'Tritanium')
            for task_id, task_data in new_state.active_tasks.items():
                existing_task_type = task_data.get('type')
                # Can't gather same resource twice, but can gather different resources
                if existing_task_type == "gather_resource" and task_data.get('resource') == resource:
                    raise RuntimeError(f"Already gathering {resource}. Please wait for completion.")
                # Can't gather if building/growing (exclusive tasks)
                if existing_task_type in ["build_womb", "grow_clone"]:
                    raise RuntimeError("Cannot gather resources while building or growing. Please wait.")
    
    # Calculate duration
    if task_type == "build_womb":
        t_min, t_max = CONFIG["ASSEMBLER_TIME"]
        base_seconds = new_state.rng.randint(t_min, t_max)
        time_mult = perk_constructive_craft_time_mult(new_state)
        duration = int(round(base_seconds * time_mult))
    elif task_type == "grow_clone":
        kind = task_params.get('clone_kind', 'BASIC')
        t_min, t_max = CONFIG["CLONE_TIME"].get(kind, (30, 45))
        base_seconds = new_state.rng.randint(t_min, t_max)
        time_mult = perk_constructive_craft_time_mult(new_state)
        duration = int(round(base_seconds * time_mult))
    elif task_type == "gather_resource":
        resource = task_params.get('resource', 'Tritanium')
        t_min, t_max = CONFIG["GATHER_TIME"].get(resource, (12, 20))
        duration = new_state.rng.randint(t_min, t_max)
    else:
        duration = 30
    
    # Create task
    task_id = str(uuid.uuid4())
    new_state.active_tasks[task_id] = {
        'type': task_type,
        'start_time': time.time(),
        'duration': duration,
        **task_params
    }
    
    return new_state, task_id


def game_state_to_dict(state: GameState) -> Dict[str, Any]:
    """Convert GameState to dictionary for JSON serialization"""
    return {
        "version": state.version,
        "rng_seed": state.rng_seed,
        "soul_percent": state.soul_percent,
        "soul_xp": state.soul_xp,
        "soul_level": state.soul_level(),  # Add calculated soul level
        "assembler_built": state.assembler_built,
        "resources": state.resources,
        "applied_clone_id": state.applied_clone_id,
        "practices_xp": state.practices_xp,
        "practice_levels": {  # Add calculated practice levels
            "Kinetic": state.practice_level("Kinetic"),
            "Cognitive": state.practice_level("Cognitive"),
            "Constructive": state.practice_level("Constructive")
        },
        "last_saved_ts": state.last_saved_ts,
        "self_name": state.self_name,
        "active_tasks": getattr(state, "active_tasks", {}),
        "ui_layout": getattr(state, "ui_layout", {}),
        "clones": {
            cid: {
                "id": c.id,
                "kind": c.kind,
                "traits": c.traits,
                "xp": c.xp,
                "survived_runs": c.survived_runs,
                "alive": c.alive,
                "uploaded": c.uploaded,
                "created_at": getattr(c, "created_at", 0.0),
                "biological_days": c.biological_days(time.time()) if hasattr(c, "biological_days") else 0.0
            }
            for cid, c in state.clones.items()
        }
    }


def dict_to_game_state(data: Dict[str, Any]) -> GameState:
    """Convert dictionary to GameState"""
    from core.models import Clone
    
    state = GameState(
        version=data.get("version", get_latest_version()),
        rng_seed=data.get("rng_seed"),
        soul_percent=data.get("soul_percent", CONFIG["SOUL_START"]),
        soul_xp=data.get("soul_xp", 0),
        assembler_built=data.get("assembler_built", False),
        resources=data.get("resources", {}),
        applied_clone_id=data.get("applied_clone_id", ""),
        practices_xp=data.get("practices_xp", {}),
        last_saved_ts=data.get("last_saved_ts", time.time()),
        self_name=data.get("self_name", ""),
        active_tasks=data.get("active_tasks", {}),
        ui_layout=data.get("ui_layout", {})
    )
    
    # Load clones
    clones_data = data.get("clones", {})
    for cid, c_data in clones_data.items():
        state.clones[cid] = Clone(
            id=c_data["id"],
            kind=c_data["kind"],
            traits=c_data.get("traits", {}),
            xp=c_data.get("xp", {}),
            survived_runs=c_data.get("survived_runs", 0),
            alive=c_data.get("alive", True),
            uploaded=c_data.get("uploaded", False),
            created_at=c_data.get("created_at", 0.0)
        )
    
    return state


def load_game_state(db: DatabaseConnection, session_id: str, create_if_missing: bool = False) -> Optional[GameState]:
    """
    Load game state from database.
    
    Args:
        db: Database connection
        session_id: Session identifier
        create_if_missing: If True, create new state if not found (for recovery after redeploy)
    
    Returns:
        GameState if found or created, None otherwise
    """
    cursor = execute_query(
        db,
        "SELECT state_data FROM game_states WHERE session_id = ?",
        (session_id,)
    )
    row = cursor.fetchone()
    if row is None:
        if create_if_missing:
            # Auto-recover: create new state after redeploy/database wipe
            logger.info(f"Auto-recovering: creating new state for session {session_id[:8]}... (likely after redeploy)")
            state = GameState()
            state.version = get_latest_version()
            state.assembler_built = False
            state.last_saved_ts = time.time()
            save_game_state(db, session_id, state)
            return state
        return None
    
    try:
        data = json.loads(row[0])
        state = dict_to_game_state(data)
        
        # Check and complete any finished tasks
        state = check_and_complete_tasks(state)
        if state.active_tasks != data.get("active_tasks", {}):
            # Tasks were completed, save updated state
            save_game_state(db, session_id, state)
        
        return state
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # Corrupted state - auto-recover
        logger.error(f"Corrupted state for session {session_id[:8]}..., recovering: {e}")
        if create_if_missing:
            state = GameState()
            state.version = get_latest_version()
            state.assembler_built = False
            state.last_saved_ts = time.time()
            save_game_state(db, session_id, state)
            return state
        return None


def save_game_state(db: DatabaseConnection, session_id: str, state: GameState, check_version: bool = False):
    """
    Save game state to database with optional optimistic locking.

    Args:
        db: Database connection
        session_id: Session identifier
        state: Game state to save
        check_version: If True, verify version matches before saving (prevents conflicts)

    Raises:
        RuntimeError: If check_version is True and state version doesn't match database
    """
    if check_version:
        # Optimistic locking: check if version matches
        cursor = execute_query(
            db,
            "SELECT state_data FROM game_states WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        if row:
            existing_data = json.loads(row[0])
            existing_version = existing_data.get("version", 1)
            if existing_version != state.version:
                logger.warning(
                    f"State conflict for session {session_id[:8]}...: "
                    f"expected v{state.version}, found v{existing_version}"
                )
                raise RuntimeError(
                    "State conflict detected. Your game state may have been updated in another tab. "
                    "Please refresh the page."
                )

    # Increment version on save to track changes
    state.version += 1
    state_dict = game_state_to_dict(state)
    state_json = json.dumps(state_dict)

    execute_query(db, """
        INSERT INTO game_states (session_id, state_data, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id) DO UPDATE SET
            state_data = excluded.state_data,
            updated_at = CURRENT_TIMESTAMP
    """, (session_id, state_json))
    db.commit()


@router.get("/state")
async def get_game_state(
    request: Request,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Get current game state.
    Creates new state if none exists.
    Rate limit: 60 requests/minute
    """
    sid = get_session_id(session_id)
    enforce_rate_limit(sid, "get_state")

    # Check session expiry
    if not check_session_expiry(db, sid):
        # Session expired, create new one
        sid = str(uuid.uuid4())

    state = load_game_state(db, sid)
    if state is None:
        # Create new game state
        state = GameState()
        state.version = get_latest_version()
        state.assembler_built = False
        state.last_saved_ts = time.time()
        save_game_state(db, sid, state)

    # Check for completed tasks
    state = check_and_complete_tasks(state)
    if state.active_tasks != (state.active_tasks if True else {}):
        save_game_state(db, sid, state)

    response = JSONResponse(content=game_state_to_dict(state))
    response.set_cookie(
        key="session_id",
        value=sid,
        httponly=True,
        samesite="lax",
        secure=IS_PRODUCTION,
        max_age=SESSION_EXPIRY
    )
    return response


@router.get("/tasks/status")
async def get_task_status(
    request: Request,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Get current task status (for polling).
    Returns status of all active tasks, or primary task if only one.
    Rate limit: 120 requests/minute
    """
    sid = get_session_id(session_id)
    enforce_rate_limit(sid, "task_status")

    state = load_game_state(db, sid, create_if_missing=True)

    if state is None or not state.active_tasks:
        return JSONResponse(content={"active": False, "task": None, "tasks": []})

    current_time = time.time()
    tasks_info = []
    completed_tasks = []

    # Check all tasks
    for task_id, task_data in state.active_tasks.items():
        start_time = task_data.get('start_time', 0)
        duration = task_data.get('duration', 0)
        elapsed = current_time - start_time
        remaining = max(0, duration - elapsed)
        progress = min(100, int((elapsed / duration * 100)) if duration > 0 else 0)
        is_complete = current_time >= start_time + duration

        if is_complete:
            completed_tasks.append(task_id)
        else:
            task_type = task_data.get('type', 'unknown')
            label = task_type.replace('_', ' ').title()
            if task_type == "build_womb":
                label = "Building Womb"
            elif task_type == "gather_resource":
                resource = task_data.get('resource', 'Resource')
                label = f"Gathering {resource}"
            elif task_type == "grow_clone":
                clone_kind = task_data.get('clone_kind', 'Clone')
                label = f"Growing {clone_kind} Clone"
            
            tasks_info.append({
                "id": task_id,
                "type": task_type,
                "progress": progress,
                "elapsed": int(elapsed),
                "remaining": int(remaining),
                "duration": duration,
                "label": label
            })

    # Auto-complete finished tasks
    if completed_tasks:
        state = check_and_complete_tasks(state)
        save_game_state(db, sid, state)

    # Return primary task (first one) for backward compatibility, plus all tasks
    primary_task = tasks_info[0] if tasks_info else None
    
    return JSONResponse(content={
        "active": len(tasks_info) > 0,
        "task": primary_task,  # Primary task for backward compatibility
        "tasks": tasks_info,   # All active tasks
        "completed": len(completed_tasks) > 0
    })


@router.post("/state")
async def save_game_state_endpoint(
    state_data: Dict[str, Any],
    request: Request,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Save game state.
    Rate limit: 30 requests/minute
    Max request size: 1MB
    """
    sid = get_session_id(session_id)
    enforce_rate_limit(sid, "save_state")

    try:
        state = dict_to_game_state(state_data)
        state.last_saved_ts = time.time()
        save_game_state(db, sid, state)

        response = JSONResponse(content={"status": "saved"})
        response.set_cookie(
            key="session_id",
            value=sid,
            httponly=True,
            samesite="lax",
            secure=IS_PRODUCTION,
            max_age=SESSION_EXPIRY
        )
        return response
    except Exception as e:
        error_msg = sanitize_error_message(e)
        logger.error(f"Error saving game state for session {sid[:8]}...: {str(e)}")
        raise HTTPException(status_code=400, detail=error_msg)


@router.post("/gather-resource")
async def gather_resource_endpoint(
    resource: str,
    request: Request,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Gather a resource (starts timer, completes immediately but UI waits).
    Rate limit: 20 requests/minute
    """
    sid = get_session_id(session_id)
    enforce_rate_limit(sid, "gather_resource")

    # Validate input
    try:
        resource = validate_resource(resource)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(e))

    state = load_game_state(db, sid, create_if_missing=True)
    
    if state is None:
        # This should rarely happen now (auto-recovery), but handle it gracefully
        raise HTTPException(
            status_code=404, 
            detail="Game state not found. Your session may have been lost during a backend restart. Please refresh the page."
        )

    # Note: Task conflict checking is now done in start_task()
    # Gathering can run alongside expeditions, but blocks on build/grow tasks

    try:
        # Calculate gather amount now (but don't apply until task completes)
        # Use a deterministic RNG state to calculate amount
        amount = state.rng.randint(
            CONFIG["GATHER_AMOUNT"][resource][0],
            CONFIG["GATHER_AMOUNT"][resource][1]
        )
        if resource == "Shilajit":
            amount = 1
        
        # Start task timer with pending resource amount stored
        new_state, task_id = start_task(state, "gather_resource", resource=resource, pending_amount=amount)

        # Don't add resources yet - they'll be added when task completes
        # Just save state with the active task
        save_game_state(db, sid, new_state)

        # Create message for when task completes (but don't show yet)
        if resource == "Shilajit":
            message = "Shilajit sample extracted. Resource +1."
        else:
            # We'll update the total when task completes
            message = f"Gathered {amount} {resource}."
        
        response = JSONResponse(content={
            "state": game_state_to_dict(new_state),  # Return state WITHOUT resources added yet
            "message": message,
            "amount": amount,
            "task_id": task_id
        })
        response.set_cookie(
            key="session_id",
            value=sid,
            httponly=True,
            samesite="lax",
            secure=IS_PRODUCTION,
            max_age=SESSION_EXPIRY
        )
        return response
    except Exception as e:
        error_msg = sanitize_error_message(e)
        logger.error(f"Error gathering resource for session {sid[:8]}...: {str(e)}")
        raise HTTPException(status_code=400, detail=error_msg)


@router.post("/build-womb")
async def build_womb_endpoint(
    request: Request,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Build the Womb (assembler) - starts timer.
    Rate limit: 5 requests/minute
    """
    sid = get_session_id(session_id)
    enforce_rate_limit(sid, "build_womb")

    state = load_game_state(db, sid, create_if_missing=True)
    
    if state is None:
        # This should rarely happen now (auto-recovery), but handle it gracefully
        raise HTTPException(
            status_code=404, 
            detail="Game state not found. Your session may have been lost during a backend restart. Please refresh the page."
        )

    # Check for active tasks
    if state.active_tasks:
        raise HTTPException(status_code=400, detail="A task is already in progress")

    try:
        # Actually build (happens immediately)
        new_state, message = build_womb(state)

        # Start timer task
        final_state, task_id = start_task(new_state, "build_womb")

        save_game_state(db, sid, final_state)

        response = JSONResponse(content={
            "state": game_state_to_dict(final_state),
            "message": message,
            "task_id": task_id
        })
        response.set_cookie(
            key="session_id",
            value=sid,
            httponly=True,
            samesite="lax",
            secure=IS_PRODUCTION,
            max_age=SESSION_EXPIRY
        )
        return response
    except Exception as e:
        error_msg = sanitize_error_message(e)
        logger.error(f"Error building womb for session {sid[:8]}...: {str(e)}")
        raise HTTPException(status_code=400, detail=error_msg)


@router.post("/grow-clone")
async def grow_clone_endpoint(
    kind: str,
    request: Request,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Grow a new clone - starts timer.
    Rate limit: 10 requests/minute
    """
    sid = get_session_id(session_id)
    enforce_rate_limit(sid, "grow_clone")

    # Validate input
    try:
        kind = validate_clone_kind(kind)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(e))

    state = load_game_state(db, sid, create_if_missing=True)
    
    if state is None:
        # This should rarely happen now (auto-recovery), but handle it gracefully
        raise HTTPException(
            status_code=404, 
            detail="Game state not found. Your session may have been lost during a backend restart. Please refresh the page."
        )

    # Check for active tasks
    if state.active_tasks:
        raise HTTPException(status_code=400, detail="A task is already in progress")

    try:
        # Prepare clone data (but don't create clone yet - will be created when task completes)
        new_state, clone, soul_split, message, clone_data = grow_clone(state, kind)

        # Start timer task with clone data stored
        final_state, task_id = start_task(new_state, "grow_clone", clone_kind=kind, pending_clone_data=clone_data)

        # Don't add clone to state yet - it will be added when task completes
        save_game_state(db, sid, final_state)

        response = JSONResponse(content={
            "state": game_state_to_dict(final_state),  # Return state WITHOUT clone added yet
            "clone": None,  # Clone not created yet - will appear when task completes
            "soul_split": soul_split,
            "message": message,
            "task_id": task_id
        })
        response.set_cookie(
            key="session_id",
            value=sid,
            httponly=True,
            samesite="lax",
            secure=IS_PRODUCTION,
            max_age=SESSION_EXPIRY
        )
        return response
    except Exception as e:
        error_msg = sanitize_error_message(e)
        logger.error(f"Error growing clone for session {sid[:8]}...: {str(e)}")
        raise HTTPException(status_code=400, detail=error_msg)


@router.post("/apply-clone")
async def apply_clone_endpoint(
    clone_id: str,
    request: Request,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Apply a clone (activate it).
    Rate limit: 10 requests/minute
    """
    sid = get_session_id(session_id)
    enforce_rate_limit(sid, "apply_clone")

    # Validate input
    try:
        clone_id = validate_clone_id(clone_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(e))

    state = load_game_state(db, sid, create_if_missing=True)
    
    if state is None:
        # This should rarely happen now (auto-recovery), but handle it gracefully
        raise HTTPException(
            status_code=404, 
            detail="Game state not found. Your session may have been lost during a backend restart. Please refresh the page."
        )

    try:
        new_state, message = apply_clone(state, clone_id)
        save_game_state(db, sid, new_state)

        response = JSONResponse(content={
            "state": game_state_to_dict(new_state),
            "message": message
        })
        response.set_cookie(
            key="session_id",
            value=sid,
            httponly=True,
            samesite="lax",
            secure=IS_PRODUCTION,
            max_age=SESSION_EXPIRY
        )
        return response
    except Exception as e:
        error_msg = sanitize_error_message(e)
        logger.error(f"Error applying clone for session {sid[:8]}...: {str(e)}")
        raise HTTPException(status_code=400, detail=error_msg)


@router.post("/run-expedition")
async def run_expedition_endpoint(
    kind: str,
    request: Request,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Run an expedition (Mining, Combat, or Exploration).
    Rate limit: 10 requests/minute
    """
    sid = get_session_id(session_id)
    enforce_rate_limit(sid, "run_expedition")

    # Validate input
    try:
        kind = validate_expedition_kind(kind)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(e))

    state = load_game_state(db, sid, create_if_missing=True)
    
    if state is None:
        # This should rarely happen now (auto-recovery), but handle it gracefully
        raise HTTPException(
            status_code=404, 
            detail="Game state not found. Your session may have been lost during a backend restart. Please refresh the page."
        )

    try:
        new_state, message = run_expedition(state, kind)
        save_game_state(db, sid, new_state)

        response = JSONResponse(content={
            "state": game_state_to_dict(new_state),
            "message": message
        })
        response.set_cookie(
            key="session_id",
            value=sid,
            httponly=True,
            samesite="lax",
            secure=IS_PRODUCTION,
            max_age=SESSION_EXPIRY
        )
        return response
    except Exception as e:
        error_msg = sanitize_error_message(e)
        logger.error(f"Error running expedition for session {sid[:8]}...: {str(e)}")
        raise HTTPException(status_code=400, detail=error_msg)


@router.post("/upload-clone")
async def upload_clone_endpoint(
    clone_id: str,
    request: Request,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Upload a clone to SELF.
    Rate limit: 10 requests/minute
    """
    sid = get_session_id(session_id)
    enforce_rate_limit(sid, "upload_clone")

    # Validate input
    try:
        clone_id = validate_clone_id(clone_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(e))

    state = load_game_state(db, sid, create_if_missing=True)
    
    if state is None:
        # This should rarely happen now (auto-recovery), but handle it gracefully
        raise HTTPException(
            status_code=404, 
            detail="Game state not found. Your session may have been lost during a backend restart. Please refresh the page."
        )

    try:
        new_state, message = upload_clone(state, clone_id)
        save_game_state(db, sid, new_state)

        response = JSONResponse(content={
            "state": game_state_to_dict(new_state),
            "message": message
        })
        response.set_cookie(
            key="session_id",
            value=sid,
            httponly=True,
            samesite="lax",
            secure=IS_PRODUCTION,
            max_age=SESSION_EXPIRY
        )
        return response
    except Exception as e:
        error_msg = sanitize_error_message(e)
        logger.error(f"Error uploading clone for session {sid[:8]}...: {str(e)}")
        raise HTTPException(status_code=400, detail=error_msg)
