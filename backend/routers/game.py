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
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Cookie, Request
from fastapi.responses import JSONResponse
import sqlite3

from database import get_db
from game.state import GameState
from game.rules import (
    build_womb, grow_clone, apply_clone, run_expedition,
    upload_clone, gather_resource
)
from core.models import Clone
from core.config import CONFIG
from core.state_manager import get_latest_version
from core.game_logic import perk_constructive_craft_time_mult

router = APIRouter(prefix="/api/game", tags=["game"])


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
            completed_tasks.append((task_id, task_type, task_data))
            del new_state.active_tasks[task_id]
    
    # Auto-complete tasks (currently just remove them, actual completion happens immediately on start)
    # For gather/build/grow, the action happens immediately, timer is just UI feedback
    # But we mark them as complete here
    
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
    """
    new_state = state.copy()
    
    # Check if already busy
    if new_state.active_tasks:
        raise RuntimeError("A task is already in progress. Please wait.")
    
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
        "assembler_built": state.assembler_built,
        "resources": state.resources,
        "applied_clone_id": state.applied_clone_id,
        "practices_xp": state.practices_xp,
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
                "uploaded": c.uploaded
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
            uploaded=c_data.get("uploaded", False)
        )
    
    return state


def load_game_state(db: sqlite3.Connection, session_id: str) -> Optional[GameState]:
    """Load game state from database"""
    cursor = db.cursor()
    cursor.execute(
        "SELECT state_data FROM game_states WHERE session_id = ?",
        (session_id,)
    )
    row = cursor.fetchone()
    if row is None:
        return None
    
    data = json.loads(row[0])
    state = dict_to_game_state(data)
    
    # Check and complete any finished tasks
    state = check_and_complete_tasks(state)
    if state.active_tasks != data.get("active_tasks", {}):
        # Tasks were completed, save updated state
        save_game_state(db, session_id, state)
    
    return state


def save_game_state(db: sqlite3.Connection, session_id: str, state: GameState):
    """Save game state to database"""
    cursor = db.cursor()
    state_dict = game_state_to_dict(state)
    state_json = json.dumps(state_dict)
    
    cursor.execute("""
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
    db: sqlite3.Connection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """
    Get current game state.
    Creates new state if none exists.
    """
    sid = get_session_id(session_id)
    
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
    response.set_cookie(key="session_id", value=sid, httponly=True, samesite="lax")
    return response


