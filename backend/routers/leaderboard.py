"""Leaderboard API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List
from datetime import datetime
import time

from models import LeaderboardEntry, LeaderboardSubmission
from database import get_db, DatabaseConnection, execute_query

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
    offset: int = 0
):
    """
    Retrieve leaderboard entries.
    
    Returns top SELFs sorted by soul_level (descending), then soul_xp (descending).
    Returns empty array if database is unavailable.
    """
    if limit > 1000:
        limit = 1000  # Cap at 1000
    if limit < 1:
        limit = 100
    if offset < 0:
        offset = 0
    
    # Try to get DB connection (optional)
    try:
        db = get_db()
    except Exception as e:
        # Database unavailable - return empty leaderboard
        return []
    
    try:
        cursor = execute_query(db, """
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
    except Exception as e:
        # Database error - return empty leaderboard
        print(f"Database error fetching leaderboard: {e}")
        return []


@router.post("/submit")
async def submit_to_leaderboard(
    submission: LeaderboardSubmission,
    request: Request
):
    """
    Submit SELF stats to leaderboard.
    
    Rate limited: 10 requests per minute per IP.
    Returns error if database is unavailable (leaderboard is optional feature).
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
    
    # Try to get DB connection (optional)
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Leaderboard service unavailable (database not accessible). Leaderboard is optional."
        )
    
    try:
        # Check if entry exists for this self_name
        cursor = execute_query(db, "SELECT * FROM leaderboard WHERE self_name = ?", (submission.self_name,))
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
                execute_query(db, """
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
            execute_query(db, """
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Leaderboard service unavailable: {str(e)}"
        )


@router.get("/stats")
async def get_leaderboard_stats():
    """Get leaderboard statistics (total entries, etc.)
    
    Returns default values if database is unavailable.
    """
    try:
        db = get_db()
    except Exception as e:
        # Database unavailable - return default stats
        return {
            "total_entries": 0,
            "max_soul_level": 0,
            "max_soul_xp": 0
        }
    
    try:
        cursor = execute_query(db, "SELECT COUNT(*) as total FROM leaderboard")
        total_row = cursor.fetchone()
        total = total_row['total'] if total_row else 0
        
        cursor = execute_query(db, """
            SELECT MAX(soul_level) as max_level, MAX(soul_xp) as max_xp
            FROM leaderboard
        """)
        stats = cursor.fetchone()
        
        return {
            "total_entries": total,
            "max_soul_level": (stats['max_level'] or 0) if stats else 0,
            "max_soul_xp": (stats['max_xp'] or 0) if stats else 0
        }
    except Exception as e:
        # Database error - return default stats
        print(f"Database error fetching leaderboard stats: {e}")
        return {
            "total_entries": 0,
            "max_soul_level": 0,
            "max_soul_xp": 0
        }

