"""Database setup and connection for LINEAGE backend"""
import sqlite3
from pathlib import Path
from typing import Optional
import os


class Database:
    """Manages database connection and schema"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. If None, uses environment variable
                    or defaults to 'lineage.db' in backend directory.
        """
        if db_path is None:
            db_path = os.getenv("DATABASE_URL", "sqlite:///lineage.db")
            # Convert SQLite URL format to file path
            if db_path.startswith("sqlite:///"):
                db_path = db_path.replace("sqlite:///", "")
            elif db_path.startswith("sqlite://"):
                db_path = db_path.replace("sqlite://", "")
        
        # Ensure directory exists for the database file (needed for Railway volumes)
        db_file = Path(db_path)
        db_dir = db_file.parent
        if db_dir and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = str(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._init_schema()
    
    def connect(self) -> sqlite3.Connection:
        """Get database connection (creates if not exists)"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        return self.conn
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _init_schema(self):
        """Initialize database schema"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Leaderboard table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard (
                id TEXT PRIMARY KEY,
                self_name TEXT NOT NULL,
                soul_level INTEGER NOT NULL,
                soul_xp INTEGER NOT NULL,
                clones_uploaded INTEGER DEFAULT 0,
                total_expeditions INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on self_name for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_leaderboard_self_name 
            ON leaderboard(self_name)
        """)
        
        # Create index on soul_level for sorting
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_leaderboard_soul_level 
            ON leaderboard(soul_level DESC, soul_xp DESC)
        """)
        
        # Telemetry events table (optional, for analytics)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_events (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                event_type TEXT NOT NULL,
                data TEXT,  -- JSON string
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on session_id and timestamp
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_session 
            ON telemetry_events(session_id, timestamp)
        """)
        
        # Game states table (for web version - stores game state per session)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_states (
                session_id TEXT PRIMARY KEY,
                state_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on updated_at for cleanup queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_game_states_updated_at 
            ON game_states(updated_at)
        """)
        
        conn.commit()
    
    def __enter__(self):
        """Context manager entry"""
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Global database instance
_db_instance: Optional[Database] = None


def get_db() -> sqlite3.Connection:
    """Get database connection (dependency injection for FastAPI)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance.connect()

