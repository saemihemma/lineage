"""Critical Path Tests - Ensures the core user journey never breaks

Priority 1: Test session management, state recovery, name entry, and critical actions.
These tests verify that players can always complete the core flow:
Briefing -> Loading (enter name) -> Simulation (main game)
"""
import pytest
import json
import time
import uuid
from fastapi.testclient import TestClient

from game.state import GameState
from core.config import CONFIG


class TestSessionManagement:
    """Session management tests - ensure sessions persist and recover properly"""

    def test_session_creation_on_first_visit(self, client):
        """Test that first visit creates a new session with cookie"""
        response = client.get("/api/game/state")

        assert response.status_code == 200
        assert "session_id" in response.cookies

        session_id = response.cookies.get("session_id")
        assert session_id is not None
        assert len(session_id) > 0

        # Verify session data is valid
        data = response.json()
        assert data["soul_percent"] == CONFIG["SOUL_START"]
        assert data["soul_xp"] == 0

    def test_session_retrieval_with_valid_cookie(self, client):
        """Test that valid session cookie retrieves existing state"""
        # Create session
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Modify state
        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200

        # Retrieve with same cookie
        response3 = client.get(
            "/api/game/state",
            cookies={"session_id": session_id}
        )
        assert response3.status_code == 200
        assert response3.json()["assembler_built"] == True

    def test_session_persistence_across_requests(self, client):
        """Test that session persists across multiple requests"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Make multiple modifications
        actions = [
            lambda: client.post("/api/game/gather-resource?resource=Tritanium",
                              cookies={"session_id": session_id}),
            lambda: client.post("/api/game/build-womb",
                              cookies={"session_id": session_id}),
        ]

        for action in actions:
            time.sleep(0.1)
            response = action()
            assert response.status_code in [200, 400]  # 400 if task blocking

        # Verify state accumulated changes
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert final_state["assembler_built"] == True

    def test_session_recovery_after_page_refresh(self, client):
        """Test that session recovers after simulated page refresh"""
        # Initial load
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})

        # Simulate page refresh (new request with same cookie)
        response2 = client.get("/api/game/state", cookies={"session_id": session_id})

        assert response2.status_code == 200
        assert response2.json()["assembler_built"] == True
        assert response2.cookies.get("session_id") == session_id

    def test_expired_session_handling(self, client, temp_db):
        """Test that expired sessions are cleaned up and new one created"""
        # Create session
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Manually expire the session by setting old timestamp
        from datetime import datetime, timedelta
        from database import execute_query

        conn = temp_db.connect()
        old_timestamp = (datetime.utcnow() - timedelta(hours=25)).isoformat()

        execute_query(conn, """
            UPDATE game_states
            SET updated_at = ?
            WHERE session_id = ?
        """, (old_timestamp, session_id))
        conn.commit()

        # Try to access with expired session
        response2 = client.get("/api/game/state", cookies={"session_id": session_id})

        assert response2.status_code == 200
        # Should create new session
        new_session_id = response2.cookies.get("session_id")
        assert new_session_id != session_id

    def test_missing_cookie_creates_new_session(self, client):
        """Test that missing cookie creates new session"""
        # Request without cookie
        response = client.get("/api/game/state")

        assert response.status_code == 200
        assert "session_id" in response.cookies

        data = response.json()
        assert data["soul_xp"] == 0
        assert data["assembler_built"] == False

    def test_invalid_session_id_creates_new_session(self, client):
        """Test that invalid session ID creates new session"""
        # Request with invalid/non-existent session
        response = client.get(
            "/api/game/state",
            cookies={"session_id": "invalid-uuid-12345"}
        )

        assert response.status_code == 200
        assert "session_id" in response.cookies

        # Should create fresh state
        data = response.json()
        assert data["soul_xp"] == 0

    def test_concurrent_session_isolation(self, client):
        """Test that concurrent sessions don't interfere with each other"""
        # Create two separate sessions
        response1 = client.get("/api/game/state")
        session1 = response1.cookies.get("session_id")

        response2 = client.get("/api/game/state")
        session2 = response2.cookies.get("session_id")

        assert session1 != session2

        # Modify session 1
        client.post("/api/game/build-womb", cookies={"session_id": session1})

        # Verify session 1 has womb
        state1 = client.get("/api/game/state", cookies={"session_id": session1}).json()
        assert state1["assembler_built"] == True

        # Verify session 2 doesn't have womb
        state2 = client.get("/api/game/state", cookies={"session_id": session2}).json()
        assert state2["assembler_built"] == False


