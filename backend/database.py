"""Database setup and connection for LINEAGE backend

Supports both SQLite and PostgreSQL databases.
Automatically detects database type from DATABASE_URL environment variable.
"""
import os
from pathlib import Path
from typing import Optional, Union, Any, Protocol
from abc import ABC, abstractmethod


# Database abstraction protocol
class DatabaseConnection(Protocol):
    """Protocol for database connections that work with both SQLite and PostgreSQL"""
    def cursor(self) -> Any:
        """Get a cursor"""
        ...
    def commit(self) -> None:
        """Commit transaction"""
        ...
    def close(self) -> None:
        """Close connection"""
        ...


class DatabaseAdapter(ABC):
    """Abstract base class for database adapters"""
    
    @abstractmethod
    def connect(self) -> DatabaseConnection:
        """Get database connection"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close database connection"""
        pass
    
    @abstractmethod
    def get_placeholder(self) -> str:
        """Get parameter placeholder style ('?' for SQLite, '%s' for PostgreSQL)"""
        pass
    
    @abstractmethod
    def init_schema(self, conn: DatabaseConnection) -> None:
        """Initialize database schema"""
        pass


class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[Any] = None
        
        # Ensure directory exists for the database file (needed for Railway volumes)
        db_file = Path(db_path)
        db_dir = db_file.parent
        if db_dir and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
    
    def connect(self) -> DatabaseConnection:
        """Get SQLite connection"""
        import sqlite3
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Enable dict-like access
            self.init_schema(self.conn)
        return self.conn
    
    def close(self) -> None:
        """Close SQLite connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_placeholder(self) -> str:
        """SQLite uses '?' placeholders"""
        return "?"
    
    def init_schema(self, conn: DatabaseConnection) -> None:
        """Initialize SQLite schema"""
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
        
        # Telemetry events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_events (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                event_type TEXT NOT NULL,
                data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on session_id and timestamp
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_session 
            ON telemetry_events(session_id, timestamp)
        """)
        
        # Game states table
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

        # Expedition outcomes table (anti-cheat)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expedition_outcomes (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                expedition_kind TEXT NOT NULL,
                clone_id TEXT NOT NULL,
                start_ts REAL NOT NULL,
                end_ts REAL NOT NULL,
                result TEXT NOT NULL,
                loot_json TEXT,
                xp_gained INTEGER DEFAULT 0,
                survived BOOLEAN DEFAULT 1,
                signature TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index on session_id for queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expedition_outcomes_session
            ON expedition_outcomes(session_id, created_at DESC)
        """)

        # Anomaly flags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anomaly_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                anomaly_description TEXT NOT NULL,
                action_rate REAL,
                flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index on session_id for admin queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_anomaly_flags_session
            ON anomaly_flags(session_id, flagged_at DESC)
        """)

        # Enhanced events table (A2: Event Logging & HUD)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_subtype TEXT,
                entity_id TEXT,
                payload_json TEXT,
                privacy_level TEXT DEFAULT 'private',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create composite index on session_id and created_at for feed queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_session_created
            ON events(session_id, created_at DESC)
        """)

        # Create index on event_type for filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type
            ON events(event_type, created_at DESC)
        """)

        # Create index on created_at for cursor-based pagination
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_created_cursor
            ON events(created_at DESC, id)
        """)

        # Schema initialization doesn't need explicit commit with autocommit=True
        # But we'll keep commit for safety
        try:
            conn.commit()
        except Exception:
            pass


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL database adapter"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn: Optional[Any] = None
    
    def connect(self) -> DatabaseConnection:
        """Get PostgreSQL connection"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            from psycopg2.extensions import STATUS_READY, STATUS_IN_TRANSACTION
        except ImportError:
            raise ImportError(
                "psycopg2-binary is required for PostgreSQL support. "
                "Install it with: pip install psycopg2-binary"
            )
        
        # Always ensure autocommit is enabled and connection is healthy
        if self.conn is not None:
            # Check if connection is in a bad state
            try:
                status = self.conn.status
                # If in transaction (shouldn't happen with autocommit, but check anyway)
                # or connection is closed (status < 0), recreate it
                if status < 0 or (status == STATUS_IN_TRANSACTION):
                    # Connection is bad or in a transaction state, close and recreate
                    try:
                        self.conn.close()
                    except Exception:
                        pass
                    self.conn = None
                elif status == STATUS_READY:
                    # Connection is healthy, but ensure autocommit is still enabled
                    # (it might have been disabled or connection was reused from before fix)
                    if not self.conn.autocommit:
                        self.conn.autocommit = True
            except Exception:
                # Connection is in error state, close and recreate
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None
        
        if self.conn is None:
            self.conn = psycopg2.connect(
                self.db_url,
                cursor_factory=RealDictCursor  # Returns dict-like rows similar to sqlite3.Row
            )
            # Enable autocommit mode - each query is its own transaction
            # This prevents "transaction aborted" errors when one query fails
            # For multi-query operations that need transactions, we'll use explicit BEGIN/COMMIT
            self.conn.autocommit = True
            self.init_schema(self.conn)
        
        return self.conn
    
    def close(self) -> None:
        """Close PostgreSQL connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_placeholder(self) -> str:
        """PostgreSQL uses '%s' placeholders"""
        return "%s"
    
    def init_schema(self, conn: DatabaseConnection) -> None:
        """Initialize PostgreSQL schema"""
        cursor = conn.cursor()
        
        # Leaderboard table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard (
                id VARCHAR(255) PRIMARY KEY,
                self_name VARCHAR(255) NOT NULL,
                soul_level INTEGER NOT NULL,
                soul_xp INTEGER NOT NULL,
                clones_uploaded INTEGER DEFAULT 0,
                total_expeditions INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on self_name
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_leaderboard_self_name 
            ON leaderboard(self_name)
        """)
        
        # Create index on soul_level
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_leaderboard_soul_level 
            ON leaderboard(soul_level DESC, soul_xp DESC)
        """)
        
        # Telemetry events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_events (
                id VARCHAR(255) PRIMARY KEY,
                session_id VARCHAR(255),
                event_type VARCHAR(255) NOT NULL,
                data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on session_id and timestamp
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_session 
            ON telemetry_events(session_id, timestamp)
        """)
        
        # Game states table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_states (
                session_id VARCHAR(255) PRIMARY KEY,
                state_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on updated_at
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_game_states_updated_at
            ON game_states(updated_at)
        """)

        # Expedition outcomes table (anti-cheat)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expedition_outcomes (
                id VARCHAR(255) PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                expedition_kind VARCHAR(50) NOT NULL,
                clone_id VARCHAR(255) NOT NULL,
                start_ts DOUBLE PRECISION NOT NULL,
                end_ts DOUBLE PRECISION NOT NULL,
                result VARCHAR(50) NOT NULL,
                loot_json TEXT,
                xp_gained INTEGER DEFAULT 0,
                survived BOOLEAN DEFAULT TRUE,
                signature VARCHAR(64) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index on session_id for queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expedition_outcomes_session
            ON expedition_outcomes(session_id, created_at DESC)
        """)

        # Anomaly flags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anomaly_flags (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                action_type VARCHAR(50) NOT NULL,
                anomaly_description TEXT NOT NULL,
                action_rate DOUBLE PRECISION,
                flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index on session_id for admin queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_anomaly_flags_session
            ON anomaly_flags(session_id, flagged_at DESC)
        """)

        # Enhanced events table (A2: Event Logging & HUD)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id VARCHAR(255) PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                event_subtype VARCHAR(50),
                entity_id VARCHAR(255),
                payload_json TEXT,
                privacy_level VARCHAR(20) DEFAULT 'private',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create composite index on session_id and created_at for feed queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_session_created
            ON events(session_id, created_at DESC)
        """)

        # Create index on event_type for filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type
            ON events(event_type, created_at DESC)
        """)

        # Create index on created_at for cursor-based pagination
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_created_cursor
            ON events(created_at DESC, id)
        """)

        # Schema initialization doesn't need explicit commit with autocommit=True
        # But we'll keep commit for safety
        try:
            conn.commit()
        except Exception:
            pass


