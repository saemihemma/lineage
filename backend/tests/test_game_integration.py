"""Integration tests for complete game flows"""
import pytest
import time
from fastapi.testclient import TestClient


class TestCompleteGameFlow:
    """Tests for complete game workflows from start to finish"""

    def test_new_player_to_first_clone_upload_flow(self, client):
        """Test complete flow: new game -> build womb -> grow clone -> upload"""
        # Step 1: New game
        response1 = client.get("/api/game/state")
        assert response1.status_code == 200
        session_id = response1.cookies.get("session_id")
        initial_state = response1.json()

        assert initial_state["assembler_built"] == False
        assert len(initial_state["clones"]) == 0
        assert initial_state["soul_xp"] == 0

        # Step 2: Build womb
        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200
        assert response2.json()["state"]["assembler_built"] == True

        # Step 3: Grow clone
        time.sleep(0.1)
        response3 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        assert response3.status_code == 200
        clone_id = response3.json()["clone"]["id"]
        assert len(response3.json()["state"]["clones"]) == 1

        # Step 4: Give clone XP
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["clones"][clone_id]["xp"] = {"MINING": 50, "COMBAT": 30, "EXPLORATION": 20}
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Step 5: Upload clone
        response4 = client.post(
            f"/api/game/upload-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )
        assert response4.status_code == 200
        final_state = response4.json()["state"]

        assert final_state["clones"][clone_id]["uploaded"] == True
        assert final_state["soul_xp"] > initial_state["soul_xp"]

    def test_resource_gathering_to_clone_creation_flow(self, client):
        """Test flow: gather resources -> build womb -> grow clone"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Gather multiple resources
        resources = ["Tritanium", "Metal Ore", "Biomass"]
        for resource in resources:
            time.sleep(0.1)
            response = client.post(
                f"/api/game/gather-resource?resource={resource}",
                cookies={"session_id": session_id}
            )
            assert response.status_code == 200

        # Build womb
        time.sleep(0.1)
        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200

        # Gather clone materials
        clone_materials = ["Synthetic", "Organic", "Shilajit"]
        for resource in clone_materials:
            time.sleep(0.1)
            response = client.post(
                f"/api/game/gather-resource?resource={resource}",
                cookies={"session_id": session_id}
            )
            assert response.status_code == 200

        # Grow clone
        time.sleep(0.1)
        response3 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        assert response3.status_code == 200

    def test_expedition_lifecycle_flow(self, client):
        """Test flow: create clone -> apply -> expedition -> unapply/death"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Setup: build womb and grow clone
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

        # Run expedition
        response4 = client.post(
            "/api/game/run-expedition?kind=MINING",
            cookies={"session_id": session_id}
        )
        assert response4.status_code == 200

        # Check clone status after expedition
        state = response4.json()["state"]
        clone = state["clones"][clone_id]

        if clone["alive"]:
            # Clone survived
            assert clone["xp"]["MINING"] > 0
            assert clone["survived_runs"] > 0
            assert state["applied_clone_id"] == clone_id
        else:
            # Clone died
            assert state["applied_clone_id"] == ""

    def test_multiple_clones_management_flow(self, client):
        """Test managing multiple clones"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)

        # Grow multiple clones
        clone_ids = []
        for i in range(3):
            # Add resources for each clone
            state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
            state["resources"]["Synthetic"] = 20
            state["resources"]["Organic"] = 20
            state["resources"]["Shilajit"] = 5
            client.post("/api/game/state", json=state, cookies={"session_id": session_id})

            time.sleep(0.1)
            response = client.post(
                "/api/game/grow-clone?kind=BASIC",
                cookies={"session_id": session_id}
            )
            assert response.status_code == 200
            clone_ids.append(response.json()["clone"]["id"])

        # Verify all clones exist
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert len(state["clones"]) == 3

        # Apply and use different clones
        for clone_id in clone_ids:
            if state["clones"][clone_id]["alive"]:
                client.post(
                    f"/api/game/apply-clone?clone_id={clone_id}",
                    cookies={"session_id": session_id}
                )
                client.post(
                    "/api/game/run-expedition?kind=MINING",
                    cookies={"session_id": session_id}
                )

    def test_soul_progression_flow(self, client):
        """Test soul XP progression and leveling"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)

        # Create multiple clones with XP and upload them
        uploaded_clones = 0
        target_uploads = 3

        for i in range(target_uploads):
            # Add resources
            state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
            state["resources"]["Synthetic"] = 20
            state["resources"]["Organic"] = 20
            state["resources"]["Shilajit"] = 5
            state["soul_percent"] = 100.0  # Restore soul
            client.post("/api/game/state", json=state, cookies={"session_id": session_id})

            # Grow clone
            time.sleep(0.1)
            response = client.post(
                "/api/game/grow-clone?kind=BASIC",
                cookies={"session_id": session_id}
            )
            clone_id = response.json()["clone"]["id"]

            # Give clone XP
            state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
            state["clones"][clone_id]["xp"] = {"MINING": 50, "COMBAT": 50, "EXPLORATION": 50}
            client.post("/api/game/state", json=state, cookies={"session_id": session_id})

            # Upload
            response = client.post(
                f"/api/game/upload-clone?clone_id={clone_id}",
                cookies={"session_id": session_id}
            )
            assert response.status_code == 200
            uploaded_clones += 1

        # Verify soul XP increased
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert final_state["soul_xp"] > 0
        assert uploaded_clones == target_uploads


class TestTaskManagement:
    """Tests for task system and state persistence"""

    def test_task_creation_and_completion(self, client):
        """Test task is created and auto-completes"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Start a gather task
        response2 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200
        task_id = response2.json()["task_id"]

        # Verify task is active
        response3 = client.get(
            "/api/game/tasks/status",
            cookies={"session_id": session_id}
        )
        data = response3.json()
        assert data["active"] == True
        assert data["task"]["id"] == task_id

    def test_task_persistence_across_requests(self, client):
        """Test that tasks persist across different requests"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Start task
        response2 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )
        task_id = response2.json()["task_id"]

        # Check state has task
        response3 = client.get(
            "/api/game/state",
            cookies={"session_id": session_id}
        )
        state = response3.json()
        assert task_id in state["active_tasks"]

        # Check task status
        response4 = client.get(
            "/api/game/tasks/status",
            cookies={"session_id": session_id}
        )
        assert response4.json()["active"] == True

    def test_task_blocking_mechanism(self, client):
        """Test that tasks block other actions"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb first for future tests
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)

        # Start gather task
        response2 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200

        # Try to start another gather
        response3 = client.post(
            "/api/game/gather-resource?resource=Metal Ore",
            cookies={"session_id": session_id}
        )
        assert response3.status_code == 400

        # Try to build womb
        response4 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )
        assert response4.status_code == 400

        # Try to grow clone
        response5 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        assert response5.status_code == 400

    def test_concurrent_session_isolation(self, client):
        """Test that tasks in different sessions don't interfere"""
        # Session 1
        response1 = client.get("/api/game/state")
        session1 = response1.cookies.get("session_id")

        # Session 2
        response2 = client.get("/api/game/state")
        session2 = response2.cookies.get("session_id")

        # Start task in session 1
        response3 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session1}
        )
        assert response3.status_code == 200

        # Should be able to start task in session 2
        response4 = client.post(
            "/api/game/gather-resource?resource=Metal Ore",
            cookies={"session_id": session2}
        )
        assert response4.status_code == 200

        # Both sessions should have active tasks
        status1 = client.get(
            "/api/game/tasks/status",
            cookies={"session_id": session1}
        ).json()
        status2 = client.get(
            "/api/game/tasks/status",
            cookies={"session_id": session2}
        ).json()

        assert status1["active"] == True
        assert status2["active"] == True


