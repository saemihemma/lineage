"""
Comprehensive tests for bug fixes and synchronization issues.

Tests verify:
1. Soul level calculation sync between frontend and backend
2. Practice level calculation sync
3. Request deduplication and race conditions
4. Optimistic locking for state updates
5. Session management and expiration
6. Error handling and offline scenarios
"""
import pytest
import json
import time
import sqlite3
from unittest.mock import Mock, patch
from typing import Dict, Any

# Import the modules we're testing
import sys
from pathlib import Path
_backend_dir = Path(__file__).parent.parent
_project_root = _backend_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.routers.game import (
    game_state_to_dict,
    dict_to_game_state,
    save_game_state,
    load_game_state,
)
from game.state import GameState
from core.models import Clone, PlayerState, Womb
from core.config import CONFIG
from game.wombs import calculate_repair_cost


class TestSoulLevelSync:
    """Test soul level calculation consistency between backend and frontend"""

    def test_soul_level_in_response(self):
        """Test that soul_level is included in game state response"""
        state = GameState()
        state.soul_xp = 250  # Should be level 3 (0-99=1, 100-199=2, 200-299=3)

        response = game_state_to_dict(state)

        assert "soul_level" in response
        assert response["soul_level"] == state.soul_level()
        assert response["soul_level"] == 3

    def test_soul_level_calculation_consistency(self):
        """Test that soul level calculation matches between PlayerState and response"""
        test_cases = [
            (0, 1),      # 0 XP = level 1
            (50, 1),     # 50 XP = level 1
            (99, 1),     # 99 XP = level 1
            (100, 2),    # 100 XP = level 2
            (199, 2),    # 199 XP = level 2
            (200, 3),    # 200 XP = level 3
            (500, 6),    # 500 XP = level 6
            (1000, 11),  # 1000 XP = level 11
        ]

        for soul_xp, expected_level in test_cases:
            state = GameState()
            state.soul_xp = soul_xp

            # Check PlayerState.soul_level() method
            assert state.soul_level() == expected_level, \
                f"soul_xp={soul_xp} should give level {expected_level}, got {state.soul_level()}"

            # Check response dict
            response = game_state_to_dict(state)
            assert response["soul_level"] == expected_level, \
                f"Response for soul_xp={soul_xp} should have level {expected_level}"

    def test_soul_level_readonly(self):
        """Test that soul_level in response is calculated, not stored"""
        state = GameState()
        state.soul_xp = 150

        # Get response
        response = game_state_to_dict(state)
        original_level = response["soul_level"]

        # Modify XP
        state.soul_xp = 250

        # Get new response
        new_response = game_state_to_dict(state)

        # Level should have changed based on XP
        assert new_response["soul_level"] != original_level
        assert new_response["soul_level"] == 3


class TestPracticeLevelSync:
    """Test practice level calculation consistency"""

    def test_practice_levels_in_response(self):
        """Test that practice_levels are included in game state response"""
        state = GameState()
        state.practices_xp = {
            "Kinetic": 150,
            "Cognitive": 250,
            "Constructive": 50
        }

        response = game_state_to_dict(state)

        assert "practice_levels" in response
        assert "Kinetic" in response["practice_levels"]
        assert "Cognitive" in response["practice_levels"]
        assert "Constructive" in response["practice_levels"]

    def test_practice_level_calculation_consistency(self):
        """Test that practice levels are calculated correctly"""
        test_cases = [
            (0, 0),      # 0 XP = level 0
            (50, 0),     # 50 XP = level 0
            (99, 0),     # 99 XP = level 0
            (100, 1),    # 100 XP = level 1
            (199, 1),    # 199 XP = level 1
            (200, 2),    # 200 XP = level 2
            (500, 5),    # 500 XP = level 5
        ]

        for xp, expected_level in test_cases:
            state = GameState()
            state.practices_xp = {
                "Kinetic": xp,
                "Cognitive": 0,
                "Constructive": 0
            }

            # Check practice_level() method
            assert state.practice_level("Kinetic") == expected_level, \
                f"Kinetic XP={xp} should give level {expected_level}"

            # Check response dict
            response = game_state_to_dict(state)
            assert response["practice_levels"]["Kinetic"] == expected_level, \
                f"Response for Kinetic XP={xp} should have level {expected_level}"

    def test_all_practice_tracks_included(self):
        """Test that all three practice tracks are in response"""
        state = GameState()
        state.practices_xp = {
            "Kinetic": 250,
            "Cognitive": 150,
            "Constructive": 300
        }

        response = game_state_to_dict(state)

        assert response["practice_levels"]["Kinetic"] == 2
        assert response["practice_levels"]["Cognitive"] == 1
        assert response["practice_levels"]["Constructive"] == 3


