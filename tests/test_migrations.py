#!/usr/bin/env python3
"""Tests for migration system"""
import unittest
import json
import tempfile
import os
from game.migrations.migrate import migrate, get_latest_version
from core.state_manager import save_state, load_state
from core.models import PlayerState


class TestMigrations(unittest.TestCase):
    """Test migration system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_save_file = "frontier_save.json"
    
    def tearDown(self):
        """Clean up test files"""
        test_save = os.path.join(self.temp_dir, self.original_save_file)
        if os.path.exists(test_save):
            os.remove(test_save)
    
    def test_get_latest_version(self):
        """Test that get_latest_version returns correct version"""
        version = get_latest_version()
        self.assertIsInstance(version, int)
        self.assertGreaterEqual(version, 1)
    
    def test_migrate_same_version(self):
        """Test that migrating same version returns unchanged state"""
        state = {"version": 1, "soul_percent": 100.0}
        result = migrate(state, 1, 1)
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["soul_percent"], 100.0)
    
    def test_migrate_pre_versioned_save(self):
        """Test that pre-versioned saves (version 0) migrate correctly"""
        # Simulate old save without version
        old_state = {
            "soul_percent": 75.5,
            "soul_xp": 150,
            "assembler_built": True,
            "resources": {"Tritanium": 100},
            "practices_xp": {"Kinetic": 50}
        }
        
        latest = get_latest_version()
        migrated = migrate(old_state, 0, latest)
        
        self.assertEqual(migrated["version"], latest)
        self.assertEqual(migrated["soul_percent"], 75.5)
        self.assertIn("self_name", migrated)
    
    def test_new_game_has_version(self):
        """Test that new PlayerState has version field"""
        p = PlayerState()
        self.assertEqual(p.version, 1)
    
    def test_save_load_preserves_version(self):
        """Test that save/load preserves version"""
        p = PlayerState()
        p.version = 1
        save_state(p)
        
        loaded = load_state()
        self.assertEqual(loaded.version, 1)

if __name__ == "__main__":
    unittest.main()