class TestEdgeCasesAndErrors:
    """Tests for edge cases and error handling"""

    def test_malformed_session_id_creates_new(self, client):
        """Test that malformed session ID creates new session"""
        response = client.get(
            "/api/game/state",
            cookies={"session_id": "not-a-valid-uuid"}
        )

        assert response.status_code == 200
        # Should create new session
        assert "session_id" in response.cookies

    def test_state_consistency_after_error(self, client):
        """Test that state remains consistent after error"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_state = response1.json()

        # Try invalid operation (grow without womb)
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 400

        # Verify state didn't change
        response3 = client.get(
            "/api/game/state",
            cookies={"session_id": session_id}
        )
        current_state = response3.json()

        assert current_state["assembler_built"] == initial_state["assembler_built"]
        assert len(current_state["clones"]) == len(initial_state["clones"])

    def test_resource_integrity_after_operations(self, client):
        """Test that resources don't go negative or become inconsistent"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb (consumes resources)
        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )

        state = response2.json()["state"]

        # Verify no negative resources
        for resource, amount in state["resources"].items():
            assert amount >= 0, f"{resource} is negative: {amount}"

    def test_invalid_expedition_type(self, client):
        """Test running expedition with invalid type"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb and grow clone
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        clone_id = response2.json()["clone"]["id"]
        client.post(
            f"/api/game/apply-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )

        # Try invalid expedition type
        response3 = client.post(
            "/api/game/run-expedition?kind=INVALID",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 400

    def test_database_rollback_on_error(self, client):
        """Test that database doesn't save on error"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_resources = response1.json()["resources"].copy()

        # Try to build womb with insufficient resources
        state = response1.json()
        state["resources"] = {k: 0 for k in state["resources"]}
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 400

        # Verify resources are still zero (operation didn't partially complete)
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})
        current_resources = response3.json()["resources"]

        for resource, amount in current_resources.items():
            assert amount == 0  # Should still be zero, not partially deducted


