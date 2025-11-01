"""Pytest configuration and fixtures for backend tests"""
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient

from backend.database import Database
from backend.main import app


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    # Create temporary file
    fd, temp_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Create database instance
    db = Database(temp_path)

    yield db

    # Cleanup
    db.close()
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def db_connection(temp_db):
    """Get database connection from temp database"""
    conn = temp_db.connect()
    yield conn
    # Connection will be closed by temp_db fixture


@pytest.fixture
def client(temp_db):
    """FastAPI test client with temporary database"""
    # Override get_db dependency
    from backend.database import get_db
    from backend.main import app

    def override_get_db():
        return temp_db.connect()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_leaderboard_entry():
    """Sample leaderboard entry data"""
    return {
        "self_name": "TestSELF",
        "soul_level": 5,
        "soul_xp": 1500,
        "clones_uploaded": 10,
        "total_expeditions": 25
    }


@pytest.fixture
def sample_telemetry_events():
    """Sample telemetry events data"""
    return [
        {
            "session_id": "test-session-1",
            "event_type": "game_start",
            "data": {"version": "1.0.0"}
        },
        {
            "session_id": "test-session-1",
            "event_type": "clone_created",
            "data": {"clone_type": "worker", "stats": {"strength": 5}}
        }
    ]
