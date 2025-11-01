"""
Game API endpoints - handles game actions and state management
"""
import json
import uuid
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Cookie, Request
from fastapi.responses import JSONResponse
import sqlite3

from backend.database import get_db
from game.state import GameState
from game.rules import (
    build_womb, grow_clone, apply_clone, run_expedition,
    upload_clone, gather_resource
)
from core.models import Clone
from core.config import CONFIG
from core.state_manager import get_latest_version

router = APIRouter(prefix="/api/game", tags=["game"])


def get_session_id(session_id: Optional[str] = Cookie(None)) -> str:
    """Get or create session ID from cookie"""
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


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
            traits=c_data.get("traits", []),
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
    return dict_to_game_state(data)


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
    
    response = JSONResponse(content=game_state_to_dict(state))
    response.set_cookie(key="session_id", value=sid, httponly=True, samesite="lax")
    return response


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
    """Gather a resource"""
    sid = get_session_id(session_id)
    state = load_game_state(db, sid)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Game state not found")
    
    try:
        new_state, amount, message = gather_resource(state, resource)
        save_game_state(db, sid, new_state)
        
        response = JSONResponse(content={
            "state": game_state_to_dict(new_state),
            "message": message,
            "amount": amount
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
    """Build the Womb (assembler)"""
    sid = get_session_id(session_id)
    state = load_game_state(db, sid)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Game state not found")
    
    try:
        new_state, message = build_womb(state)
        save_game_state(db, sid, new_state)
        
        response = JSONResponse(content={
            "state": game_state_to_dict(new_state),
            "message": message
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
    """Grow a new clone"""
    sid = get_session_id(session_id)
    state = load_game_state(db, sid)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Game state not found")
    
    try:
        new_state, clone, soul_split, message = grow_clone(state, kind)
        save_game_state(db, sid, new_state)
        
        response = JSONResponse(content={
            "state": game_state_to_dict(new_state),
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
            "message": message
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

