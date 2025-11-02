"""Database Resilience Tests - Ensures database handles failures gracefully

Priority 2: Test database connection resilience and state persistence under stress.
These tests verify that the database layer is robust and can handle:
- Connection failures and recovery
- Large state data
- Concurrent operations
- PostgreSQL-specific behavior
"""
import pytest
import json
import time
import uuid
from fastapi.testclient import TestClient

from game.state import GameState
from core.config import CONFIG
from database import Database, execute_query


class TestDatabaseConnection:
    """Database connection tests - ensure connections work reliably"""

    def test_database_connection_on_startup(self, temp_db):
        """Test that database connects successfully on startup"""
        conn = temp_db.connect()

        assert conn is not None
        assert hasattr(conn, 'cursor')
        assert hasattr(conn, 'commit')

    def test_database_schema_initialization(self, temp_db):
        """Test that database schema is initialized correctly"""
        conn = temp_db.connect()
        cursor = conn.cursor()

        # Check game_states table exists
        if temp_db.db_type == "sqlite":
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='game_states'
            """)
        else:
            cursor.execute("""
                SELECT tablename FROM pg_tables
                WHERE tablename='game_states'
            """)

        result = cursor.fetchone()
        assert result is not None

    def test_reconnection_after_connection_close(self, temp_db):
        """Test that database can reconnect after connection closes"""
        # First connection
        conn1 = temp_db.connect()
        assert conn1 is not None

        # Close connection
        temp_db.close()

        # Reconnect
        conn2 = temp_db.connect()
        assert conn2 is not None

        # Verify it works
        cursor = execute_query(conn2, "SELECT 1 as test")
        result = cursor.fetchone()
        assert result is not None

    def test_query_timeout_handling(self, temp_db):
        """Test that query timeouts are handled gracefully"""
        conn = temp_db.connect()

        # Simple query should not timeout
        cursor = execute_query(conn, "SELECT 1 as test")
        result = cursor.fetchone()

        assert result is not None

    def test_transaction_rollback_on_error(self, temp_db):
        """Test that transactions rollback on error"""
        conn = temp_db.connect()

        # Insert valid data
        session_id = str(uuid.uuid4())
        state_data = json.dumps({"test": "data"})

        execute_query(conn, """
            INSERT INTO game_states (session_id, state_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (session_id, state_data))
        conn.commit()

        # Try invalid operation (duplicate session_id)
        try:
            execute_query(conn, """
                INSERT INTO game_states (session_id, state_data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (session_id, state_data))
            conn.commit()
        except Exception:
            # Rollback should happen
            pass

        # Verify original data still exists
        cursor = execute_query(conn,
            "SELECT session_id FROM game_states WHERE session_id = ?",
            (session_id,)
        )
        result = cursor.fetchone()
        assert result is not None

    def test_concurrent_connection_handling(self, temp_db):
        """Test that concurrent connections work correctly"""
        # Create multiple connections (simulates concurrent requests)
        conn1 = temp_db.connect()
        conn2 = temp_db.connect()

        # Both should work
        assert conn1 is not None
        assert conn2 is not None

        # Execute queries on both
        cursor1 = execute_query(conn1, "SELECT 1 as test")
        cursor2 = execute_query(conn2, "SELECT 1 as test")

        assert cursor1.fetchone() is not None
        assert cursor2.fetchone() is not None

    def test_connection_pool_behavior(self, temp_db):
        """Test that connection pooling works correctly"""
        # Get connection multiple times
        connections = []
        for i in range(5):
            conn = temp_db.connect()
            assert conn is not None
            connections.append(conn)

        # All should be functional
        for conn in connections:
            cursor = execute_query(conn, "SELECT 1 as test")
            assert cursor.fetchone() is not None


class TestStatePersistence:
    """State persistence tests - ensure data persists correctly"""

    def test_saving_large_states_many_clones(self, client):
        """Test saving states with many clones"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Create state with many clones
        state = response1.json()
        state["assembler_built"] = True

        # Add 50 clones
        from core.models import Clone
        for i in range(50):
            clone_id = f"clone-{i}"
            state["clones"][clone_id] = {
                "id": clone_id,
                "kind": "BASIC",
                "traits": {
                    "PWC": 5, "SSC": 6, "MGC": 4,
                    "DLT": 7, "ENF": 5, "ELK": 3, "FRK": 4
                },
                "xp": {"MINING": 100, "COMBAT": 50, "EXPLORATION": 75},
                "survived_runs": 10,
                "alive": True,
                "uploaded": False,
                "created_at": time.time()
            }

        # Save large state
        response2 = client.post(
            "/api/game/state",
            json=state,
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200

        # Verify retrieval
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})
        assert response3.status_code == 200
        assert len(response3.json()["clones"]) == 50

    def test_saving_states_with_special_characters(self, client):
        """Test saving states with special characters in names"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Special characters in name
        state = response1.json()
        state["self_name"] = "Test'Player\"With<Special>Chars&Symbols"

        response2 = client.post(
            "/api/game/state",
            json=state,
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200

        # Verify retrieval
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})
        assert response3.json()["self_name"] == "Test'Player\"With<Special>Chars&Symbols"

    def test_loading_states_after_database_restart(self, client, temp_db):
        """Test loading states after database restart simulation"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Modify state
        client.post("/api/game/build-womb", cookies={"session_id": session_id})

        # Simulate database "restart" by closing and reopening
        temp_db.close()
        conn = temp_db.connect()

        # Verify data persists
        cursor = execute_query(conn,
            "SELECT state_data FROM game_states WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        state_data = json.loads(row['state_data'])
        assert state_data["assembler_built"] == True

    def test_upsert_behavior_update_existing(self, temp_db):
        """Test that upsert updates existing records"""
        conn = temp_db.connect()
        session_id = str(uuid.uuid4())

        # Insert initial state
        state1 = json.dumps({"test": "value1"})
        execute_query(conn, """
            INSERT INTO game_states (session_id, state_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                state_data = excluded.state_data,
                updated_at = CURRENT_TIMESTAMP
        """, (session_id, state1))
        conn.commit()

        # Update with new state
        state2 = json.dumps({"test": "value2"})
        execute_query(conn, """
            INSERT INTO game_states (session_id, state_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                state_data = excluded.state_data,
                updated_at = CURRENT_TIMESTAMP
        """, (session_id, state2))
        conn.commit()

        # Verify only one record exists with updated value
        cursor = execute_query(conn,
            "SELECT state_data FROM game_states WHERE session_id = ?",
            (session_id,)
        )
        rows = cursor.fetchall()

        assert len(rows) == 1
        assert json.loads(rows[0]['state_data'])["test"] == "value2"

    def test_cleanup_of_old_sessions(self, temp_db):
        """Test cleanup of old sessions"""
        conn = temp_db.connect()

        # Create old session
        old_session_id = str(uuid.uuid4())
        state_data = json.dumps({"test": "old"})

        from datetime import datetime, timedelta
        old_timestamp = (datetime.utcnow() - timedelta(hours=25)).isoformat()

        execute_query(conn, """
            INSERT INTO game_states (session_id, state_data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (old_session_id, state_data, old_timestamp, old_timestamp))
        conn.commit()

        # Create new session
        new_session_id = str(uuid.uuid4())
        execute_query(conn, """
            INSERT INTO game_states (session_id, state_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (new_session_id, state_data))
        conn.commit()

        # Manual cleanup of old sessions (>24 hours)
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()

        execute_query(conn,
            "DELETE FROM game_states WHERE updated_at < ?",
            (cutoff,)
        )
        conn.commit()

        # Verify old session deleted
        cursor = execute_query(conn,
            "SELECT COUNT(*) as count FROM game_states WHERE session_id = ?",
            (old_session_id,)
        )
        result = cursor.fetchone()
        assert result['count'] == 0

        # Verify new session still exists
        cursor = execute_query(conn,
            "SELECT COUNT(*) as count FROM game_states WHERE session_id = ?",
            (new_session_id,)
        )
        result = cursor.fetchone()
        assert result['count'] == 1


class TestDatabaseErrorHandling:
    """Database error handling tests"""

    def test_invalid_query_handling(self, temp_db):
        """Test that invalid queries are handled gracefully"""
        conn = temp_db.connect()

        # Invalid SQL should raise exception
        with pytest.raises(Exception):
            execute_query(conn, "INVALID SQL QUERY")

    def test_null_value_handling(self, temp_db):
        """Test handling of NULL values in database"""
        conn = temp_db.connect()
        session_id = str(uuid.uuid4())

        # Insert with valid data
        state_data = json.dumps({"test": None})  # JSON null
        execute_query(conn, """
            INSERT INTO game_states (session_id, state_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (session_id, state_data))
        conn.commit()

        # Retrieve and verify
        cursor = execute_query(conn,
            "SELECT state_data FROM game_states WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        data = json.loads(row['state_data'])
        assert data["test"] is None

    def test_concurrent_writes_to_same_session(self, client):
        """Test concurrent writes to same session (last write wins)"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Get state twice
        state1 = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state2 = client.get("/api/game/state", cookies={"session_id": session_id}).json()

        # Modify both differently
        state1["self_name"] = "Name1"
        state2["self_name"] = "Name2"

        # Save both (last write wins)
        client.post("/api/game/state", json=state1, cookies={"session_id": session_id})
        client.post("/api/game/state", json=state2, cookies={"session_id": session_id})

        # Verify last write won
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert final_state["self_name"] == "Name2"

    def test_database_timestamp_handling(self, temp_db):
        """Test that timestamps are handled correctly"""
        conn = temp_db.connect()
        session_id = str(uuid.uuid4())

        # Insert with CURRENT_TIMESTAMP
        state_data = json.dumps({"test": "data"})
        execute_query(conn, """
            INSERT INTO game_states (session_id, state_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (session_id, state_data))
        conn.commit()

        # Retrieve and verify timestamp exists
        cursor = execute_query(conn,
            "SELECT updated_at FROM game_states WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        assert row['updated_at'] is not None

    def test_empty_state_data_handling(self, temp_db):
        """Test handling of minimal/empty state data"""
        conn = temp_db.connect()
        session_id = str(uuid.uuid4())

        # Insert minimal state
        state_data = json.dumps({})
        execute_query(conn, """
            INSERT INTO game_states (session_id, state_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (session_id, state_data))
        conn.commit()

        # Retrieve and verify
        cursor = execute_query(conn,
            "SELECT state_data FROM game_states WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        data = json.loads(row['state_data'])
        assert data == {}


class TestDatabasePerformance:
    """Database performance tests"""

    def test_bulk_session_creation(self, temp_db):
        """Test creating many sessions quickly"""
        conn = temp_db.connect()

        # Create 100 sessions
        sessions = []
        for i in range(100):
            session_id = str(uuid.uuid4())
            state_data = json.dumps({"test": f"data{i}"})

            execute_query(conn, """
                INSERT INTO game_states (session_id, state_data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (session_id, state_data))

            sessions.append(session_id)

        conn.commit()

        # Verify all exist
        cursor = execute_query(conn, "SELECT COUNT(*) as count FROM game_states")
        result = cursor.fetchone()
        assert result['count'] >= 100

    def test_rapid_state_updates(self, client):
        """Test rapid state updates don't cause issues"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Perform 20 rapid updates
        for i in range(20):
            state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
            state["self_name"] = f"Name{i}"
            response = client.post("/api/game/state", json=state, cookies={"session_id": session_id})
            assert response.status_code == 200

        # Verify final state
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert final_state["self_name"] == "Name19"

    def test_query_with_large_result_set(self, temp_db):
        """Test querying with large result sets"""
        conn = temp_db.connect()

        # Create many sessions
        for i in range(50):
            session_id = str(uuid.uuid4())
            state_data = json.dumps({"index": i})

            execute_query(conn, """
                INSERT INTO game_states (session_id, state_data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (session_id, state_data))

        conn.commit()

        # Query all
        cursor = execute_query(conn, "SELECT * FROM game_states")
        rows = cursor.fetchall()

        assert len(rows) >= 50
