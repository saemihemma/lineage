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


def set_session_cookie(response: JSONResponse, session_id: str, cookie_name: str = "session_id"):
    """
    Helper to set session cookie with consistent settings.
    Handles Railway/production cookie requirements.
    
    For Railway: May need SameSite=None with Secure=True if behind proxy.
    SameSite=None REQUIRES Secure=True (browser security requirement).
    """
    # Check for Railway-specific environment variable to use SameSite=None
    use_samesite_none = os.getenv("RAILWAY_ENVIRONMENT", "").lower() == "production" or \
                       os.getenv("USE_SAMESITE_NONE", "false").lower() == "true"
    
    # For Railway/production with potential proxy: try SameSite=None
    # SameSite=None REQUIRES Secure=True (browser security)
    if IS_PRODUCTION and use_samesite_none:
        same_site_value = "none"
        secure_value = True  # Required when SameSite=None
        logger.info(f"🍪 Railway mode: Setting cookie {cookie_name} with SameSite=None, Secure=True")
    else:
        same_site_value = "lax"
        secure_value = IS_PRODUCTION  # True in production (HTTPS), False in dev (HTTP)
        logger.debug(f"🍪 Setting cookie {cookie_name}: same_site={same_site_value}, secure={secure_value}, httponly=True")
    
    response.set_cookie(
        key=cookie_name,
        value=session_id,
        httponly=True,
        samesite=same_site_value,
        secure=secure_value,
        max_age=SESSION_EXPIRY,
        path="/"  # Explicit path
    )

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


def emit_event(
    db: DatabaseConnection,
    session_id: str,
    event_type: str,
    event_data: Dict[str, Any],
    entity_id: Optional[str] = None
) -> None:
    """
    Emit an event to the events feed.
    Events are stored in the database for the events feed endpoint.
    """
    try:
        event_id = str(uuid.uuid4())
        event_subtype = None
        
        # Map event types to database fields
        # Frontend expects: gather.start, gather.complete, clone.grow.start, etc.
        # Database uses: event_type, event_subtype
        if "." in event_type:
            parts = event_type.split(".", 1)
            event_type_db = parts[0]  # e.g., "gather", "clone", "expedition"
            event_subtype = parts[1]   # e.g., "start", "complete", "result"
        else:
            event_type_db = event_type
        
        payload_json = json.dumps(event_data)
        
        try:
            execute_query(db, """
                INSERT INTO events (id, session_id, event_type, event_subtype, entity_id, payload_json, privacy_level, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'private', CURRENT_TIMESTAMP)
            """, (
                event_id,
                session_id,
                event_type_db,
                event_subtype,
                entity_id,
                payload_json
            ))
            db.commit()
        except Exception as db_error:
            # Rollback on error to prevent transaction cascade
            try:
                db.rollback()
            except Exception:
                pass
            # Don't break the game if event emission fails
            logger.warning(f"Failed to emit event {event_type} for session {session_id[:8]}...: {db_error}")
    except Exception as e:
        # Don't break the game if event emission fails
        logger.warning(f"Failed to emit event {event_type} for session {session_id[:8]}...: {e}")