@router.get("/tasks/status")
async def get_task_status(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """Get current task status (for polling)"""
    sid = get_session_id(session_id)
    state = load_game_state(db, sid)
    
    if state is None or not state.active_tasks:
        return JSONResponse(content={"active": False, "task": None})
    
    # Get first (and should be only) active task
    task_id = list(state.active_tasks.keys())[0]
    task_data = state.active_tasks[task_id]
    
    current_time = time.time()
    start_time = task_data.get('start_time', 0)
    duration = task_data.get('duration', 0)
    elapsed = current_time - start_time
    remaining = max(0, duration - elapsed)
    progress = min(100, int((elapsed / duration * 100)) if duration > 0 else 0)
    
    # Check if complete
    is_complete = current_time >= start_time + duration
    
    if is_complete:
        # Auto-complete
        state = check_and_complete_tasks(state)
        save_game_state(db, sid, state)
        return JSONResponse(content={"active": False, "task": None, "completed": True})
    
    return JSONResponse(content={
        "active": True,
        "task": {
            "id": task_id,
            "type": task_data.get('type'),
            "progress": progress,
            "elapsed": int(elapsed),
            "remaining": int(remaining),
            "duration": duration,
            "label": task_data.get('type', 'task').replace('_', ' ').title()
        }
    })


@router.post("/state")
async def save_game_state_endpoint(
    state_data: Dict[str, Any],
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """Save game state"""
    sid = get_session_id(session_id)
    
    try:
        state = dict_to_game_state(state_data)
        state.last_saved_ts = time.time()
        save_game_state(db, sid, state)
        
        response = JSONResponse(content={"status": "saved"})
        response.set_cookie(key="session_id", value=sid, httponly=True, samesite="lax")
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid game state: {str(e)}")


@router.post("/gather-resource")
async def gather_resource_endpoint(
    resource: str,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """Gather a resource (starts timer, completes immediately but UI waits)"""
    sid = get_session_id(session_id)
    state = load_game_state(db, sid)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Game state not found")
    
    # Check for active tasks
    if state.active_tasks:
        raise HTTPException(status_code=400, detail="A task is already in progress")
    
    try:
        # Start task timer
        new_state, task_id = start_task(state, "gather_resource", resource=resource)
        
        # Actually perform the gather (happens immediately)
        final_state, amount, message = gather_resource(new_state, resource)
        
        # Remove task since it's instant (just for consistency, we could keep it for UI feedback)
        # Actually, let's keep it so frontend can show progress
        save_game_state(db, sid, final_state)
        
        response = JSONResponse(content={
            "state": game_state_to_dict(final_state),
            "message": message,
            "amount": amount,
            "task_id": task_id
        })
        response.set_cookie(key="session_id", value=sid, httponly=True, samesite="lax")
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/build-womb")
async def build_womb_endpoint(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """Build the Womb (assembler) - starts timer"""
    sid = get_session_id(session_id)
    state = load_game_state(db, sid)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Game state not found")
    
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
        response.set_cookie(key="session_id", value=sid, httponly=True, samesite="lax")
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/grow-clone")
async def grow_clone_endpoint(
    kind: str,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """Grow a new clone - starts timer"""
    sid = get_session_id(session_id)
    state = load_game_state(db, sid)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Game state not found")
    
    # Check for active tasks
    if state.active_tasks:
        raise HTTPException(status_code=400, detail="A task is already in progress")
    
    try:
        # Actually grow (happens immediately)
        new_state, clone, soul_split, message = grow_clone(state, kind)
        
        # Start timer task
        final_state, task_id = start_task(new_state, "grow_clone", clone_kind=kind)
        
        save_game_state(db, sid, final_state)
        
        response = JSONResponse(content={
            "state": game_state_to_dict(final_state),
            "clone": {
                "id": clone.id,
                "kind": clone.kind,
                "traits": clone.traits,
                "xp": clone.xp,
                "survived_runs": clone.survived_runs,
                "alive": clone.alive,
                "uploaded": clone.uploaded
            },
            "soul_split": soul_split,
            "message": message,
            "task_id": task_id
        })
        response.set_cookie(key="session_id", value=sid, httponly=True, samesite="lax")
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/apply-clone")
async def apply_clone_endpoint(
    clone_id: str,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """Apply a clone (activate it)"""
    sid = get_session_id(session_id)
    state = load_game_state(db, sid)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Game state not found")
    
    try:
        new_state, message = apply_clone(state, clone_id)
        save_game_state(db, sid, new_state)
        
        response = JSONResponse(content={
            "state": game_state_to_dict(new_state),
            "message": message
        })
        response.set_cookie(key="session_id", value=sid, httponly=True, samesite="lax")
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/run-expedition")
async def run_expedition_endpoint(
    kind: str,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """Run an expedition (Mining, Combat, or Exploration)"""
    sid = get_session_id(session_id)
    state = load_game_state(db, sid)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Game state not found")
    
    try:
        new_state, message = run_expedition(state, kind)
        save_game_state(db, sid, new_state)
        
        response = JSONResponse(content={
            "state": game_state_to_dict(new_state),
            "message": message
        })
        response.set_cookie(key="session_id", value=sid, httponly=True, samesite="lax")
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload-clone")
async def upload_clone_endpoint(
    clone_id: str,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    session_id: Optional[str] = Cookie(None)
):
    """Upload a clone to SELF"""
    sid = get_session_id(session_id)
    state = load_game_state(db, sid)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Game state not found")
    
    try:
        new_state, message = upload_clone(state, clone_id)
        save_game_state(db, sid, new_state)
        
        response = JSONResponse(content={
            "state": game_state_to_dict(new_state),
            "message": message
        })
        response.set_cookie(key="session_id", value=sid, httponly=True, samesite="lax")
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