class TestStateRecovery:
    """State recovery tests - ensure state persists and recovers from failures"""

    def test_get_state_creates_state_if_missing(self, client):
        """Test GET /api/game/state creates state if missing (auto-recovery)"""
        # New session without existing state
        response = client.get("/api/game/state")

        assert response.status_code == 200
        data = response.json()

        # Should create fresh state
        assert "version" in data
        assert "soul_percent" in data
        assert data["assembler_built"] == False

    def test_get_state_with_existing_state(self, client):
        """Test GET /api/game/state returns existing state"""
        # Create state
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Modify state
        client.post("/api/game/build-womb", cookies={"session_id": session_id})

        # Retrieve state
        response2 = client.get("/api/game/state", cookies={"session_id": session_id})

        assert response2.status_code == 200
        assert response2.json()["assembler_built"] == True

    def test_state_persists_in_database(self, client, temp_db):
        """Test that state is saved to database and can be retrieved"""
        # Create and modify state
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        client.post("/api/game/build-womb", cookies={"session_id": session_id})

        # Query database directly
        from database import execute_query
        conn = temp_db.connect()
        cursor = execute_query(conn,
            "SELECT state_data FROM game_states WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        state_data = json.loads(row['state_data'])
        assert state_data["assembler_built"] == True

    def test_state_recovery_after_backend_restart(self, client, temp_db):
        """Test state auto-recovery after backend restart (create_if_missing=True)"""
        # This simulates backend restart where database exists but session might not
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})

        # Delete state from database (simulate data loss)
        from database import execute_query
        conn = temp_db.connect()
        execute_query(conn, "DELETE FROM game_states WHERE session_id = ?", (session_id,))
        conn.commit()

        # Try to access state - should auto-recover
        response2 = client.get("/api/game/state", cookies={"session_id": session_id})

        assert response2.status_code == 200
        # Should create fresh state (auto-recovery)
        assert response2.json()["assembler_built"] == False

    def test_corrupted_state_handling(self, client, temp_db):
        """Test handling of corrupted state data"""
        # Create session
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Corrupt the state in database
        from database import execute_query
        conn = temp_db.connect()
        execute_query(conn, """
            UPDATE game_states
            SET state_data = ?
            WHERE session_id = ?
        """, ('{"corrupted": "data}', session_id))  # Invalid JSON
        conn.commit()

        # Try to load - should recover gracefully
        response2 = client.get("/api/game/state", cookies={"session_id": session_id})

        assert response2.status_code == 200
        # Should auto-recover with fresh state
        data = response2.json()
        assert "version" in data

    def test_state_version_increments_on_save(self, client):
        """Test that state version increments on each save"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_version = response1.json()["version"]

        # Modify state
        response2 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )

        # Version should have incremented
        new_version = response2.json()["state"]["version"]
        assert new_version > initial_version


class TestNameEntryFlow:
    """Name entry flow tests - ensure player name persists"""

    def test_entering_name_for_first_time(self, client):
        """Test entering name for the first time"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Get initial state
        state = response1.json()
        assert state["self_name"] == ""

        # Set name
        state["self_name"] = "TestPlayer"
        response2 = client.post(
            "/api/game/state",
            json=state,
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200

        # Verify name persisted
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})
        assert response3.json()["self_name"] == "TestPlayer"

    def test_updating_name_persists(self, client):
        """Test that updating name persists correctly"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Set initial name
        state = response1.json()
        state["self_name"] = "OldName"
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Update name
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["self_name"] = "NewName"
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Verify updated name
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert final_state["self_name"] == "NewName"

    def test_empty_name_allowed(self, client):
        """Test that empty name is allowed (user might skip)"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        state = response1.json()
        state["self_name"] = ""
        response2 = client.post(
            "/api/game/state",
            json=state,
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200

    def test_name_character_limits(self, client):
        """Test that name handles various character lengths"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Test short name
        state = response1.json()
        state["self_name"] = "A"
        response2 = client.post("/api/game/state", json=state, cookies={"session_id": session_id})
        assert response2.status_code == 200

        # Test long name
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["self_name"] = "A" * 100
        response3 = client.post("/api/game/state", json=state, cookies={"session_id": session_id})
        assert response3.status_code == 200

        # Verify long name persisted
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert len(final_state["self_name"]) == 100

    def test_name_persistence_after_save(self, client):
        """Test that name persists across game saves"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Set name
        state = response1.json()
        state["self_name"] = "PersistentPlayer"
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Do some game actions
        client.post("/api/game/gather-resource?resource=Tritanium",
                   cookies={"session_id": session_id})
        time.sleep(0.1)

        # Verify name still there
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert final_state["self_name"] == "PersistentPlayer"


class TestCriticalActions:
    """Critical actions tests - ensure core game actions work reliably"""

    def test_build_womb_full_flow(self, client):
        """Test complete build womb flow"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb
        response2 = client.post("/api/game/build-womb", cookies={"session_id": session_id})

        assert response2.status_code == 200
        data = response2.json()

        # Verify response structure
        assert "state" in data
        assert "message" in data
        assert "task_id" in data

        # Verify womb was built
        assert data["state"]["assembler_built"] == True

        # Verify resources were consumed
        assert data["state"]["resources"]["Tritanium"] < 100

        # Verify task was created
        assert len(data["state"]["active_tasks"]) == 1

    def test_grow_clone_full_flow(self, client):
        """Test complete grow clone flow"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb first
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)

        # Grow clone
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
        data = response2.json()

        # Verify response structure
        assert "state" in data
        assert "clone" in data
        assert "soul_split" in data
        assert "message" in data
        assert "task_id" in data

        # Verify clone data
        clone = data["clone"]
        assert clone["kind"] == "BASIC"
        assert clone["alive"] == True
        assert "traits" in clone

    def test_gather_resource_with_timer_completion(self, client):
        """Test gather resource with timer and auto-completion"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_tritanium = response1.json()["resources"]["Tritanium"]

        # Start gathering
        response2 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
        data = response2.json()

        # Verify task created
        assert "task_id" in data
        assert len(data["state"]["active_tasks"]) == 1

        # Manually complete task by setting old start time
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        task_id = list(state["active_tasks"].keys())[0]
        state["active_tasks"][task_id]["start_time"] = time.time() - 100
        state["active_tasks"][task_id]["duration"] = 10
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Check task status - should auto-complete
        response3 = client.get("/api/game/tasks/status", cookies={"session_id": session_id})
        assert response3.json()["active"] == False

        # Verify resources increased
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert final_state["resources"]["Tritanium"] > initial_tritanium

    def test_run_expedition_immediate(self, client):
        """Test run expedition (immediate, no timer)"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Setup: build womb, grow clone, apply
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        clone_id = response2.json()["clone"]["id"]
        client.post(f"/api/game/apply-clone?clone_id={clone_id}",
                   cookies={"session_id": session_id})

        # Run expedition
        response3 = client.post(
            "/api/game/run-expedition?kind=MINING",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 200
        data = response3.json()

        # Verify immediate completion (no task)
        assert "state" in data
        assert "message" in data

        # Verify clone gained XP
        clone = data["state"]["clones"][clone_id]
        assert clone["xp"]["MINING"] > 0

    def test_upload_clone_state_update(self, client):
        """Test upload clone updates state correctly"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_soul_xp = response1.json()["soul_xp"]

        # Setup: create clone with XP
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        clone_id = response2.json()["clone"]["id"]

        # Give clone XP
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["clones"][clone_id]["xp"] = {"MINING": 50, "COMBAT": 30, "EXPLORATION": 20}
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Upload clone
        response3 = client.post(
            f"/api/game/upload-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 200
        data = response3.json()

        # Verify clone uploaded
        assert data["state"]["clones"][clone_id]["uploaded"] == True
        assert data["state"]["clones"][clone_id]["alive"] == False

        # Verify SELF gained XP
        assert data["state"]["soul_xp"] > initial_soul_xp

    def test_apply_clone_state_update(self, client):
        """Test apply clone updates state correctly"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Setup: create clone
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        clone_id = response2.json()["clone"]["id"]

        # Apply clone
        response3 = client.post(
            f"/api/game/apply-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 200
        assert response3.json()["state"]["applied_clone_id"] == clone_id

    def test_all_actions_update_database(self, client, temp_db):
        """Test that all actions update the database correctly"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Perform various actions
        actions = [
            lambda: client.post("/api/game/gather-resource?resource=Tritanium",
                              cookies={"session_id": session_id}),
            lambda: client.post("/api/game/build-womb",
                              cookies={"session_id": session_id}),
        ]

        for action in actions:
            time.sleep(0.1)
            action()

        # Verify database has latest state
        from database import execute_query
        conn = temp_db.connect()
        cursor = execute_query(conn,
            "SELECT state_data FROM game_states WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        state_data = json.loads(row['state_data'])
        assert state_data["assembler_built"] == True

    def test_actions_fail_gracefully_with_clear_errors(self, client):
        """Test that actions fail gracefully with clear error messages"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Try to grow without womb
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 400
        assert "Build the Womb first" in response2.json()["detail"]

        # Try to build with insufficient resources
        state = response1.json()
        state["resources"] = {k: 0 for k in state["resources"]}
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        response3 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 400
        assert "Insufficient resources" in response3.json()["detail"]