def check_session_expiry(db: DatabaseConnection, session_id: str) -> bool:
    """Check if session has expired. Returns True if valid, False if expired."""
    # Check if transaction is in error state (PostgreSQL specific)
    # If so, force connection recreation to get a clean connection
    try:
        if hasattr(db, 'status'):
            # PostgreSQL connection status check
            import psycopg2
            from psycopg2.extensions import STATUS_READY, STATUS_IN_TRANSACTION
            
            status = db.status
            # If connection is in transaction state (shouldn't happen with autocommit),
            # or connection is closed/invalid, force connection recreation
            if status < 0 or status == STATUS_IN_TRANSACTION:
                # Connection is in bad state - force recreation by closing global connection
                try:
                    from backend.database import _db_instance
                    if _db_instance and hasattr(_db_instance, 'adapter') and _db_instance.adapter:
                        _db_instance.adapter.close()  # Force close to trigger recreation
                        if hasattr(_db_instance.adapter, 'conn'):
                            _db_instance.adapter.conn = None
                        if hasattr(_db_instance, 'conn'):
                            _db_instance.conn = None
                        logger.warning("Closed bad PostgreSQL connection, will recreate on next use")
                except Exception as e:
                    logger.debug(f"Could not force close connection: {e}")
                # Try rollback as fallback
                try:
                    db.rollback()
                except Exception:
                    pass
    except Exception:
        # Not PostgreSQL or status check failed, continue
        pass
    
    try:
        cursor = execute_query(
            db,
            "SELECT updated_at FROM game_states WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()

        if row is None:
            return True  # New session is valid

        # Parse updated_at timestamp
        # PostgreSQL returns datetime objects, SQLite returns strings
        updated_at_value = row['updated_at']
        try:
            from datetime import datetime
            if isinstance(updated_at_value, datetime):
                # PostgreSQL returns datetime object directly
                updated_at = updated_at_value
            else:
                # SQLite returns string, parse it
                updated_at = datetime.fromisoformat(str(updated_at_value))
            now = datetime.utcnow()
            age_seconds = (now - updated_at).total_seconds()

            if age_seconds > SESSION_EXPIRY:
                # Session expired, clean it up
                try:
                    execute_query(db, "DELETE FROM game_states WHERE session_id = ?", (session_id,))
                    # Don't need commit() with autocommit, but harmless if called
                    try:
                        db.commit()
                    except Exception:
                        pass  # Ignore commit errors with autocommit
                    logger.info(f"Cleaned up expired session {session_id[:8]}...")
                    return False
                except Exception as delete_error:
                    # Rollback on error
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    logger.error(f"Error deleting expired session {session_id[:8]}...: {delete_error}")
                    return True  # Allow on error

            return True
        except Exception as e:
            logger.error(f"Error parsing timestamp in check_session_expiry: {e}")
            return True  # Allow on error
    except Exception as e:
        # Query failed - likely transaction aborted or connection issue
        # Force connection recreation
        error_str = str(e).lower()
        if ("current transaction is aborted" in error_str or 
            "transaction" in error_str and "aborted" in error_str):
            try:
                from backend.database import _db_instance
                if _db_instance and hasattr(_db_instance, 'adapter') and _db_instance.adapter:
                    _db_instance.adapter.close()
                    if hasattr(_db_instance.adapter, 'conn'):
                        _db_instance.adapter.conn = None
                    if hasattr(_db_instance, 'conn'):
                        _db_instance.conn = None
                    logger.warning("Closed bad connection after transaction abort error, will recreate")
            except Exception as close_error:
                logger.debug(f"Could not force close connection after error: {close_error}")
        # Try rollback as fallback
        try:
            db.rollback()
            logger.info("Rolled back transaction after check_session_expiry error")
        except Exception:
            pass
        return True  # Allow on error - fail open to prevent breaking the game


def get_session_id(session_id: Optional[str] = Cookie(None), request: Optional[Request] = None) -> str:
    """
    Get or create session ID from cookie.
    Note: Caller must ensure cookie is set in response if new session is created.
    Session ID is used for rate limiting and CSRF tokens (short-term tracking).
    """
    if not session_id:
        session_id = str(uuid.uuid4())
        # Log more details about why new session was created
        cookie_header = request.headers.get("Cookie", "") if request else "N/A"
        logger.warning(f"🆕 New session created: {session_id[:8]}... (Cookie header present: {bool(cookie_header)}, length: {len(cookie_header)})")
        if request:
            logger.debug(f"   Request headers: Cookie={cookie_header[:100]}...")
    else:
        logger.debug(f"📋 Existing session: {session_id[:8]}...")
    return session_id


def get_player_id(player_id: Optional[str] = None, session_id: Optional[str] = None) -> str:
    """
    Get or create player ID.
    
    Priority:
    1. Use provided player_id (from frontend localStorage)
    2. Fall back to session_id if player_id not provided (backward compatibility)
    
    Player ID is persistent and stored in localStorage on frontend.
    It's used for saving/loading game state (long-term persistence).
    
    Args:
        player_id: Player ID from frontend (preferred)
        session_id: Session ID as fallback (backward compatibility)
    
    Returns:
        Player ID string
    """
    if player_id:
        logger.debug(f"📋 Using provided player_id: {player_id[:8]}...")
        return player_id
    
    # Fallback to session_id for backward compatibility
    if session_id:
        logger.debug(f"📋 Falling back to session_id as player_id: {session_id[:8]}...")
        return session_id
    
    # Generate new player_id if neither provided
    new_player_id = str(uuid.uuid4())
    logger.info(f"🆕 Generated new player_id: {new_player_id[:8]}...")
    return new_player_id


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
    
    logger.debug(f"🔍 check_and_complete_tasks: Checking {len(new_state.active_tasks)} task(s) at time {current_time:.2f}")
    
    for task_id, task_data in list(new_state.active_tasks.items()):
        start_time = task_data.get('start_time', 0)
        duration = task_data.get('duration', 0)
        task_type = task_data.get('type', 'unknown')
        
        # Debug: log task timing details
        elapsed = current_time - start_time
        remaining = max(0, (start_time + duration) - current_time)
        
        logger.debug(f"📋 Task {task_id}: type={task_type}, start={start_time:.2f}, duration={duration}, elapsed={elapsed:.2f}, remaining={remaining:.2f}")
        
        if duration <= 0:
            logger.warning(f"⚠️ Task {task_id} ({task_type}) has invalid duration: {duration}. start_time: {start_time}, current: {current_time}")
        elif remaining <= 0:
            logger.info(f"✅ Task {task_id} ({task_type}) completed: elapsed={elapsed:.1f}s, duration={duration}s")
        
        if current_time >= start_time + duration:
            # Task is complete
            logger.info(f"🔔 Task {task_id} ({task_type}) is COMPLETE - entering completion handler")
            task_type = task_data.get('type')
            logger.debug(f"🔍 Processing completion for task_type='{task_type}'")
            
            # Apply resource gathering if this was a gather task
            if task_type == "gather_resource":
                resource = task_data.get('resource')
                pending_amount = task_data.get('pending_amount', 0)
                if resource and pending_amount > 0:
                    old_total = new_state.resources.get(resource, 0)
                    new_state.resources[resource] = old_total + pending_amount
                    new_total = new_state.resources[resource]
                    
                    # Award practice XP
                    from core.game_logic import award_practice_xp
                    award_practice_xp(new_state, "Kinetic", 2)
                    
                    # Store completion message in task data for frontend to retrieve
                    if resource == "Shilajit":
                        task_data['completion_message'] = f"Shilajit sample extracted. Resource +1. Total: {new_total}"
                    else:
                        task_data['completion_message'] = f"Gathered {pending_amount} {resource}. Total: {new_total}"
                    
                    # Note: gather.complete event will be emitted when state is saved (after this function returns)
            
            # Complete build_womb if this was a build task
            if task_type == "build_womb":
                logger.info(f"🏗️ Entering build_womb completion handler")
                from game.wombs import create_womb
                # Create new womb with index based on current count
                old_womb_count = len(new_state.wombs) if new_state.wombs else 0
                logger.debug(f"🏗️ build_womb: old_womb_count={old_womb_count}, wombs array exists={new_state.wombs is not None}")
                new_womb_id = old_womb_count
                try:
                    new_womb = create_womb(new_womb_id)
                    logger.debug(f"🏗️ build_womb: Created womb object, id={new_womb.id}, durability={new_womb.durability}")
                except Exception as e:
                    logger.error(f"❌ build_womb: Failed to create_womb: {e}")
                    raise
                
                if not new_state.wombs:
                    logger.debug(f"🏗️ build_womb: Initializing wombs array (was None)")
                    new_state.wombs = []
                new_state.wombs.append(new_womb)
                logger.debug(f"🏗️ build_womb: Appended womb, new count={len(new_state.wombs)}")
                
                # Also set assembler_built for backward compatibility (if first womb)
                if len(new_state.wombs) == 1:
                    new_state.assembler_built = True
                    logger.debug(f"🏗️ build_womb: Set assembler_built=True (first womb)")
                
                task_data['completion_message'] = f"Womb {new_womb_id + 1} built successfully. You can now grow clones."
                logger.info(f"🏗️ Womb created: ID={new_womb_id}, total wombs={len(new_state.wombs)}, durability={new_womb.durability}/{new_womb.max_durability}, assembler_built={new_state.assembler_built}")
            else:
                logger.debug(f"🔍 Task {task_id} type '{task_type}' is not 'build_womb', skipping womb creation")
            
            # Complete repair_womb if this was a repair task
            if task_type == "repair_womb":
                womb_id = task_data.get('womb_id')
                repair_amount = task_data.get('repair_amount', 0)
                if womb_id is not None:
                    target_womb = next((w for w in new_state.wombs if w.id == womb_id), None)
                    if target_womb:
                        # Restore durability to full
                        target_womb.durability = target_womb.max_durability
                        task_data['completion_message'] = f"Womb {womb_id} repaired to full durability."
            
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
                    
                    # Store clone data in task_data for event emission later
                    task_data['completed_clone'] = {
                        "id": clone.id,
                        "kind": clone.kind,
                        "xp": clone.xp,
                        "created_at": clone.created_at
                    }
            
            completed_tasks.append((task_id, task_type, task_data))
            del new_state.active_tasks[task_id]
            logger.info(f"🗑️ Removed completed task {task_id} ({task_type}) from active_tasks. Remaining: {len(new_state.active_tasks)}")
    
    if completed_tasks:
        logger.info(f"✅ check_and_complete_tasks: Completed {len(completed_tasks)} task(s): {[t[1] for t in completed_tasks]}")
    else:
        logger.debug(f"ℹ️ check_and_complete_tasks: No tasks completed")
    
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
    elif task_type == "repair_womb":
        from game.wombs import calculate_repair_time
        womb_id = state.active_tasks.get(list(state.active_tasks.keys())[0] if state.active_tasks else None, {}).get('womb_id')
        if womb_id is not None:
            target_womb = next((w for w in state.wombs if w.id == womb_id), None)
            if target_womb:
                return calculate_repair_time(state, target_womb)
        return 30  # Fallback
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
        if task_type in ["build_womb", "grow_clone", "repair_womb"]:
            # Building/growing/repairing blocks on ANY active task
            raise RuntimeError("A task is already in progress. Please wait.")
        elif task_type == "gather_resource":
            # Gathering can run alongside expeditions, but check for duplicate resource gathering
            resource = task_params.get('resource', 'Tritanium')
            for task_id, task_data in new_state.active_tasks.items():
                existing_task_type = task_data.get('type')
                # Can't gather same resource twice, but can gather different resources
                if existing_task_type == "gather_resource" and task_data.get('resource') == resource:
                    raise RuntimeError(f"Already gathering {resource}. Please wait for completion.")
                # Can't gather if building/growing/repairing (exclusive tasks)
                if existing_task_type in ["build_womb", "grow_clone", "repair_womb"]:
                    raise RuntimeError("Cannot gather resources while building, growing, or repairing. Please wait.")
    
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
    elif task_type == "repair_womb":
        from game.wombs import calculate_repair_time
        womb_id = task_params.get('womb_id')
        if womb_id is not None:
            target_womb = next((w for w in new_state.wombs if w.id == womb_id), None)
            if target_womb:
                duration = calculate_repair_time(new_state, target_womb)
            else:
                duration = 30
        else:
            duration = 30
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
    from core.models import Womb
    
    result = {
        "version": state.version,
        "rng_seed": state.rng_seed,
        "soul_percent": state.soul_percent,
        "soul_xp": state.soul_xp,
        "soul_level": state.soul_level(),  # Add calculated soul level
        "assembler_built": state.assembler_built,  # Keep for backward compatibility
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
    
    # Add wombs array if it exists
    if hasattr(state, 'wombs') and state.wombs:
        result["wombs"] = [
            {
                "id": w.id,
                "durability": w.durability,
                "attention": w.attention,
                "max_durability": w.max_durability,
                "max_attention": w.max_attention
            }
            for w in state.wombs
        ]
    else:
        result["wombs"] = []
    
    return result


def dict_to_game_state(data: Dict[str, Any]) -> GameState:
    """Convert dictionary to GameState, applying migrations if needed"""
    from core.models import Clone, Womb
    from game.migrations.migrate import migrate, get_latest_version
    
    # Check version and migrate if needed
    saved_version = data.get("version", 0)  # 0 means pre-versioned
    latest_version = get_latest_version()
    
    if saved_version < latest_version:
        # Apply migrations
        data = migrate(data, saved_version, latest_version)
    
    state = GameState(
        version=data.get("version", latest_version),
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
    
    # Load wombs
    wombs_data = data.get("wombs", [])
    if wombs_data:
        state.wombs = [
            Womb(
                id=w_data.get("id", i),
                durability=w_data.get("durability", CONFIG["WOMB_MAX_DURABILITY"]),
                attention=w_data.get("attention", CONFIG["WOMB_MAX_ATTENTION"]),
                max_durability=w_data.get("max_durability", CONFIG["WOMB_MAX_DURABILITY"]),
                max_attention=w_data.get("max_attention", CONFIG["WOMB_MAX_ATTENTION"])
            )
            for i, w_data in enumerate(wombs_data)
        ]
    else:
        state.wombs = []
    
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


def load_game_state(db: DatabaseConnection, player_id: str, session_id: Optional[str] = None, create_if_missing: bool = False) -> Optional[GameState]:
    """
    Load game state from database using player_id (persistent identifier).
    
    Args:
        db: Database connection
        player_id: Player identifier (from localStorage, persistent)
        session_id: Optional session identifier (for logging/migration)
        create_if_missing: If True, create new state if not found (for recovery after redeploy)
    
    Returns:
        GameState if found or created, None otherwise
    """
    logger.debug(f"🔍 Loading state for player_id: {player_id[:8]}...")
    
    # Try to load by player_id first (new system)
    cursor = execute_query(
        db,
        "SELECT state_data FROM game_states WHERE player_id = ?",
        (player_id,)
    )
    row = cursor.fetchone()
    
    # Fallback: if no player_id match and session_id provided, try legacy session_id lookup
    if row is None and session_id:
        logger.debug(f"⚠️ No state found for player_id {player_id[:8]}..., trying legacy session_id {session_id[:8]}...")
        cursor = execute_query(
            db,
            "SELECT state_data FROM game_states WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        if row:
            # Found by session_id - migrate to player_id
            logger.info(f"🔄 Migrating state from session_id to player_id: {session_id[:8]}... → {player_id[:8]}...")
            try:
                execute_query(
                    db,
                    "UPDATE game_states SET player_id = ? WHERE session_id = ?",
                    (player_id, session_id)
                )
                logger.info(f"✅ Migration complete: state now uses player_id {player_id[:8]}...")
            except Exception as migrate_error:
                logger.warning(f"⚠️ Migration failed: {migrate_error}")
    
    if row is None:
        logger.debug(f"❌ No state found for player_id: {player_id[:8]}..., create_if_missing={create_if_missing}")
        if create_if_missing:
            # Auto-recover: create new state after redeploy/database wipe
            logger.info(f"Auto-recovering: creating new state for player_id {player_id[:8]}... (likely after redeploy)")
            state = GameState()
            state.version = get_latest_version()
            state.assembler_built = False
            state.last_saved_ts = time.time()
            save_game_state(db, player_id, state, session_id=session_id)
            return state
        return None
    
    try:
        data = json.loads(row['state_data'])
        state = dict_to_game_state(data)
        
        womb_count = len(state.wombs) if state.wombs else 0
        logger.debug(f"✅ State loaded for session {session_id[:8]}... - Wombs: {womb_count}, Assembler: {state.assembler_built}, Self: {state.self_name}")
        
        # Check and complete any finished tasks
        state = check_and_complete_tasks(state)
        if state.active_tasks != data.get("active_tasks", {}):
            # Tasks were completed, save updated state
            logger.info(f"🔄 Tasks completed during load, saving updated state for player_id {player_id[:8]}...")
            save_game_state(db, player_id, state, session_id=session_id)
        
        return state
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # Corrupted state - auto-recover
        logger.error(f"Corrupted state for player_id {player_id[:8]}..., recovering: {e}")
        if create_if_missing:
            state = GameState()
            state.version = get_latest_version()
            state.assembler_built = False
            state.last_saved_ts = time.time()
            save_game_state(db, player_id, state, session_id=session_id)
            return state
        return None


def save_game_state(db: DatabaseConnection, player_id: str, state: GameState, check_version: bool = False, session_id: Optional[str] = None):
    """
    Save game state to database using player_id (persistent identifier).
    Applies womb systems (decay, attacks) before saving.

    Args:
        db: Database connection
        player_id: Player identifier (from localStorage, persistent)
        state: Game state to save
        check_version: If True, verify version matches before saving (prevents conflicts)
        session_id: Optional session identifier (for logging/migration)

    Raises:
        RuntimeError: If check_version is True and state version doesn't match database
    """
    # Apply womb systems (decay, attacks) before saving
    from game.wombs import check_and_apply_womb_systems
    state = check_and_apply_womb_systems(state)
    
    if check_version:
        # Optimistic locking: check if version matches
        cursor = execute_query(
            db,
            "SELECT state_data FROM game_states WHERE player_id = ?",
            (player_id,)
        )
        row = cursor.fetchone()
        if row:
            existing_data = json.loads(row['state_data'])
            existing_version = existing_data.get("version", 1)
            if existing_version != state.version:
                logger.warning(
                    f"State conflict for player_id {player_id[:8]}...: "
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
    
    # Log save details
    womb_count = len(state.wombs) if state.wombs else 0
    logger.debug(f"💾 Saving state - Player: {player_id[:8]}..., Wombs: {womb_count}, Assembler: {state.assembler_built}, Self: {state.self_name}, Version: {state.version}")

    try:
        # Use player_id as primary key, store session_id for migration/backward compatibility
        execute_query(db, """
            INSERT INTO game_states (player_id, session_id, state_data, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(player_id) DO UPDATE SET
                session_id = excluded.session_id,
                state_data = excluded.state_data,
                updated_at = CURRENT_TIMESTAMP
        """, (player_id, session_id, state_json))
        db.commit()
    except Exception as db_error:
        # Rollback on error to prevent transaction cascade
        try:
            db.rollback()
        except Exception as rollback_error:
            logger.error(f"Failed to rollback transaction in save_game_state: {rollback_error}")
        logger.error(f"Database error saving game state for player_id {player_id[:8]}...: {db_error}")
        raise


@router.get("/state")
async def get_game_state(
    request: Request,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Get current game state.
    Creates new state if none exists.
    Includes CSRF token for state-changing requests.
    Rate limit: 60 requests/minute
    """
    from core.csrf import generate_csrf_cookie_value

    sid = get_session_id(session_id, request)
    logger.info(f"📥 GET /state - Session: {sid[:8]}..., Cookie present: {session_id is not None}")
    enforce_rate_limit(sid, "get_state")

    # Check if this is a new session (no cookie provided)
    is_new_session = not session_id
    
    # Check session expiry
    if not check_session_expiry(db, sid):
        # Session expired, create new one
        sid = str(uuid.uuid4())
        is_new_session = True

    state = load_game_state(db, sid)
    if state is None:
        # Create new game state
        logger.info(f"🆕 Creating new game state for session {sid[:8]}...")
        state = GameState()
        state.version = get_latest_version()
        state.assembler_built = False
        state.last_saved_ts = time.time()
        save_game_state(db, sid, state)
        is_new_session = True  # Mark as new since we just created state
    else:
        womb_count = len(state.wombs) if state.wombs else 0
        logger.debug(f"📦 Loaded state for session {sid[:8]}... - Wombs: {womb_count}, Assembler: {state.assembler_built}, Self: {state.self_name}")

    # Check for completed tasks
    old_active_tasks = state.active_tasks.copy() if state.active_tasks else {}
    old_womb_count = len(state.wombs) if state.wombs else 0
    logger.debug(f"🔍 Before check_and_complete_tasks: active_tasks={len(old_active_tasks)}, wombs={old_womb_count}")
    state = check_and_complete_tasks(state)
    new_womb_count = len(state.wombs) if state.wombs else 0
    logger.debug(f"🔍 After check_and_complete_tasks: active_tasks={len(state.active_tasks) if state.active_tasks else 0}, wombs={new_womb_count}")
    
    if state.active_tasks != old_active_tasks:
        # Tasks were completed - emit completion events
        logger.info(f"🔄 Tasks completed during load, saving updated state for session {session_id[:8]}... (wombs: {old_womb_count} → {new_womb_count})")
        save_game_state(db, session_id, state)
        for task_id, old_task_data in old_active_tasks.items():
            if task_id not in state.active_tasks:
                # Task was completed
                task_type = old_task_data.get('type')
                
                if task_type == "gather_resource":
                    resource = old_task_data.get('resource')
                    if resource:
                        new_total = state.resources.get(resource, 0)
                        delta = old_task_data.get('pending_amount', 0)
                        emit_event(db, sid, "gather.complete", {
                            "resource": resource,
                            "delta": delta,
                            "new_total": new_total
                        })
                        emit_event(db, sid, "resource.delta", {
                            "resource": resource,
                            "delta": delta,
                            "new_total": new_total
                        })
                
                elif task_type == "grow_clone":
                    completed_clone = old_task_data.get('completed_clone')
                    if completed_clone:
                        emit_event(db, sid, "clone.grow.complete", {
                            "clone": completed_clone
                        }, entity_id=completed_clone.get("id"))
    elif new_womb_count != old_womb_count:
        # Wombs changed but tasks didn't (edge case - should save anyway)
        logger.warning(f"⚠️ Wombs changed ({old_womb_count} → {new_womb_count}) but active_tasks unchanged - saving anyway")
        save_game_state(db, session_id, state)

    # Generate CSRF token for this session
    csrf_token = generate_csrf_cookie_value(sid)

    response = JSONResponse(content=game_state_to_dict(state))

    # Set session cookie
    set_session_cookie(response, sid, "session_id")

    # Set CSRF token cookie (NOT HttpOnly, so client can read it for headers)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # Client needs to read this for X-CSRF-Token header
        samesite="lax" if IS_PRODUCTION else "lax",
        secure=IS_PRODUCTION,
        max_age=SESSION_EXPIRY,
        path="/"
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
        # Still set cookie even when no active tasks
        response = JSONResponse(content={"active": False, "task": None, "tasks": []})
        response.set_cookie(
            key="session_id",
            value=sid,
            httponly=True,
            samesite="lax",
            secure=IS_PRODUCTION,
            max_age=SESSION_EXPIRY
        )
        return response

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
            elif task_type == "repair_womb":
                womb_id = task_data.get('womb_id', '?')
                label = f"Repairing Womb {womb_id}"
            
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
        old_active_tasks = state.active_tasks.copy() if state.active_tasks else {}
        state = check_and_complete_tasks(state)
        
        # Emit completion events for completed tasks
        for task_id in completed_tasks:
            old_task_data = old_active_tasks.get(task_id, {})
            task_type = old_task_data.get('type')
            
            if task_type == "gather_resource":
                resource = old_task_data.get('resource')
                if resource:
                    new_total = state.resources.get(resource, 0)
                    delta = old_task_data.get('pending_amount', 0)
                    emit_event(db, sid, "gather.complete", {
                        "resource": resource,
                        "delta": delta,
                        "new_total": new_total
                    })
                    emit_event(db, sid, "resource.delta", {
                        "resource": resource,
                        "delta": delta,
                        "new_total": new_total
                    })
            
            elif task_type == "grow_clone":
                completed_clone = old_task_data.get('completed_clone')
                if completed_clone:
                    emit_event(db, sid, "clone.grow.complete", {
                        "clone": completed_clone
                    }, entity_id=completed_clone.get("id"))
        
        save_game_state(db, sid, state)

    # Return primary task (first one) for backward compatibility, plus all tasks
    primary_task = tasks_info[0] if tasks_info else None
    
    response = JSONResponse(content={
        "active": len(tasks_info) > 0,
        "task": primary_task,  # Primary task for backward compatibility
        "tasks": tasks_info,   # All active tasks
        "completed": len(completed_tasks) > 0
    })
    # Always set session cookie to ensure persistence
    set_session_cookie(response, sid, "session_id")
    return response


@router.post("/state")
async def save_game_state_endpoint(
    state_data: Dict[str, Any],
    request: Request,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Save game state.
    Uses optimistic locking to prevent race conditions where frontend auto-save
    might overwrite newer backend state (e.g., after task completion).
    
    Rate limit: 30 requests/minute
    Max request size: 1MB
    """
    sid = get_session_id(session_id)
    enforce_rate_limit(sid, "save_state")

    # Check if this is a new session (no cookie provided)
    is_new_session = not session_id

    try:
        state = dict_to_game_state(state_data)
        state.last_saved_ts = time.time()
        # Use optimistic locking to prevent overwriting newer backend state
        # This protects against race conditions where frontend auto-save sends stale state
        try:
            save_game_state(db, sid, state, check_version=True)
        except RuntimeError as version_error:
            # Version conflict - likely frontend has stale state
            # Reload latest state from database and return it
            logger.warning(f"Version conflict for session {sid[:8]}...: {version_error}")
            latest_state = load_game_state(db, sid, create_if_missing=True)
            if latest_state:
                # Return latest state so frontend can refresh
                response = JSONResponse(content={
                    "status": "conflict",
                    "state": game_state_to_dict(latest_state),
                    "message": "Your game state was updated. Please refresh."
                })
            else:
                # Shouldn't happen, but handle gracefully
                response = JSONResponse(content={"status": "error", "message": str(version_error)})
            response.set_cookie(
                key="session_id",
                value=sid,
                httponly=True,
                samesite="lax",
                secure=IS_PRODUCTION,
                max_age=SESSION_EXPIRY
            )
            return response

        response = JSONResponse(content={"status": "saved"})
        # Always set cookie (even if not new session, ensures cookie is refreshed)
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

        # Emit gather.start event
        task_data = new_state.active_tasks[task_id]
        emit_event(db, sid, "gather.start", {
            "resource": resource,
            "duration": task_data.get("duration", 0)
        }, entity_id=task_id)

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
    sid = get_session_id(session_id, request)
    logger.info(f"🔨 POST /build-womb - Session: {sid[:8]}..., Cookie present: {session_id is not None}")
    enforce_rate_limit(sid, "build_womb")

    state = load_game_state(db, sid, create_if_missing=True)
    current_womb_count = len(state.wombs) if state.wombs else 0
    logger.info(f"📊 Before build_womb - Session: {sid[:8]}..., Wombs: {current_womb_count}, Assembler: {state.assembler_built}")
    
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
        
        new_womb_count = len(final_state.wombs) if final_state.wombs else 0
        logger.info(f"✅ build_womb saved - Session: {sid[:8]}..., Wombs: {new_womb_count}, Task: {task_id}, Assembler: {final_state.assembler_built}")

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

        # Emit clone.grow.start event
        task_data = final_state.active_tasks[task_id]
        emit_event(db, sid, "clone.grow.start", {
            "kind": kind,
            "clone": None,  # Clone not created yet
            "duration": task_data.get("duration", 0)
        }, entity_id=task_id)

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
    Run an expedition (Mining, Combat, or Exploration) with server-authoritative outcomes.
    Rate limit: 10 requests/minute

    Anti-cheat measures:
    - Server generates RNG seed from HMAC(session_id, expedition_id, timestamp)
    - Outcomes are signed with HMAC to prevent tampering
    - Anomaly detection flags suspicious behavior patterns
    """
    from core.anticheat import (
        generate_expedition_seed,
        generate_outcome_signature,
        check_and_flag_anomaly
    )

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
        # Generate unique expedition ID
        expedition_id = str(uuid.uuid4())
        start_ts = time.time()

        # Emit expedition.start event
        clone_id = state.applied_clone_id
        if clone_id:
            emit_event(db, sid, "expedition.start", {
                "kind": kind,
                "clone_id": clone_id,
                "duration": 0  # Expeditions complete immediately
            }, entity_id=expedition_id)

        # Run expedition with server-authoritative outcome
        new_state, message = run_expedition(state, kind)

        # Get clone that ran expedition
        clone_survived = new_state.clones.get(clone_id, None).alive if clone_id and clone_id in new_state.clones else True

        # Calculate XP gained and loot (extract from state changes)
        xp_before = state.clones.get(clone_id).xp.get(kind, 0) if clone_id and clone_id in state.clones else 0
        xp_after = new_state.clones.get(clone_id).xp.get(kind, 0) if clone_id and clone_id in new_state.clones else 0
        xp_gained = xp_after - xp_before

        # Calculate loot (resource diff)
        loot = {}
        for res in RESOURCE_TYPES:
            before = state.resources.get(res, 0)
            after = new_state.resources.get(res, 0)
            if after > before:
                loot[res] = after - before

        # Create outcome data
        outcome_data = {
            "result": "success" if clone_survived else "death",
            "clone_id": clone_id,
            "expedition_kind": kind,
            "loot": loot,
            "xp_gained": xp_gained,
            "survived": clone_survived
        }

        # Generate signature
        signature = generate_outcome_signature(sid, expedition_id, start_ts, outcome_data)

        # Store outcome in database
        # Fix: Explicitly cast timestamps to float for PostgreSQL compatibility
        end_ts = time.time()
        start_ts_float = float(start_ts)
        end_ts_float = float(end_ts)
        
        try:
            execute_query(db, """
                INSERT INTO expedition_outcomes
                (id, session_id, expedition_kind, clone_id, start_ts, end_ts, result, loot_json, xp_gained, survived, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                expedition_id,
                sid,
                kind,
                clone_id or "",
                start_ts_float,  # Explicitly float for PostgreSQL DOUBLE PRECISION
                end_ts_float,    # Explicitly float for PostgreSQL DOUBLE PRECISION
                outcome_data["result"],
                json.dumps(loot),
                xp_gained,
                1 if clone_survived else 0,
                signature
            ))
            db.commit()
        except Exception as db_error:
            # Critical: Rollback transaction on error to prevent "transaction aborted" cascade
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")
            logger.error(f"Database error inserting expedition outcome for session {sid[:8]}...: {db_error}")
            raise

        # Check for anomalies
        anomaly = check_and_flag_anomaly(sid, "expedition")
        if anomaly:
            # Store anomaly flag
            try:
                execute_query(db, """
                    INSERT INTO anomaly_flags (session_id, action_type, anomaly_description, action_rate)
                    VALUES (?, ?, ?, ?)
                """, (sid, "expedition", anomaly, 0.0))
                db.commit()
                logger.warning(f"🚩 Anomaly flagged for session {sid[:8]}...: {anomaly}")
            except Exception as db_error:
                try:
                    db.rollback()
                except Exception:
                    pass
                logger.error(f"Failed to store anomaly flag: {db_error}")
                # Don't fail expedition on anomaly flag error

        # Save state (with autocommit, each statement commits automatically)
        save_game_state(db, sid, new_state)
        
        # Emit expedition.result event
        clone_xp = {}
        if clone_id and clone_id in new_state.clones:
            clone_xp = new_state.clones[clone_id].xp
        
        emit_event(db, sid, "expedition.result", {
            "kind": kind,
            "clone_id": clone_id or "",
            "clone_xp": clone_xp,
            "loot": loot,
            "message": message,
            "success": clone_survived,
            "death": not clone_survived
        }, entity_id=expedition_id)

        response = JSONResponse(content={
            "state": game_state_to_dict(new_state),
            "message": message,
            "expedition_id": expedition_id,
            "signature": signature  # Return signature for client verification (optional)
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
        # Calculate soul changes before upload
        old_soul_xp = state.soul_xp
        old_soul_percent = state.soul_percent
        
        new_state, message = upload_clone(state, clone_id)
        save_game_state(db, sid, new_state)

        # Emit upload.complete event
        soul_xp_delta = new_state.soul_xp - old_soul_xp
        soul_percent_delta = new_state.soul_percent - old_soul_percent
        emit_event(db, sid, "upload.complete", {
            "clone_id": clone_id,
            "soul_xp_delta": soul_xp_delta,
            "soul_percent_delta": soul_percent_delta,
        }, entity_id=clone_id)

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


@router.post("/repair-womb")
async def repair_womb_endpoint(
    womb_id: int,
    request: Request,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Repair a womb (durability restoration with resource cost and timed task).
    Rate limit: 10 requests/minute
    """
    from game.wombs import calculate_repair_cost, calculate_repair_time, find_active_womb
    
    sid = get_session_id(session_id)
    enforce_rate_limit(sid, "repair_womb")
    
    state = load_game_state(db, sid, create_if_missing=True)
    
    if state is None:
        raise HTTPException(
            status_code=404,
            detail="Game state not found. Your session may have been lost during a backend restart. Please refresh the page."
        )
    
    # Find womb to repair
    target_womb = next((w for w in state.wombs if w.id == womb_id), None)
    if target_womb is None:
        raise HTTPException(status_code=400, detail=f"Womb {womb_id} not found.")
    
    if target_womb.durability >= target_womb.max_durability:
        raise HTTPException(status_code=400, detail="Womb is already at full durability.")
    
    # Check for active tasks (repair blocks on other tasks)
    if state.active_tasks:
        raise HTTPException(status_code=400, detail="A task is already in progress. Please wait.")
    
    try:
        # Calculate repair cost and time
        repair_cost = calculate_repair_cost(target_womb)
        repair_time = calculate_repair_time(state, target_womb)
        
        # Check if player can afford repair
        from core.game_logic import can_afford, format_resource_error
        if not can_afford(state.resources, repair_cost):
            raise RuntimeError(format_resource_error(state.resources, repair_cost, f"Repair Womb {womb_id}"))
        
        # Create new state
        new_state = state.copy()
        
        # Deduct repair cost
        from core.game_logic import spend
        spend(new_state.resources, repair_cost)
        
        # Start repair task
        final_state, task_id = start_task(
            new_state,
            "repair_womb",
            womb_id=womb_id,
            repair_amount=target_womb.max_durability - target_womb.durability
        )
        
        save_game_state(db, sid, final_state)
        
        response = JSONResponse(content={
            "state": game_state_to_dict(final_state),
            "message": f"Repairing Womb {womb_id}...",
            "cost": repair_cost,
            "repair_time": repair_time,
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
        logger.error(f"Error repairing womb for session {sid[:8]}...: {str(e)}")
        raise HTTPException(status_code=400, detail=error_msg)


@router.get("/events/feed")
async def get_events_feed(
    request: Request,
    after: Optional[float] = None,
    db: DatabaseConnection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Get events feed for live state sync (B3).
    Returns incremental events since timestamp with ETag support.
    
    Rate limit: None (this is a read-only endpoint, but could add if needed)
    """
    from fastapi.responses import Response
    import hashlib
    
    # Log that endpoint is being called (debugging 404 issue)
    logger.debug(f"Events feed endpoint called: after={after}, session_id={session_id[:8] if session_id else 'None'}...")
    
    sid = get_session_id(session_id)
    
    # Check session expiry
    if not check_session_expiry(db, sid):
        sid = str(uuid.uuid4())
    
    try:
        # Build query to get events since timestamp
        # Use database-agnostic timestamp comparison
        if after:
            # Convert Unix timestamp to datetime for database comparison
            from datetime import datetime
            after_dt = datetime.fromtimestamp(after)
            
            # Get events after this timestamp
            # Database adapter handles placeholder conversion, but we need to handle timestamp format
            # SQLite uses string comparison, PostgreSQL uses timestamp comparison
            from database import get_db_placeholder
            placeholder = get_db_placeholder()
            
            # For PostgreSQL, pass datetime object directly
            # For SQLite, convert to ISO string
            if placeholder == "%s":  # PostgreSQL
                after_param = after_dt
            else:  # SQLite
                after_param = after_dt.isoformat()
            
            cursor = execute_query(db, """
                SELECT id, event_type, event_subtype, payload_json, created_at
                FROM events
                WHERE session_id = ? AND created_at > ?
                ORDER BY created_at ASC
                LIMIT 100
            """, (sid, after_param))
        else:
            # Get last 50 events (initial load)
            cursor = execute_query(db, """
                SELECT id, event_type, event_subtype, payload_json, created_at
                FROM events
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 50
            """, (sid,))
        
        rows = cursor.fetchall()
        
        # Convert database events to frontend format
        events = []
        for row in rows:
            # Reconstruct event type from database fields
            event_type_db = row['event_type']
            event_subtype = row['event_subtype']
            
            if event_subtype:
                event_type = f"{event_type_db}.{event_subtype}"
            else:
                event_type = event_type_db
            
            # Parse payload
            try:
                payload = json.loads(row['payload_json']) if row['payload_json'] else {}
            except:
                payload = {}
            
            # Parse timestamp
            created_at = row['created_at']
            if isinstance(created_at, str):
                from datetime import datetime
                timestamp = datetime.fromisoformat(created_at).timestamp()
            else:
                timestamp = created_at.timestamp() if hasattr(created_at, 'timestamp') else time.time()
            
            events.append({
                "id": row['id'],
                "type": event_type,
                "timestamp": int(timestamp),
                "data": payload
            })
        
        # Generate ETag from events (hash of event IDs)
        if events:
            event_ids = "|".join(sorted([e["id"] for e in events]))
            etag = hashlib.md5(event_ids.encode()).hexdigest()
            etag_value = f'"{etag}"'
        else:
            etag_value = '"empty"'
        
        # Check If-None-Match header
        if_none_match = request.headers.get("If-None-Match")
        if if_none_match and if_none_match.strip('"') == etag_value.strip('"'):
            # No changes, return 304
            # Still set cookie even for 304 responses
            response = Response(status_code=304, headers={"ETag": etag_value})
            response.set_cookie(
                key="session_id",
                value=sid,
                httponly=True,
                samesite="lax",
                secure=IS_PRODUCTION,
                max_age=SESSION_EXPIRY
            )
            return response
        
        response = JSONResponse(content=events)
        response.headers["ETag"] = etag_value
        # Always set session cookie to ensure persistence
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
        logger.error(f"Error fetching events feed for session {sid[:8]}...: {e}", exc_info=True)
        # Don't break the game - return empty array
        # Log full exception for debugging 404 issue
        import traceback
        logger.error(f"Events feed exception traceback: {traceback.format_exc()}")
        response = JSONResponse(content=[])
        # Still set cookie even on error
        response.set_cookie(
            key="session_id",
            value=sid,
            httponly=True,
            samesite="lax",
            secure=IS_PRODUCTION,
            max_age=SESSION_EXPIRY
        )
        return response


@router.get("/limits/status")
async def get_limits_status(
    request: Request,
    session_id: Optional[str] = Cookie(None)
):
    """
    Get rate limit status for fuel bar gamification (B1).
    Returns remaining counts per endpoint and combined total.
    """
    sid = get_session_id(session_id)
    now = time.time()
    window_seconds = 60  # 1 minute window
    
    # Endpoints to include in fuel bar (action endpoints only)
    action_endpoints = {
        "gather_resource": RATE_LIMITS.get("gather_resource", 20),
        "grow_clone": RATE_LIMITS.get("grow_clone", 10),
        "run_expedition": RATE_LIMITS.get("run_expedition", 10),
        "upload_clone": RATE_LIMITS.get("upload_clone", 10),
    }
    
    # Calculate remaining counts per endpoint
    endpoint_status = {}
    combined_remaining = 0
    earliest_reset = now + window_seconds
    
    for endpoint_name, limit in action_endpoints.items():
        # Initialize if needed
        if sid not in _rate_limit_store:
            _rate_limit_store[sid] = {}
        if endpoint_name not in _rate_limit_store[sid]:
            _rate_limit_store[sid][endpoint_name] = []
        
        # Clean old entries
        timestamps = [
            t for t in _rate_limit_store[sid][endpoint_name]
            if now - t < window_seconds
        ]
        
        # Calculate remaining
        used = len(timestamps)
        remaining = max(0, limit - used)
        combined_remaining += remaining
        
        # Calculate reset time (when oldest request expires)
        if timestamps:
            oldest = min(timestamps)
            reset_at = oldest + window_seconds
            if reset_at < earliest_reset:
                earliest_reset = reset_at
        else:
            reset_at = now
        
        endpoint_status[f"/{endpoint_name.replace('_', '-')}"] = {
            "remaining": remaining,
            "reset_at": int(reset_at)
        }
    
    # Add combined status
    endpoint_status["combined"] = {
        "remaining": combined_remaining,
        "reset_at": int(earliest_reset)
    }
    
    response = JSONResponse(content={
        "window_seconds": window_seconds,
        "now": int(now),
        "endpoints": endpoint_status
    })
    # Always set session cookie to ensure persistence
    set_session_cookie(response, sid, "session_id")
    return response


@router.get("/time")
async def get_server_time():
    """
    Get server time for client synchronization.

    Used by frontend progress bars and timers to sync with server clock.
    Returns current server timestamp in seconds since epoch.
    """
    return JSONResponse(content={
        "server_time": time.time(),
        "timestamp": int(time.time())
    })


@router.get("/debug/upload_breakdown")
async def get_upload_breakdown(
    session_id: Optional[str] = Cookie(None)
):
    """
    Debug endpoint: Get detailed breakdown of upload formula calculation.

    Shows how SELF XP gain is calculated for uploaded clones:
    - Base XP from clone practices
    - Retention multiplier (0.6-0.9 based on soul level)
    - Final SELF XP gained

    Used by frontend tooltips to explain upload mechanics to players.
    """
    sid = get_session_id(session_id)

    # Get retain range for formula explanation
    retain_range = CONFIG["SOUL_XP_RETAIN_RANGE"]  # (0.6, 0.9)

    return JSONResponse(content={
        "formula_explanation": {
            "base_formula": "SELF XP Gain = Clone Total XP × Retention Multiplier",
            "retention_multiplier": f"Scales from {retain_range[0]} (level 0) to {retain_range[1]} (level 10+)",
            "total_xp": "Sum of MINING + COMBAT + EXPLORATION XP from expeditions",
            "retain_range": list(retain_range)
        },
        "example_calculation": {
            "clone_with_30_xp": {
                "total_xp": 30,
                "level_0_retention": retain_range[0],
                "level_0_gain": int(30 * retain_range[0]),
                "level_10_retention": retain_range[1],
                "level_10_gain": int(30 * retain_range[1])
            }
        }
    })
