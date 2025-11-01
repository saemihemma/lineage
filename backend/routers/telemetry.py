"""Telemetry API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Dict, Any
import sqlite3
import json
import time

from backend.models import TelemetryEvent
from backend.database import get_db

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

# Simple rate limiting for telemetry
_rate_limit_store: dict[str, list[float]] = {}
TELEMETRY_RATE_LIMIT_WINDOW = 60
TELEMETRY_RATE_LIMIT_MAX_REQUESTS = 50  # Higher limit for telemetry


def get_client_ip(request: Request) -> str:
    """Extract client IP address"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(ip: str) -> bool:
    """Check if IP is within rate limit"""
    now = time.time()
    
    if ip in _rate_limit_store:
        _rate_limit_store[ip] = [
            t for t in _rate_limit_store[ip] 
            if now - t < TELEMETRY_RATE_LIMIT_WINDOW
        ]
    else:
        _rate_limit_store[ip] = []
    
    if len(_rate_limit_store[ip]) >= TELEMETRY_RATE_LIMIT_MAX_REQUESTS:
        return False
    
    _rate_limit_store[ip].append(now)
    return True


@router.post("")
async def upload_telemetry(
    events: List[Dict[str, Any]],
    request: Request,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Upload telemetry events.
    
    Accepts a list of telemetry events. Each event should have:
    - session_id: string
    - event_type: string
    - data: dict (any JSON-serializable data)
    - timestamp: ISO format string (optional, defaults to now)
    """
    # Rate limiting
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before uploading again."
        )
    
    if not events:
        return {"status": "success", "count": 0}
    
    if len(events) > 100:
        raise HTTPException(
            status_code=400,
            detail="Too many events in one batch (max 100)"
        )
    
    cursor = db.cursor()
    inserted_count = 0
    
    for event_data in events:
        try:
            session_id = event_data.get("session_id", "")
            event_type = event_data.get("event_type", "unknown")
            data = event_data.get("data", {})
            timestamp = event_data.get("timestamp", None)
            
            if not event_type:
                continue
            
            # Create event
            event = TelemetryEvent.create(session_id, event_type, data)
            if timestamp:
                # Use provided timestamp (parse if string)
                if isinstance(timestamp, str):
                    from datetime import datetime
                    event.timestamp = datetime.fromisoformat(timestamp)
            
            # Insert into database
            cursor.execute("""
                INSERT INTO telemetry_events (id, session_id, event_type, data, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                event.id,
                event.session_id,
                event.event_type,
                json.dumps(event.data),
                event.timestamp.isoformat()
            ))
            inserted_count += 1
            
        except Exception as e:
            # Log error but continue processing other events
            print(f"Error processing telemetry event: {e}")
            continue
    
    db.commit()
    
    return {
        "status": "success",
        "count": inserted_count,
        "total_received": len(events)
    }


@router.get("/stats")
async def get_telemetry_stats(db: sqlite3.Connection = Depends(get_db)):
    """Get telemetry statistics"""
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM telemetry_events")
    total = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT event_type, COUNT(*) as count
        FROM telemetry_events
        GROUP BY event_type
        ORDER BY count DESC
        LIMIT 10
    """)
    top_events = [
        {"event_type": row['event_type'], "count": row['count']}
        for row in cursor.fetchall()
    ]
    
    return {
        "total_events": total,
        "top_event_types": top_events
    }

