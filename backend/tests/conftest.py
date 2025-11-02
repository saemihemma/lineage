"""Pytest configuration and fixtures for backend tests"""
import pytest
import sqlite3
import tempfile
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from database import Database
from main import app


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
    from database import get_db
    from main import app

    def override_get_db():
        return temp_db.connect()

    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)
    yield test_client
    test_client.close()

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


@pytest.fixture
def sample_game_state():
    """Sample game state data"""
    from game.state import GameState
    from core.config import CONFIG

    state = GameState()
    state.version = 1
    state.rng_seed = 12345
    state.soul_percent = 100.0
    state.soul_xp = 0
    state.assembler_built = False
    state.resources = {
        "Tritanium": 60,
        "Metal Ore": 40,
        "Biomass": 8,
        "Synthetic": 8,
        "Organic": 8,
        "Shilajit": 0
    }
    state.applied_clone_id = ""
    state.practices_xp = {
        "Kinetic": 0,
        "Cognitive": 0,
        "Constructive": 0
    }
    state.active_tasks = {}
    state.ui_layout = {}

    return state


@pytest.fixture
def sample_game_state_with_womb(sample_game_state):
    """Sample game state with womb already built"""
    state = sample_game_state.copy()
    state.assembler_built = True
    state.resources["Tritanium"] -= 30
    state.resources["Metal Ore"] -= 20
    state.resources["Biomass"] -= 5
    state.practices_xp["Constructive"] = 10
    return state


@pytest.fixture
def sample_clone_data():
    """Sample clone data"""
    from core.models import Clone

    return Clone(
        id="test-clone-1",
        kind="BASIC",
        traits={
            "PWC": 5,
            "SSC": 6,
            "MGC": 4,
            "DLT": 7,
            "ENF": 5,
            "ELK": 3,
            "FRK": 4
        },
        xp={"MINING": 0, "COMBAT": 0, "EXPLORATION": 0},
        survived_runs=0,
        alive=True,
        uploaded=False
    )


@pytest.fixture
def game_client_with_session(client):
    """Test client with initialized game session"""
    # Create initial game state
    response = client.get("/api/game/state")
    session_id = response.cookies.get("session_id")

    # Return client and session_id for convenience
    class GameClient:
        def __init__(self, client, session_id):
            self.client = client
            self.session_id = session_id

        def get(self, url, **kwargs):
            if 'cookies' not in kwargs:
                kwargs['cookies'] = {"session_id": self.session_id}
            return self.client.get(url, **kwargs)

        def post(self, url, **kwargs):
            if 'cookies' not in kwargs:
                kwargs['cookies'] = {"session_id": self.session_id}
            return self.client.post(url, **kwargs)

    return GameClient(client, session_id)


@pytest.fixture
def game_state_with_clone(client):
    """Game state with womb built and one clone created"""
    response = client.get("/api/game/state")
    session_id = response.cookies.get("session_id")

    # Build womb
    client.post("/api/game/build-womb", cookies={"session_id": session_id})

    # Wait briefly for task
    import time
    time.sleep(0.1)

    # Grow clone
    response = client.post(
        "/api/game/grow-clone?kind=BASIC",
        cookies={"session_id": session_id}
    )

    clone_id = response.json()["clone"]["id"]

    return {
        "client": client,
        "session_id": session_id,
        "clone_id": clone_id
    }
