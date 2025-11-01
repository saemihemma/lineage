"""Leaderboard API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List
import sqlite3
from datetime import datetime
import time

from backend.models import LeaderboardEntry, LeaderboardSubmission
from backend.database import get_db

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])

# Simple in-memory rate limiting (IP-based)
# In production, use Redis or a proper rate limiting library
_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 10  # max requests per window


def get_client_ip(request: Request) -> str:
    """Extract client IP address"""
    # Check for forwarded IP (from proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(ip: str) -> bool:
    """Check if IP is within rate limit"""
    now = time.time()
    
    # Clean old entries
    if ip in _rate_limit_store:
        _rate_limit_store[ip] = [
            t for t in _rate_limit_store[ip] 
            if now - t < RATE_LIMIT_WINDOW
        ]
    else:
        _rate_limit_store[ip] = []
    
    # Check limit
    if len(_rate_limit_store[ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    # Record request
    _rate_limit_store[ip].append(now)
    return True


@router.get("", response_model=List[dict])
async def get_leaderboard(
    limit: int = 100,
    offset: int = 0,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Retrieve leaderboard entries.
    
    Returns top SELFs sorted by soul_level (descending), then soul_xp (descending).
    """
    if limit > 1000:
        limit = 1000  # Cap at 1000
    if limit < 1:
        limit = 100
    if offset < 0:
        offset = 0
    
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM leaderboard
        ORDER BY soul_level DESC, soul_xp DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    rows = cursor.fetchall()
    entries = []
    for row in rows:
        try:
            entry = LeaderboardEntry.from_row(row)
            entries.append(entry.to_dict())
        except Exception as e:
            print(f"Error parsing leaderboard row: {e}")
            continue
    
    return entries


@router.post("/submit")
async def submit_to_leaderboard(
    submission: LeaderboardSubmission,
    request: Request,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Submit SELF stats to leaderboard.
    
    Rate limited: 10 requests per minute per IP.
    """
    # Validate submission
    is_valid, error_msg = submission.validate()
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Rate limiting
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before submitting again."
        )
    
    # Check if entry exists for this self_name
    cursor = db.cursor()
    cursor.execute("SELECT * FROM leaderboard WHERE self_name = ?", (submission.self_name,))
    existing = cursor.fetchone()
    
    now = datetime.utcnow()
    
    if existing:
        # Update existing entry if new stats are better
        entry = LeaderboardEntry.from_row(existing)
        should_update = (
            submission.soul_level > entry.soul_level or
            (submission.soul_level == entry.soul_level and submission.soul_xp > entry.soul_xp)
        )
        
        if should_update:
            cursor.execute("""
                UPDATE leaderboard
                SET soul_level = ?, soul_xp = ?, clones_uploaded = ?, 
                    total_expeditions = ?, updated_at = ?
                WHERE id = ?
            """, (
                submission.soul_level,
                submission.soul_xp,
                submission.clones_uploaded,
                submission.total_expeditions,
                now.isoformat(),
                entry.id
            ))
            db.commit()
            return {"status": "updated", "id": entry.id}
        else:
            return {"status": "skipped", "reason": "existing entry has equal or better stats"}
    else:
        # Insert new entry
        entry = submission.to_leaderboard_entry()
        cursor.execute("""
            INSERT INTO leaderboard (id, self_name, soul_level, soul_xp, 
                                   clones_uploaded, total_expeditions, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.self_name,
            entry.soul_level,
            entry.soul_xp,
            entry.clones_uploaded,
            entry.total_expeditions,
            entry.created_at.isoformat(),
            entry.updated_at.isoformat()
        ))
        db.commit()
        return {"status": "created", "id": entry.id}


@router.get("/stats")
async def get_leaderboard_stats(db: sqlite3.Connection = Depends(get_db)):
    """Get leaderboard statistics (total entries, etc.)"""
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM leaderboard")
    total_row = cursor.fetchone()
    total = total_row['total'] if total_row else 0
    
    cursor.execute("""
        SELECT MAX(soul_level) as max_level, MAX(soul_xp) as max_xp
        FROM leaderboard
    """)
    stats = cursor.fetchone()
    
    return {
        "total_entries": total,
        "max_soul_level": (stats['max_level'] or 0) if stats else 0,
        "max_soul_xp": (stats['max_xp'] or 0) if stats else 0
    }