class Database:
    """Manages database connection and schema
    
    Automatically detects database type from DATABASE_URL:
    - SQLite: sqlite:///path/to/db.db or sqlite://path/to/db.db
    - PostgreSQL: postgresql://user:pass@host/dbname or postgres://...
    """
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_url: Database connection string. If None, uses DATABASE_URL environment variable
                   or defaults to SQLite 'sqlite:///lineage.db'
        """
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "sqlite:///lineage.db")
        
        # Detect database type and create appropriate adapter
        if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
            self.adapter: DatabaseAdapter = PostgreSQLAdapter(db_url)
            self.db_type = "postgresql"
            # For PostgreSQL, db_path is not applicable
            self.db_path: Optional[str] = None
        else:
            # SQLite
            # Convert SQLite URL format to file path
            if db_url.startswith("sqlite:///"):
                db_path = db_url.replace("sqlite:///", "")
            elif db_url.startswith("sqlite://"):
                db_path = db_url.replace("sqlite://", "")
            else:
                db_path = db_url  # Assume it's already a path
            
            self.adapter = SQLiteAdapter(db_path)
            self.db_type = "sqlite"
            self.db_path = db_path  # Store for backward compatibility with tests
        
        # Connection cache (for backward compatibility)
        self.conn: Optional[DatabaseConnection] = None
    
    def connect(self) -> DatabaseConnection:
        """Get database connection"""
        if self.conn is None:
            self.conn = self.adapter.connect()
        return self.conn
    
    def close(self) -> None:
        """Close database connection"""
        self.adapter.close()
        self.conn = None  # Clear cache for backward compatibility
    
    def get_placeholder(self) -> str:
        """Get parameter placeholder style"""
        return self.adapter.get_placeholder()
    
    def __enter__(self):
        """Context manager entry"""
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Global database instance
_db_instance: Optional[Database] = None


def get_db() -> DatabaseConnection:
    """Get database connection (dependency injection for FastAPI)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance.connect()