class TestPracticeXPSystem:
    """Tests for practice XP and progression"""

    def test_practice_xp_from_gathering(self, client):
        """Test that gathering awards Kinetic XP"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_xp = response1.json()["practices_xp"]["Kinetic"]

        # Gather resource
        client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )

        # Check XP increased
        response2 = client.get("/api/game/state", cookies={"session_id": session_id})
        assert response2.json()["practices_xp"]["Kinetic"] > initial_xp

    def test_practice_xp_from_building(self, client):
        """Test that building awards Constructive XP"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_xp = response1.json()["practices_xp"]["Constructive"]

        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})

        # Check XP increased
        response2 = client.get("/api/game/state", cookies={"session_id": session_id})
        assert response2.json()["practices_xp"]["Constructive"] > initial_xp

    def test_practice_xp_from_expeditions(self, client):
        """Test that expeditions award practice XP"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_kinetic = response1.json()["practices_xp"]["Kinetic"]
        initial_cognitive = response1.json()["practices_xp"]["Cognitive"]

        # Setup: build womb and grow clone
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        clone_id = response2.json()["clone"]["id"]
        client.post(
            f"/api/game/apply-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )

        # Mining expedition (should award Kinetic)
        client.post(
            "/api/game/run-expedition?kind=MINING",
            cookies={"session_id": session_id}
        )

        state1 = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert state1["practices_xp"]["Kinetic"] > initial_kinetic

        # Setup for exploration
        if state1["clones"][clone_id]["alive"]:
            client.post(
                f"/api/game/apply-clone?clone_id={clone_id}",
                cookies={"session_id": session_id}
            )

            # Exploration expedition (should award Cognitive)
            client.post(
                "/api/game/run-expedition?kind=EXPLORATION",
                cookies={"session_id": session_id}
            )

            state2 = client.get("/api/game/state", cookies={"session_id": session_id}).json()
            assert state2["practices_xp"]["Cognitive"] > initial_cognitive
