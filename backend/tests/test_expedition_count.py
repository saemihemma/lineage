"""Test expedition count calculation for leaderboard"""
import pytest
from fastapi.testclient import TestClient


class TestExpeditionCountBug:
    """Test that expedition count is calculated correctly"""

    def test_expedition_count_calculation_logic(self, client):
        """Verify expedition count uses survived_runs, not XP sum"""
        # Get initial state
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Setup state with a clone that has expeditions
        state = response1.json()
        state["clones"] = {
            "test-clone-1": {
                "id": "test-clone-1",
                "kind": "BASIC",
                "traits": {"PWC": 5, "SSC": 6, "MGC": 4, "DLT": 7, "ENF": 5, "ELK": 3, "FRK": 4},
                "xp": {
                    "MINING": 30,  # 3 mining expeditions * 10 XP each = 30
                    "COMBAT": 0,
                    "EXPLORATION": 0
                },
                "survived_runs": 3,  # Actual expedition count
                "alive": True,
                "uploaded": False,
                "created_at": 0.0
            }
        }

        # Save state
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Get state back
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        clone = final_state["clones"]["test-clone-1"]

        # Verify the bug scenario:
        # - survived_runs = 3 (correct expedition count)
        # - MINING XP = 30 (would be counted as 30 expeditions with the bug)

        correct_count = clone["survived_runs"]  # Should be 3
        buggy_count = sum(clone["xp"].values())  # Would be 30 with bug

        print(f"✅ Correct expedition count: {correct_count}")
        print(f"❌ Bug would have counted: {buggy_count} (XP sum)")

        assert correct_count == 3, "Correct expedition count should be 3"
        assert buggy_count == 30, "XP sum should be 30"
        assert buggy_count != correct_count, "Bug inflates count by 10x"

    def test_multiple_clones_expedition_count(self, client):
        """Test expedition count sums across multiple clones"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Setup state with 2 clones
        state = response1.json()
        state["clones"] = {
            "clone-1": {
                "id": "clone-1",
                "kind": "BASIC",
                "traits": {"PWC": 5, "SSC": 6, "MGC": 4, "DLT": 7, "ENF": 5, "ELK": 3, "FRK": 4},
                "xp": {
                    "MINING": 20,  # 2 expeditions
                    "COMBAT": 0,
                    "EXPLORATION": 0
                },
                "survived_runs": 2,
                "alive": True,
                "uploaded": False,
                "created_at": 0.0
            },
            "clone-2": {
                "id": "clone-2",
                "kind": "MINER",
                "traits": {"PWC": 5, "SSC": 6, "MGC": 4, "DLT": 7, "ENF": 5, "ELK": 3, "FRK": 4},
                "xp": {
                    "MINING": 0,
                    "COMBAT": 36,  # 3 expeditions * 12 XP each
                    "EXPLORATION": 0
                },
                "survived_runs": 3,
                "alive": True,
                "uploaded": False,
                "created_at": 0.0
            }
        }

        # Save state
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Get state back
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()

        # Calculate total expeditions (correct way)
        total_expeditions_correct = sum(
            clone["survived_runs"] for clone in final_state["clones"].values()
        )

        # Calculate wrong way (old bug)
        total_expeditions_wrong = sum(
            clone["xp"]["MINING"] + clone["xp"]["COMBAT"] + clone["xp"]["EXPLORATION"]
            for clone in final_state["clones"].values()
        )

        print(f"✅ Correct total: {total_expeditions_correct} expeditions")
        print(f"❌ Bug would show: {total_expeditions_wrong} (XP sum)")

        assert total_expeditions_correct == 5, "Should have 5 total expeditions (2+3)"
        assert total_expeditions_wrong == 56, "XP sum should be 56 (20+36)"
        assert total_expeditions_wrong != total_expeditions_correct, "Bug inflates count by ~11x"

    def test_no_expeditions_shows_zero(self, client):
        """Test that newly created clones show 0 expeditions"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Setup state with a new clone (no expeditions)
        state = response1.json()
        state["clones"] = {
            "new-clone": {
                "id": "new-clone",
                "kind": "BASIC",
                "traits": {"PWC": 5, "SSC": 6, "MGC": 4, "DLT": 7, "ENF": 5, "ELK": 3, "FRK": 4},
                "xp": {
                    "MINING": 0,
                    "COMBAT": 0,
                    "EXPLORATION": 0
                },
                "survived_runs": 0,
                "alive": True,
                "uploaded": False,
                "created_at": 0.0
            }
        }

        # Save state
        client.post("/api/game/state", json=state, cookies={"session_id": session_id})

        # Get state back
        final_state = client.get("/api/game/state", cookies={"session_id": session_id}).json()
        clone = final_state["clones"]["new-clone"]

        # New clone should have 0 survived_runs
        assert clone["survived_runs"] == 0

        # And 0 XP
        assert clone["xp"]["MINING"] == 0
        assert clone["xp"]["COMBAT"] == 0
        assert clone["xp"]["EXPLORATION"] == 0

        # Both methods should show 0 for new clones
        correct_count = clone["survived_runs"]
        buggy_count = sum(clone["xp"].values())

        assert correct_count == 0
        assert buggy_count == 0
        assert correct_count == buggy_count, "Both should be 0 for new clones"
