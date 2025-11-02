"""User Journey Integration Tests - Complete end-to-end flows

Priority 3: Test complete user journeys from briefing to simulation.
These tests verify that the critical path works from a player's perspective:
- Briefing -> Loading -> Enter name -> Simulation
- Actions persist across page refreshes
- Timers complete correctly even after page close
- Complete game sessions work end-to-end
"""
import pytest
import json
import time
from fastapi.testclient import TestClient

from game.state import GameState
from core.config import CONFIG


class TestCompleteUserJourney:
    """Complete user journey tests - end-to-end scenarios"""

    def test_briefing_to_simulation_full_flow(self, client):
        """Test: Briefing -> Loading -> Enter name -> Simulation"""
        # Step 1: Player arrives (briefing screen creates session)
        response1 = client.get("/api/game/state")
        assert response1.status_code == 200
        session_id = response1.cookies.get("session_id")
        assert session_id is not None

        # Step 2: Loading screen - player enters name
        state = response1.json()
        state["self_name"] = "TestPlayer"
        response2 = client.post(
            "/api/game/state",
            json=state,
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200

        # Step 3: Enter simulation - verify name persisted
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})
        assert response3.status_code == 200
        assert response3.json()["self_name"] == "TestPlayer"

        # Step 4: Perform first action - gather resources
        response4 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )
        assert response4.status_code == 200

        # Step 5: Build womb
        time.sleep(0.1)
        response5 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )
        assert response5.status_code == 200

        # Verify complete flow succeeded
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert final_state["self_name"] == "TestPlayer"
        assert final_state["assembler_built"] == True

    def test_simulation_build_womb_refresh_womb_persists(self, client):
        """Test: Simulation -> Build womb -> Wait -> Refresh -> Womb still built"""
        # Step 1: Create session
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Step 2: Build womb
        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200
        assert response2.json()["state"]["assembler_built"] == True

        # Step 3: Wait for task (simulate)
        time.sleep(0.1)

        # Step 4: Simulate page refresh
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})
        assert response3.status_code == 200

        # Step 5: Verify womb still built
        assert response3.json()["assembler_built"] == True

    def test_create_clone_refresh_clone_persists(self, client):
        """Test: Create clone -> Refresh -> Clone still exists"""
        # Step 1: Setup
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Step 2: Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)

        # Step 3: Grow clone
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200
        clone_id = response2.json()["clone"]["id"]

        # Step 4: Simulate page refresh
        time.sleep(0.1)
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})

        # Step 5: Verify clone persists
        assert clone_id in response3.json()["clones"]
        assert response3.json()["clones"][clone_id]["kind"] == "BASIC"

    def test_gather_resource_close_tab_reopen_resource_granted(self, client):
        """Test: Gather resource -> Close tab -> Reopen -> Resource auto-granted"""
        # Step 1: Create session
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_tritanium = response1.json()["resources"]["Tritanium"]

        # Step 2: Start gathering
        response2 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200
        task_id = response2.json()["task_id"]

        # Step 3: Simulate closing tab (disconnect)
        # (In real scenario, client disconnects but server state persists)

        # Step 4: Manually complete task (simulate time passing)
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["active_tasks"][task_id]["start_time"] = time.time() - 100
        state["active_tasks"][task_id]["duration"] = 10
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Step 5: Simulate reopening tab
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})

        # Step 6: Verify resource was auto-granted
        assert response3.status_code == 200
        final_tritanium = response3.json()["resources"]["Tritanium"]
        assert final_tritanium > initial_tritanium

    def test_complete_game_session_multiple_actions(self, client):
        """Test: Complete game session with multiple actions"""
        # Step 1: Start new game
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Step 2: Enter name
        state = response1.json()
        state["self_name"] = "CompleteTester"
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Step 3: Gather resources
        time.sleep(0.1)
        client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )

        # Step 4: Build womb
        time.sleep(0.1)
        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200

        # Step 5: Gather clone materials
        time.sleep(0.1)
        client.post(
            "/api/game/gather-resource?resource=Synthetic",
            cookies={"session_id": session_id}
        )

        # Step 6: Grow clone
        time.sleep(0.1)
        response3 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        assert response3.status_code == 200
        clone_id = response3.json()["clone"]["id"]

        # Step 7: Apply clone
        response4 = client.post(
            f"/api/game/apply-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )
        assert response4.status_code == 200

        # Step 8: Run expedition
        response5 = client.post(
            "/api/game/run-expedition?kind=MINING",
            cookies={"session_id": session_id}
        )
        assert response5.status_code == 200

        # Step 9: Verify complete session state
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()

        assert final_state["self_name"] == "CompleteTester"
        assert final_state["assembler_built"] == True
        assert clone_id in final_state["clones"]
        assert final_state["applied_clone_id"] == clone_id or not final_state["clones"][clone_id]["alive"]


class TestRefreshRecovery:
    """Tests for page refresh and recovery scenarios"""

    def test_refresh_during_gather_task(self, client):
        """Test refresh while gather task is active"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Start gather task
        response2 = client.post(
            "/api/game/gather-resource?resource=Metal Ore",
            cookies={"session_id": session_id}
        )
        task_id = response2.json()["task_id"]

        # Refresh immediately
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})

        # Verify task still active
        assert task_id in response3.json()["active_tasks"]

    def test_refresh_during_build_womb_task(self, client):
        """Test refresh while build womb task is active"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Start build
        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )
        task_id = response2.json()["task_id"]

        # Refresh
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})

        # Verify womb marked as built and task exists
        assert response3.json()["assembler_built"] == True
        assert task_id in response3.json()["active_tasks"]

    def test_refresh_after_task_completion(self, client):
        """Test refresh after task has completed"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_resources = response1.json()["resources"]["Biomass"]

        # Start gather
        response2 = client.post(
            "/api/game/gather-resource?resource=Biomass",
            cookies={"session_id": session_id}
        )
        task_id = response2.json()["task_id"]

        # Force complete task
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["active_tasks"][task_id]["start_time"] = time.time() - 100
        state["active_tasks"][task_id]["duration"] = 10
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Refresh
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})

        # Verify task auto-completed and resources granted
        assert task_id not in response3.json()["active_tasks"]
        assert response3.json()["resources"]["Biomass"] > initial_resources

    def test_multiple_refreshes_in_quick_succession(self, client):
        """Test multiple rapid page refreshes"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})

        # Rapid refreshes
        for i in range(10):
            response = client.get("/api/game/state", cookies={"session_id": session_id})
            assert response.status_code == 200
            assert response.json()["assembler_built"] == True

    def test_refresh_with_expired_cookie(self, client):
        """Test refresh with expired session cookie"""
        # Create session
        response1 = client.get("/api/game/state")
        old_session_id = response1.cookies.get("session_id")

        # Build something
        client.post("/api/game/build-womb", cookies={"session_id": old_session_id})

        # Simulate expired cookie by using non-existent session
        response2 = client.get("/api/game/state", cookies={"session_id": "expired-session"})

        # Should create new session
        assert response2.status_code == 200
        new_session_id = response2.cookies.get("session_id")
        assert new_session_id != old_session_id

        # New session should be fresh
        assert response2.json()["assembler_built"] == False


