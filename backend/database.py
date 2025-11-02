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
        
        conn.commit()


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
        except ImportError:
            raise ImportError(
                "psycopg2-binary is required for PostgreSQL support. "
                "Install it with: pip install psycopg2-binary"
            )
        
        if self.conn is None:
            self.conn = psycopg2.connect(
                self.db_url,
                cursor_factory=RealDictCursor  # Returns dict-like rows similar to sqlite3.Row
            )
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
        
        conn.commit()


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
    
    This allows writing SQL queries with '?' placeholders (SQLite style) and automatically
    converts them to '%s' (PostgreSQL style) if needed.
    
    Args:
        conn: Database connection
        sql: SQL query with '?' placeholders
        params: Query parameters
    
    Returns:
        Cursor object
    """
    placeholder = get_db_placeholder()
    
    # Convert placeholders if needed (SQLite uses '?', PostgreSQL uses '%s')
    if placeholder == "%s" and "?" in sql:
        # Convert SQLite-style placeholders to PostgreSQL-style
        sql = sql.replace("?", "%s")
    
    cursor = conn.cursor()
    cursor.execute(sql, params)
    return cursor