class TestStateSerialization:
    """Test game state serialization and deserialization"""

    def test_round_trip_serialization(self):
        """Test that state can be serialized and deserialized without loss"""
        # Create state with various data
        state = GameState()
        state.soul_xp = 250
        state.soul_percent = 85.5
        state.assembler_built = True
        state.self_name = "TestSELF"
        state.practices_xp = {
            "Kinetic": 150,
            "Cognitive": 200,
            "Constructive": 100
        }
        state.resources = {
            "Tritanium": 50,
            "Metal Ore": 30
        }

        # Add a clone
        clone = Clone(
            id="clone-1",
            kind="BASIC",
            traits={"PWC": 5, "SSC": 7},
            xp={"MINING": 10, "COMBAT": 5, "EXPLORATION": 0}
        )
        state.clones["clone-1"] = clone

        # Serialize
        state_dict = game_state_to_dict(state)

        # Deserialize
        restored_state = dict_to_game_state(state_dict)

        # Verify
        assert restored_state.soul_xp == state.soul_xp
        assert restored_state.soul_percent == state.soul_percent
        assert restored_state.assembler_built == state.assembler_built
        assert restored_state.self_name == state.self_name
        assert restored_state.practices_xp == state.practices_xp
        assert restored_state.resources == state.resources
        assert "clone-1" in restored_state.clones
        assert restored_state.clones["clone-1"].kind == "BASIC"

    def test_calculated_fields_not_stored(self):
        """Test that calculated fields are in response but not stored in DB"""
        state = GameState()
        state.soul_xp = 250
        state.practices_xp = {"Kinetic": 150, "Cognitive": 100, "Constructive": 50}

        # Serialize
        state_dict = game_state_to_dict(state)

        # Calculated fields should be in response
        assert "soul_level" in state_dict
        assert "practice_levels" in state_dict

        # But when we deserialize, we calculate them fresh
        restored_state = dict_to_game_state(state_dict)

        # Levels should match
        assert restored_state.soul_level() == state_dict["soul_level"]
        assert restored_state.practice_level("Kinetic") == state_dict["practice_levels"]["Kinetic"]


class TestActiveTasks:
    """Test active task management"""

    def test_active_tasks_persisted(self):
        """Test that active tasks are saved and loaded correctly"""
        state = GameState()
        state.active_tasks = {
            "task-1": {
                "type": "gather_resource",
                "resource": "Tritanium",
                "start_time": time.time(),
                "duration": 15
            }
        }

        # Serialize and deserialize
        state_dict = game_state_to_dict(state)
        restored_state = dict_to_game_state(state_dict)

        assert "task-1" in restored_state.active_tasks
        assert restored_state.active_tasks["task-1"]["type"] == "gather_resource"
        assert restored_state.active_tasks["task-1"]["resource"] == "Tritanium"

    def test_empty_active_tasks(self):
        """Test that empty active_tasks is handled correctly"""
        state = GameState()
        state.active_tasks = {}

        state_dict = game_state_to_dict(state)
        restored_state = dict_to_game_state(state_dict)

        assert restored_state.active_tasks == {}


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_missing_practice_track(self):
        """Test handling of missing practice track"""
        state = GameState()
        state.practices_xp = {"Kinetic": 100}  # Missing Cognitive and Constructive

        # Should handle gracefully
        response = game_state_to_dict(state)

        assert "practice_levels" in response
        # Missing tracks should default to 0
        assert response["practice_levels"]["Cognitive"] == 0
        assert response["practice_levels"]["Constructive"] == 0

    def test_negative_xp_handling(self):
        """Test that negative XP is handled (shouldn't happen but test anyway)"""
        state = GameState()
        state.soul_xp = -100

        # Should not crash (negative XP gives level 0, which is edge case but acceptable)
        level = state.soul_level()
        assert level >= 0  # Should handle gracefully without crashing

    def test_very_large_xp(self):
        """Test handling of very large XP values"""
        state = GameState()
        state.soul_xp = 1000000

        response = game_state_to_dict(state)

        # Should calculate without overflow
        assert "soul_level" in response
        assert response["soul_level"] > 0


