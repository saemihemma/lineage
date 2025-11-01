"""Data models for LINEAGE backend API"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import json
import uuid


@dataclass
class LeaderboardEntry:
    """Leaderboard entry model"""
    id: str
    self_name: str
    soul_level: int
    soul_xp: int
    clones_uploaded: int
    total_expeditions: int
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_row(cls, row) -> 'LeaderboardEntry':
        """Create from database row"""
        # Handle both dict-like rows (sqlite3.Row) and regular dicts
        if hasattr(row, '__getitem__'):
            get_val = lambda key: row[key] if hasattr(row, 'keys') or isinstance(row, dict) else row.__getitem__(key)
        else:
            get_val = lambda key: getattr(row, key, None)
        
        created_at = get_val('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        updated_at = get_val('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        
        return cls(
            id=str(get_val('id')),
            self_name=str(get_val('self_name')),
            soul_level=int(get_val('soul_level')),
            soul_xp=int(get_val('soul_xp')),
            clones_uploaded=int(get_val('clones_uploaded') or 0),
            total_expeditions=int(get_val('total_expeditions') or 0),
            created_at=created_at,
            updated_at=updated_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            'id': self.id,
            'self_name': self.self_name,
            'soul_level': self.soul_level,
            'soul_xp': self.soul_xp,
            'clones_uploaded': self.clones_uploaded,
            'total_expeditions': self.total_expeditions,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class LeaderboardSubmission:
    """Leaderboard submission request model"""
    self_name: str
    soul_level: int
    soul_xp: int
    clones_uploaded: int = 0
    total_expeditions: int = 0
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate submission data"""
        if not self.self_name or not self.self_name.strip():
            return False, "self_name cannot be empty"
        
        if len(self.self_name) > 100:
            return False, "self_name too long (max 100 characters)"
        
        if self.soul_level < 0:
            return False, "soul_level must be non-negative"
        
        if self.soul_xp < 0:
            return False, "soul_xp must be non-negative"
        
        if self.clones_uploaded < 0:
            return False, "clones_uploaded must be non-negative"
        
        if self.total_expeditions < 0:
            return False, "total_expeditions must be non-negative"
        
        return True, None
    
    def to_leaderboard_entry(self) -> LeaderboardEntry:
        """Convert to LeaderboardEntry with generated ID"""
        now = datetime.utcnow()
        return LeaderboardEntry(
            id=str(uuid.uuid4()),
            self_name=self.self_name.strip(),
            soul_level=self.soul_level,
            soul_xp=self.soul_xp,
            clones_uploaded=self.clones_uploaded,
            total_expeditions=self.total_expeditions,
            created_at=now,
            updated_at=now
        )


@dataclass
class TelemetryEvent:
    """Telemetry event model"""
    id: str
    session_id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    
    @classmethod
    def create(cls, session_id: str, event_type: str, data: Dict[str, Any]) -> 'TelemetryEvent':
        """Create new telemetry event"""
        return cls(
            id=str(uuid.uuid4()),
            session_id=session_id,
            event_type=event_type,
            data=data,
            timestamp=datetime.utcnow()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'event_type': self.event_type,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        }

