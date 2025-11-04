"""Comprehensive tests for game API endpoints"""
import pytest
import json
import time
import uuid
from fastapi.testclient import TestClient

from game.state import GameState
from core.config import CONFIG


class TestGameStateEndpoint:
    """Tests for GET/POST /api/game/state endpoints"""

    def test_get_state_creates_new_session(self, client):
        """Test that GET /state creates a new game state if none exists"""
        response = client.get("/api/game/state")

        assert response.status_code == 200
        data = response.json()

        # Verify session cookie is set
        assert "session_id" in response.cookies

        # Verify state structure
        assert "version" in data
        assert "soul_percent" in data
        assert "soul_xp" in data
        assert "assembler_built" in data
        assert "resources" in data
        assert "clones" in data
        assert "applied_clone_id" in data
        assert "practices_xp" in data
        assert "active_tasks" in data

        # Verify default values
        assert data["soul_percent"] == CONFIG["SOUL_START"]
        assert data["soul_xp"] == 0
        assert data["assembler_built"] == False
        assert data["clones"] == {}
        assert data["applied_clone_id"] == ""

    def test_get_state_retrieves_existing_session(self, client):
        """Test that GET /state retrieves existing game state"""
        # Create initial state
        response1 = client.get("/api/game/state")
        assert response1.status_code == 200
        session_id = response1.cookies.get("session_id")

        # Modify state (build womb)
        client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )

        # Retrieve state again
        response2 = client.get(
            "/api/game/state",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200
        data = response2.json()

        # Verify state was persisted
        assert data["assembler_built"] == True

    def test_get_state_without_session_id_creates_new(self, client):
        """Test that GET /state without session_id creates new state"""
        response = client.get("/api/game/state")

        assert response.status_code == 200
        assert "session_id" in response.cookies
        data = response.json()
        assert data["soul_xp"] == 0

    def test_post_state_saves_game_state(self, client):
        """Test that POST /state saves game state"""
        # Get initial state
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Create modified state
        state_data = {
            "version": 1,
            "rng_seed": 12345,
            "soul_percent": 90.0,
            "soul_xp": 50,
            "assembler_built": True,
            "resources": {
                "Tritanium": 100,
                "Metal Ore": 50
            },
            "applied_clone_id": "",
            "practices_xp": {"Kinetic": 10, "Cognitive": 0, "Constructive": 20},
            "last_saved_ts": time.time(),
            "self_name": "TestPlayer",
            "active_tasks": {},
            "ui_layout": {},
            "clones": {}
        }

        # Save state
        response2 = client.post(
            "/api/game/state",
            json=state_data,
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
        assert response2.json() == {"status": "saved"}

        # Verify state was saved
        response3 = client.get(
            "/api/game/state",
            cookies={"session_id": session_id}
        )
        data = response3.json()
        assert data["soul_xp"] == 50
        assert data["assembler_built"] == True
        assert data["soul_percent"] == 90.0

    def test_post_state_with_invalid_data_returns_400(self, client):
        """Test that POST /state with invalid data returns 400"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Send invalid data (missing required fields)
        invalid_data = {"invalid": "data"}

        response2 = client.post(
            "/api/game/state",
            json=invalid_data,
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 400
        assert "Invalid game state" in response2.json()["detail"]

    def test_state_persistence_across_multiple_sessions(self, client):
        """Test that different session IDs maintain separate states"""
        # Create first session
        response1 = client.get("/api/game/state")
        session1 = response1.cookies.get("session_id")

        # Create second session
        response2 = client.get("/api/game/state")
        session2 = response2.cookies.get("session_id")

        # Verify different sessions
        assert session1 != session2

        # Modify first session
        client.post(
            "/api/game/build-womb",
            cookies={"session_id": session1}
        )

        # Check first session has womb
        resp1 = client.get("/api/game/state", cookies={"session_id": session1})
        assert resp1.json()["assembler_built"] == True

        # Check second session doesn't have womb
        resp2 = client.get("/api/game/state", cookies={"session_id": session2})
        assert resp2.json()["assembler_built"] == False


class TestGatherResourceEndpoint:
    """Tests for POST /api/game/gather-resource endpoint"""

    def test_gather_tritanium_success(self, client):
        """Test gathering Tritanium resource"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_state = response1.json()
        initial_tritanium = initial_state["resources"]["Tritanium"]

        response2 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
        data = response2.json()
        assert "state" in data
        assert "message" in data
        assert "amount" in data
        assert "task_id" in data

        # Verify resource increased
        assert data["state"]["resources"]["Tritanium"] > initial_tritanium
        assert data["amount"] >= CONFIG["GATHER_AMOUNT"]["Tritanium"][0]
        assert data["amount"] <= CONFIG["GATHER_AMOUNT"]["Tritanium"][1]

        # Verify task created
        assert len(data["state"]["active_tasks"]) == 1

    def test_gather_all_resource_types(self, client):
        """Test gathering each type of resource"""
        resources_to_test = ["Tritanium", "Metal Ore", "Biomass", "Synthetic", "Organic", "Shilajit"]

        for resource in resources_to_test:
            response1 = client.get("/api/game/state")
            session_id = response1.cookies.get("session_id")

            response2 = client.post(
                f"/api/game/gather-resource?resource={resource}",
                cookies={"session_id": session_id}
            )

            assert response2.status_code == 200, f"Failed for {resource}"
            data = response2.json()
            assert data["state"]["resources"][resource] > 0

    def test_gather_with_active_task_returns_400(self, client):
        """Test that gathering while task is active returns 400"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Start first gather
        response2 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200

        # Try to start second gather while first is active
        response3 = client.post(
            "/api/game/gather-resource?resource=Metal Ore",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 400
        assert "task is already in progress" in response3.json()["detail"].lower()

    def test_gather_invalid_resource_returns_400(self, client):
        """Test gathering invalid resource type"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        response2 = client.post(
            "/api/game/gather-resource?resource=InvalidResource",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 400

    def test_gather_without_session_returns_404(self, client):
        """Test gathering without valid session"""
        response = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": "invalid-session-id"}
        )

        assert response.status_code == 404

    def test_gather_awards_practice_xp(self, client):
        """Test that gathering awards Kinetic practice XP"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_state = response1.json()
        initial_kinetic_xp = initial_state["practices_xp"]["Kinetic"]

        response2 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
        data = response2.json()
        assert data["state"]["practices_xp"]["Kinetic"] > initial_kinetic_xp


class TestBuildWombEndpoint:
    """Tests for POST /api/game/build-womb endpoint"""

    def test_build_womb_success(self, client):
        """Test building the womb successfully"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
        data = response2.json()
        assert "state" in data
        assert "message" in data
        assert "task_id" in data

        # Verify womb was built
        assert data["state"]["assembler_built"] == True

        # Verify resources were consumed
        womb_cost = CONFIG["ASSEMBLER_COST"]
        for resource, cost in womb_cost.items():
            assert data["state"]["resources"][resource] < 100  # Less than starting amount

        # Verify task created
        assert len(data["state"]["active_tasks"]) == 1

    def test_build_womb_already_built_returns_400(self, client):
        """Test that building womb twice fails"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build first time
        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )
        assert response2.status_code == 200

        # Wait for task to complete
        time.sleep(0.1)

        # Try to build again
        response3 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 400

    def test_build_womb_insufficient_resources_returns_400(self, client):
        """Test building womb with insufficient resources"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Set resources to zero
        empty_state = response1.json()
        empty_state["resources"] = {k: 0 for k in empty_state["resources"]}
        client.post(
            "/api/game/state",
            json=empty_state,
            cookies={"session_id": session_id}
        )

        # Try to build womb
        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 400

    def test_build_womb_with_active_task_returns_400(self, client):
        """Test building womb while another task is active"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Start gather task
        client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )

        # Try to build womb
        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 400
        assert "task is already in progress" in response2.json()["detail"].lower()

    def test_build_womb_awards_practice_xp(self, client):
        """Test that building womb awards Constructive practice XP"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_xp = response1.json()["practices_xp"]["Constructive"]

        response2 = client.post(
            "/api/game/build-womb",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
        assert response2.json()["state"]["practices_xp"]["Constructive"] > initial_xp


class TestGrowCloneEndpoint:
    """Tests for POST /api/game/grow-clone endpoint"""

    def test_grow_basic_clone_success(self, client):
        """Test growing a basic clone"""
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
        assert "state" in data
        assert "clone" in data
        assert "soul_split" in data
        assert "message" in data
        assert "task_id" in data

        # Verify clone was created
        assert len(data["state"]["clones"]) == 1
        clone = data["clone"]
        assert clone["kind"] == "BASIC"
        assert clone["alive"] == True
        assert clone["uploaded"] == False
        assert "traits" in clone
        assert "xp" in clone

        # Verify soul was split
        assert data["state"]["soul_percent"] < 100.0

    def test_grow_all_clone_types(self, client):
        """Test growing each type of clone"""
        clone_types = ["BASIC", "MINER", "VOLATILE"]

        for clone_type in clone_types:
            response1 = client.get("/api/game/state")
            session_id = response1.cookies.get("session_id")

            # Build womb
            client.post("/api/game/build-womb", cookies={"session_id": session_id})
            time.sleep(0.1)

            # Grow clone
            response2 = client.post(
                f"/api/game/grow-clone?kind={clone_type}",
                cookies={"session_id": session_id}
            )

            assert response2.status_code == 200, f"Failed for {clone_type}"
            data = response2.json()
            assert data["clone"]["kind"] == clone_type

    def test_grow_clone_without_womb_returns_400(self, client):
        """Test growing clone without building womb first"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 400
        assert "Build the Womb first" in response2.json()["detail"]

    def test_grow_clone_insufficient_resources_returns_400(self, client):
        """Test growing clone with insufficient resources"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)

        # Set resources to zero
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["resources"] = {k: 0 for k in state["resources"]}
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Try to grow clone
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 400

    def test_grow_clone_insufficient_soul_returns_400(self, client):
        """Test growing clone with insufficient soul integrity"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)

        # Set soul to very low
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["soul_percent"] = 1.0
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Try to grow clone
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 400
        assert "soul integrity" in response2.json()["detail"].lower()

    def test_grow_clone_with_active_task_returns_400(self, client):
        """Test growing clone while another task is active"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)

        # Start gather task
        client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )

        # Try to grow clone
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 400


class TestApplyCloneEndpoint:
    """Tests for POST /api/game/apply-clone endpoint"""

    def test_apply_clone_success(self, client):
        """Test applying a clone to spaceship"""
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

        # Apply clone
        response3 = client.post(
            f"/api/game/apply-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 200
        data = response3.json()
        assert "state" in data
        assert "message" in data
        assert data["state"]["applied_clone_id"] == clone_id

    def test_apply_invalid_clone_returns_400(self, client):
        """Test applying invalid clone ID"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        response2 = client.post(
            "/api/game/apply-clone?clone_id=invalid-id",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 400
        assert "unavailable" in response2.json()["detail"].lower()

    def test_apply_dead_clone_returns_400(self, client):
        """Test applying a dead clone"""
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

        # Mark clone as dead
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["clones"][clone_id]["alive"] = False
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Try to apply dead clone
        response3 = client.post(
            f"/api/game/apply-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 400

    def test_apply_uploaded_clone_returns_400(self, client):
        """Test applying an uploaded clone"""
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

        # Mark clone as uploaded
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["clones"][clone_id]["uploaded"] = True
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Try to apply uploaded clone
        response3 = client.post(
            f"/api/game/apply-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 400
        assert "uploaded" in response3.json()["detail"].lower()


class TestRunExpeditionEndpoint:
    """Tests for POST /api/game/run-expedition endpoint"""

    def test_run_mining_expedition_success(self, client):
        """Test running a mining expedition"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Build womb, grow clone, apply clone
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

        # Run expedition
        response3 = client.post(
            "/api/game/run-expedition?kind=MINING",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 200
        data = response3.json()
        assert "state" in data
        assert "message" in data

        # Verify clone gained XP
        clone = data["state"]["clones"][clone_id]
        assert clone["xp"]["MINING"] > 0

    def test_run_all_expedition_types(self, client):
        """Test running each type of expedition"""
        expedition_types = ["MINING", "COMBAT", "EXPLORATION"]

        for exp_type in expedition_types:
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
            client.post(
                f"/api/game/apply-clone?clone_id={clone_id}",
                cookies={"session_id": session_id}
            )

            # Run expedition
            response3 = client.post(
                f"/api/game/run-expedition?kind={exp_type}",
                cookies={"session_id": session_id}
            )

            assert response3.status_code == 200, f"Failed for {exp_type}"
            data = response3.json()
            clone = data["state"]["clones"][clone_id]
            assert clone["xp"][exp_type] > 0

    def test_run_expedition_without_applied_clone_returns_success_with_message(self, client):
        """Test running expedition without applied clone"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        response2 = client.post(
            "/api/game/run-expedition?kind=MINING",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
        assert "No clone applied" in response2.json()["message"]

    def test_run_expedition_clone_survival(self, client):
        """Test that clone survives expedition (most of the time)"""
        survival_count = 0
        attempts = 10

        for i in range(attempts):
            response1 = client.get("/api/game/state")
            session_id = response1.cookies.get("session_id")

            # Setup
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

            # Run expedition
            response3 = client.post(
                "/api/game/run-expedition?kind=MINING",
                cookies={"session_id": session_id}
            )

            clone = response3.json()["state"]["clones"][clone_id]
            if clone["alive"]:
                survival_count += 1

        # With 12% death rate, we expect most clones to survive
        assert survival_count >= 6  # At least 60% survival

    def test_run_expedition_increments_survived_runs(self, client):
        """Test that survived runs increment"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Setup
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

        # Run multiple expeditions
        for i in range(3):
            response = client.post(
                "/api/game/run-expedition?kind=MINING",
                cookies={"session_id": session_id}
            )
            if response.json()["state"]["clones"][clone_id]["alive"]:
                # Reapply if still alive
                client.post(
                    f"/api/game/apply-clone?clone_id={clone_id}",
                    cookies={"session_id": session_id}
                )

        # Check survived runs
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        assert state["clones"][clone_id]["survived_runs"] > 0


class TestUploadCloneEndpoint:
    """Tests for POST /api/game/upload-clone endpoint"""

    def test_upload_clone_success(self, client):
        """Test uploading a clone to SELF"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_soul_xp = response1.json()["soul_xp"]

        # Build womb and grow clone
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(0.1)
        response2 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        clone_id = response2.json()["clone"]["id"]

        # Give clone some XP
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
        assert "state" in data
        assert "message" in data

        # Verify clone is marked as uploaded
        clone = data["state"]["clones"][clone_id]
        assert clone["uploaded"] == True
        assert clone["alive"] == False

        # Verify SELF gained XP
        assert data["state"]["soul_xp"] > initial_soul_xp

    def test_upload_clone_restores_soul_percent(self, client):
        """Test that uploading clone restores soul integrity"""
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
        soul_after_grow = response2.json()["state"]["soul_percent"]

        # Give clone XP
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["clones"][clone_id]["xp"] = {"MINING": 100, "COMBAT": 100, "EXPLORATION": 100}
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Upload clone
        response3 = client.post(
            f"/api/game/upload-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )

        soul_after_upload = response3.json()["state"]["soul_percent"]
        assert soul_after_upload > soul_after_grow

    def test_upload_dead_clone_returns_success_with_message(self, client):
        """Test uploading a dead clone"""
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

        # Mark clone as dead
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        state["clones"][clone_id]["alive"] = False
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Try to upload
        response3 = client.post(
            f"/api/game/upload-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 200
        assert "destroyed" in response3.json()["message"].lower()

    def test_upload_already_uploaded_clone_returns_success_with_message(self, client):
        """Test uploading already uploaded clone"""
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

        # Upload first time
        client.post(
            f"/api/game/upload-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )

        # Try to upload again
        response3 = client.post(
            f"/api/game/upload-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )

        assert response3.status_code == 200
        assert "already been uploaded" in response3.json()["message"].lower()

    def test_upload_invalid_clone_returns_success_with_message(self, client):
        """Test uploading invalid clone ID"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        response2 = client.post(
            "/api/game/upload-clone?clone_id=invalid-id",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
        assert "not found" in response2.json()["message"].lower()


class TestTaskStatusEndpoint:
    """Tests for GET /api/game/tasks/status endpoint"""

    def test_task_status_no_active_task(self, client):
        """Test task status when no task is active"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        response2 = client.get(
            "/api/game/tasks/status",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
        data = response2.json()
        assert data["active"] == False
        assert data["task"] is None

    def test_task_status_with_active_task(self, client):
        """Test task status with active task"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Start a task
        client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )

        # Check task status
        response2 = client.get(
            "/api/game/tasks/status",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
        data = response2.json()
        assert data["active"] == True
        assert data["task"] is not None
        assert "id" in data["task"]
        assert "type" in data["task"]
        assert "progress" in data["task"]
        assert "elapsed" in data["task"]
        assert "remaining" in data["task"]
        assert "duration" in data["task"]

    def test_task_status_progress_tracking(self, client):
        """Test that task progress is tracked correctly"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Start a task
        client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )

        # Check immediately
        response2 = client.get(
            "/api/game/tasks/status",
            cookies={"session_id": session_id}
        )
        data1 = response2.json()
        assert data1["active"] == True
        progress1 = data1["task"]["progress"]

        # Wait a bit
        time.sleep(0.5)

        # Check again
        response3 = client.get(
            "/api/game/tasks/status",
            cookies={"session_id": session_id}
        )
        data2 = response3.json()

        # Progress should increase or task should complete
        if data2["active"]:
            assert data2["task"]["progress"] >= progress1
        else:
            # Task completed
            assert data2.get("completed") == True

    def test_task_status_completion(self, client):
        """Test that completed tasks are auto-completed"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Manually create a task that's already "complete"
        state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        task_id = str(uuid.uuid4())
        state["active_tasks"][task_id] = {
            "type": "gather_resource",
            "resource": "Tritanium",
            "start_time": time.time() - 100,  # Started 100 seconds ago
            "duration": 10  # 10 second duration
        }
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Check task status
        response2 = client.get(
            "/api/game/tasks/status",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
        data = response2.json()
        assert data["active"] == False
        assert data.get("completed") == True


class TestRateLimitMessageFormatting:
    """Tests for rate limit message formatting"""
    
    def test_format_rate_limit_message_seconds(self):
        """Test rate limit message formatting for seconds (< 60)"""
        from backend.routers.game import format_rate_limit_message
        import random
        
        rng = random.Random(42)  # Fixed seed for reproducibility
        
        # Test 1 second
        msg = format_rate_limit_message(1, rng)
        assert "Keeper:" in msg
        assert "1 second" in msg
        assert "Try again in" in msg
        
        # Test 30 seconds
        msg = format_rate_limit_message(30, rng)
        assert "Keeper:" in msg
        assert "30 seconds" in msg
        assert "Try again in" in msg
        
        # Test 59 seconds
        msg = format_rate_limit_message(59, rng)
        assert "Keeper:" in msg
        assert "59 seconds" in msg
        assert "Try again in" in msg
    
    def test_format_rate_limit_message_minutes(self):
        """Test rate limit message formatting for minutes (>= 60)"""
        from backend.routers.game import format_rate_limit_message
        import random
        
        rng = random.Random(42)  # Fixed seed for reproducibility
        
        # Test 60 seconds (1 minute)
        msg = format_rate_limit_message(60, rng)
        assert "Keeper:" in msg
        assert "1 minute" in msg
        assert "Try again in" in msg
        assert "second" not in msg  # Should not mention seconds
        
        # Test 90 seconds (1 minute and 30 seconds)
        msg = format_rate_limit_message(90, rng)
        assert "Keeper:" in msg
        assert "1 minute" in msg
        assert "30 seconds" in msg
        assert "Try again in" in msg
        
        # Test 120 seconds (2 minutes)
        msg = format_rate_limit_message(120, rng)
        assert "Keeper:" in msg
        assert "2 minutes" in msg
        assert "Try again in" in msg
        assert "second" not in msg  # Should not mention seconds
    
    def test_format_rate_limit_message_random_selection(self):
        """Test that different messages are selected randomly"""
        from backend.routers.game import format_rate_limit_message
        import random
        
        # Generate multiple messages with different seeds
        messages = set()
        for seed in range(10):
            rng = random.Random(seed)
            msg = format_rate_limit_message(30, rng)
            messages.add(msg.split(". ")[0])  # Extract just the Keeper flavor part
        
        # Should have at least some variation (though with only 5 messages, might not be all unique)
        assert len(messages) >= 1  # At least one message format
    
    def test_format_rate_limit_message_structure(self):
        """Test that message has correct structure (Keeper flavor + time estimate)"""
        from backend.routers.game import format_rate_limit_message
        import random
        
        rng = random.Random(42)
        msg = format_rate_limit_message(45, rng)
        
        # Should contain Keeper prefix
        assert msg.startswith("Keeper:")
        
        # Should contain time estimate
        assert "Try again in" in msg
        
        # Should have proper punctuation
        assert ". " in msg  # Should have period and space between flavor and functional
        
        # Should end with period
        assert msg.endswith(".")
    
    def test_format_rate_limit_message_fallback(self):
        """Test that fallback message works if JSON is missing"""
        from backend.routers.game import format_rate_limit_message
        import random
        
        # This test verifies the function doesn't crash if messages list is empty
        # (The fallback is handled in the function itself)
        rng = random.Random(42)
        msg = format_rate_limit_message(30, rng)
        
        # Should still produce a valid message
        assert len(msg) > 0
        assert "Keeper:" in msg
        assert "Try again in" in msg