class TestErrorRecovery:
    """Tests for error recovery scenarios"""

    def test_recover_from_failed_action_retry_succeeds(self, client):
        """Test recovering from failed action and retrying"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Try to grow clone without womb (should fail)
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 400

        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)

        # Retry growing clone (should succeed)
        response3 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        assert response3.status_code == 200

    def test_state_consistency_after_failed_operation(self, client):
        """Test that state remains consistent after failed operation"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_state = response1.json()

        # Try invalid operation (build womb with no resources)
        state = initial_state.copy()
        state["resources"] = {k: 0 for k in state["resources"]}
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 400

        # Verify state unchanged
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})
        assert response3.json()["assembler_built"] == False
        assert response3.json()["resources"]["Tritanium"] == 0

    def test_network_interruption_recovery(self, client):
        """Test recovery from simulated network interruption"""
        # Create session
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Perform action
        client.post("/api/game/build-womb", cookies={"session_id": session_id})

        # Simulate network interruption by closing client
        # (In real app, frontend would retry on reconnection)

        # Reconnect and verify state
        response2 = client.get("/api/game/state", cookies={"session_id": session_id})
        assert response2.status_code == 200
        assert response2.json()["assembler_built"] == True

    def test_partial_action_completion_recovery(self, client):
        """Test recovery from partially completed action"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Start gather task
        response2 = client.post(
            "/api/game/gather-resource?resource=Organic",
            cookies={"session_id": session_id}
        )
        task_id = response2.json()["task_id"]

        # Verify task exists
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert task_id in state["active_tasks"]

        # Simulate completion
        state["active_tasks"][task_id]["start_time"] = time.time() - 100
        state["active_tasks"][task_id]["duration"] = 10
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Check status - should auto-complete
        response3 = client.get("/api/game/tasks/status", cookies={"session_id": session_id})
        assert response3.json()["active"] == False


class TestTimerPersistence:
    """Tests for timer persistence across refreshes"""

    def test_timer_persists_across_refresh(self, client):
        """Test that timers persist across page refreshes"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Start timer
        response2 = client.post(
            "/api/game/gather-resource?resource=Shilajit",
            cookies={"session_id": session_id}
        )
        task_id = response2.json()["task_id"]
        start_time = response2.json()["state"]["active_tasks"][task_id]["start_time"]

        # Refresh
        time.sleep(0.5)
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})

        # Verify timer still running and time elapsed
        if task_id in response3.json()["active_tasks"]:
            persisted_start_time = response3.json()["active_tasks"][task_id]["start_time"]
            assert abs(persisted_start_time - start_time) < 1.0  # Should be same start time

    def test_timer_completion_check_on_refresh(self, client):
        """Test that timer completion is checked on refresh"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_synthetic = response1.json()["resources"]["Synthetic"]

        # Start timer
        response2 = client.post(
            "/api/game/gather-resource?resource=Synthetic",
            cookies={"session_id": session_id}
        )
        task_id = response2.json()["task_id"]

        # Force complete
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["active_tasks"][task_id]["start_time"] = time.time() - 100
        state["active_tasks"][task_id]["duration"] = 10
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Refresh - should auto-complete
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})

        # Verify completed
        assert task_id not in response3.json()["active_tasks"]
        assert response3.json()["resources"]["Synthetic"] > initial_synthetic

    def test_multiple_timers_different_states(self, client):
        """Test multiple timers at different completion states"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Start gather task
        response2 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )
        task_id1 = response2.json()["task_id"]

        # Complete first task
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["active_tasks"][task_id1]["start_time"] = time.time() - 100
        state["active_tasks"][task_id1]["duration"] = 10
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Check status
        response3 = client.get("/api/game/tasks/status", cookies={"session_id": session_id})
        assert response3.json()["active"] == False