def get_db_placeholder() -> str:
    """Get the parameter placeholder style for the current database"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance.get_placeholder()


def execute_query(conn: DatabaseConnection, sql: str, params: tuple = ()) -> Any:
    """
    Execute a SQL query with parameter placeholders converted for the current database.
    Automatically handles PostgreSQL aborted transactions by rolling back and retrying.
    
    This allows writing SQL queries with '?' placeholders (SQLite style) and automatically
    converts them to '%s' (PostgreSQL style) if needed.
    
    Args:
        conn: Database connection
        sql: SQL query with '?' placeholders
        params: Query parameters
    
    Returns:
        Cursor object
    """
    import logging
    logger = logging.getLogger(__name__)
    
    placeholder = get_db_placeholder()
    
    # Convert placeholders if needed (SQLite uses '?', PostgreSQL uses '%s')
    if placeholder == "%s" and "?" in sql:
        # Convert SQLite-style placeholders to PostgreSQL-style
        sql = sql.replace("?", "%s")
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor
    except Exception as e:
        # Check if this is a PostgreSQL "transaction aborted" error
        error_str = str(e).lower()
        error_type = str(type(e).__name__)
        
        if ("current transaction is aborted" in error_str or 
            "infailedsqltransaction" in error_type.lower() or
            "transaction" in error_str and "aborted" in error_str):
            # Rollback the aborted transaction
            try:
                conn.rollback()
                logger.warning(f"Rolled back aborted transaction before retry: {sql[:50]}...")
                # Retry the query after rollback
                cursor = conn.cursor()
                cursor.execute(sql, params)
                return cursor
            except Exception as retry_error:
                logger.error(f"Failed to retry query after rollback: {retry_error}")
                raise
        else:
            # Not a transaction error, re-raise
            raise