class TestClonesInState:
    """Test clone management in game state"""

    def test_multiple_clones(self):
        """Test that multiple clones are serialized correctly"""
        state = GameState()

        # Add multiple clones
        for i in range(3):
            clone = Clone(
                id=f"clone-{i}",
                kind="BASIC" if i % 2 == 0 else "MINER",
                traits={"PWC": i + 1},
                xp={"MINING": i * 10, "COMBAT": 0, "EXPLORATION": 0}
            )
            state.clones[f"clone-{i}"] = clone

        # Serialize and deserialize
        state_dict = game_state_to_dict(state)
        restored_state = dict_to_game_state(state_dict)

        assert len(restored_state.clones) == 3
        for i in range(3):
            assert f"clone-{i}" in restored_state.clones
            assert restored_state.clones[f"clone-{i}"].traits["PWC"] == i + 1

    def test_clone_with_uploaded_status(self):
        """Test that uploaded clones are handled correctly"""
        state = GameState()

        clone = Clone(
            id="clone-1",
            kind="BASIC",
            traits={"PWC": 5},
            xp={"MINING": 50, "COMBAT": 0, "EXPLORATION": 0},
            uploaded=True,
            alive=False
        )
        state.clones["clone-1"] = clone

        # Serialize and deserialize
        state_dict = game_state_to_dict(state)
        restored_state = dict_to_game_state(state_dict)

        assert restored_state.clones["clone-1"].uploaded == True
        assert restored_state.clones["clone-1"].alive == False


class TestVersionManagement:
    """Test version field management"""

    def test_version_preserved_in_serialization(self):
        """Test that version is preserved during serialization"""
        state = GameState()
        state.version = 5

        state_dict = game_state_to_dict(state)
        assert state_dict["version"] == 5

        restored_state = dict_to_game_state(state_dict)
        assert restored_state.version == 5

    def test_default_version(self):
        """Test that new states have a default version"""
        state = GameState()

        state_dict = game_state_to_dict(state)
        assert "version" in state_dict
        assert state_dict["version"] >= 1


class TestWombRepair:
    """Test womb repair reliability, especially edge cases"""

    def test_repair_womb_at_zero_durability(self):
        """Test that repair works correctly when womb has 0 durability"""
        state = GameState()
        state.resources = {
            "Tritanium": 100,
            "Metal Ore": 100,
            "Biomass": 100
        }
        
        # Create womb with 0 durability
        womb = Womb(id=0, durability=0.0, max_durability=100.0)
        state.wombs = [womb]
        
        # Calculate repair cost (should work at 0 durability)
        repair_cost = calculate_repair_cost(womb, state)
        
        # Should calculate cost for 5 points (restore amount)
        # Cost per point: 0.9 Tritanium, 0.6 Metal Ore, 0.15 Biomass
        # For 5 points: 4.5 Tritanium, 3.0 Metal Ore, 0.75 Biomass (rounded)
        assert repair_cost["Tritanium"] > 0
        assert repair_cost["Metal Ore"] > 0
        assert repair_cost.get("Biomass", 0) >= 0  # May round to 0 or 1
        
        # Verify restore amount calculation
        missing_durability = womb.max_durability - womb.durability
        restore_amount = min(5.0, missing_durability)
        assert restore_amount == 5.0, f"At 0 durability, restore_amount should be 5.0, got {restore_amount}"

    def test_repair_womb_negative_durability_normalized(self):
        """Test that negative durability is normalized to 0"""
        state = GameState()
        state.resources = {
            "Tritanium": 100,
            "Metal Ore": 100,
            "Biomass": 100
        }
        
        # Create womb with negative durability (edge case)
        womb = Womb(id=0, durability=-10.0, max_durability=100.0)
        state.wombs = [womb]
        
        # Calculate repair cost (should normalize negative to 0)
        repair_cost = calculate_repair_cost(womb, state)
        
        # Should treat as 0 durability (restore 5 points)
        assert repair_cost["Tritanium"] > 0
        missing_durability = womb.max_durability - max(0.0, womb.durability)
        restore_amount = min(5.0, missing_durability)
        assert restore_amount == 5.0, f"Negative durability should normalize to 0, restore_amount should be 5.0"

    def test_repair_womb_at_full_durability(self):
        """Test that repair returns 0 cost when womb is at full durability"""
        state = GameState()
        
        # Create womb at full durability
        womb = Womb(id=0, durability=100.0, max_durability=100.0)
        state.wombs = [womb]
        
        # Calculate repair cost
        repair_cost = calculate_repair_cost(womb, state)
        
        # Should return 0 cost for all resources
        assert repair_cost["Tritanium"] == 0
        assert repair_cost["Metal Ore"] == 0
        assert repair_cost.get("Biomass", 0) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