class TestSessionIsolation:
    """Tests for session isolation and concurrent users"""

    def test_two_players_simultaneous_actions(self, client):
        """Test two players performing actions simultaneously"""
        # Player 1
        response1 = client.get("/api/game/state")
        session1 = response1.cookies.get("session_id")

        # Player 2
        response2 = client.get("/api/game/state")
        session2 = response2.cookies.get("session_id")

        # Both build wombs
        response3 = client.post("/api/game/build-womb", cookies={"session_id": session1})
        response4 = client.post("/api/game/build-womb", cookies={"session_id": session2})

        assert response3.status_code == 200
        assert response4.status_code == 200

        # Verify isolation
        state1 = client.get("/api/game/state", cookies={"session_id": session1}).json()
        state2 = client.get("/api/game/state", cookies={"session_id": session2}).json()

        assert state1["assembler_built"] == True
        assert state2["assembler_built"] == True
        # But they should be independent sessions
        assert state1 != state2  # Different state objects

    def test_session_does_not_leak_to_other_session(self, client):
        """Test that session data doesn't leak between sessions"""
        # Session 1: Set name
        response1 = client.get("/api/game/state")
        session1 = response1.cookies.get("session_id")

        state1 = response1.json()
        state1["self_name"] = "Player1"
        client.post("/api/game/state", json=state1, cookies={"session_id": session1})

        # Session 2: Different name
        response2 = client.get("/api/game/state")
        session2 = response2.cookies.get("session_id")

        state2 = response2.json()
        state2["self_name"] = "Player2"
        client.post("/api/game/state", json=state2, cookies={"session_id": session2})

        # Verify no leakage
        final_state1 = client.get("/api/game/state", cookies={"session_id": session1}).json()
        final_state2 = client.get("/api/game/state", cookies={"session_id": session2}).json()

        assert final_state1["self_name"] == "Player1"
        assert final_state2["self_name"] == "Player2"

    def test_concurrent_task_execution_different_sessions(self, client):
        """Test concurrent task execution in different sessions"""
        # Session 1
        response1 = client.get("/api/game/state")
        session1 = response1.cookies.get("session_id")

        # Session 2
        response2 = client.get("/api/game/state")
        session2 = response2.cookies.get("session_id")

        # Both start gather tasks
        response3 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session1}
        )
        response4 = client.post(
            "/api/game/gather-resource?resource=Metal Ore",
            cookies={"session_id": session2}
        )

        assert response3.status_code == 200
        assert response4.status_code == 200

        # Both should have active tasks
        status1 = client.get("/api/game/tasks/status", cookies={"session_id": session1}).json()
        status2 = client.get("/api/game/tasks/status", cookies={"session_id": session2}).json()

        assert status1["active"] == True
        assert status2["active"] == True
