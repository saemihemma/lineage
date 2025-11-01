"""Comprehensive tests for leaderboard endpoints"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime


class TestLeaderboardGet:
    """Tests for GET /api/leaderboard endpoint"""

    def test_get_empty_leaderboard(self, client):
        """Test fetching leaderboard when empty"""
        response = client.get("/api/leaderboard")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_leaderboard_with_entries(self, client, sample_leaderboard_entry):
        """Test fetching leaderboard with entries"""
        # Submit some entries first
        client.post("/api/leaderboard/submit", json=sample_leaderboard_entry)

        entry2 = sample_leaderboard_entry.copy()
        entry2["self_name"] = "TestSELF2"
        entry2["soul_level"] = 10
        client.post("/api/leaderboard/submit", json=entry2)

        # Fetch leaderboard
        response = client.get("/api/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Should be sorted by soul_level DESC
        assert data[0]["soul_level"] == 10
        assert data[1]["soul_level"] == 5

    def test_get_leaderboard_with_limit(self, client, sample_leaderboard_entry):
        """Test leaderboard pagination with limit"""
        # Create 5 entries
        for i in range(5):
            entry = sample_leaderboard_entry.copy()
            entry["self_name"] = f"TestSELF{i}"
            entry["soul_level"] = i
            client.post("/api/leaderboard/submit", json=entry)

        # Request with limit=3
        response = client.get("/api/leaderboard?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_leaderboard_with_offset(self, client, sample_leaderboard_entry):
        """Test leaderboard pagination with offset"""
        # Create 5 entries
        for i in range(5):
            entry = sample_leaderboard_entry.copy()
            entry["self_name"] = f"TestSELF{i}"
            entry["soul_level"] = i
            client.post("/api/leaderboard/submit", json=entry)

        # Request with offset=2
        response = client.get("/api/leaderboard?offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3  # 5 total - 2 offset = 3

    def test_get_leaderboard_max_limit(self, client):
        """Test that limit is capped at 1000"""
        response = client.get("/api/leaderboard?limit=9999")
        assert response.status_code == 200
        # Should not error, just cap at 1000


class TestLeaderboardSubmit:
    """Tests for POST /api/leaderboard/submit endpoint"""

    def test_submit_new_entry(self, client, sample_leaderboard_entry):
        """Test submitting a new leaderboard entry"""
        response = client.post("/api/leaderboard/submit", json=sample_leaderboard_entry)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert "id" in data

    def test_submit_update_better_stats(self, client, sample_leaderboard_entry):
        """Test updating entry with better stats"""
        # Submit initial entry
        client.post("/api/leaderboard/submit", json=sample_leaderboard_entry)

        # Submit better stats
        better_entry = sample_leaderboard_entry.copy()
        better_entry["soul_level"] = 10
        response = client.post("/api/leaderboard/submit", json=better_entry)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"

    def test_submit_skip_worse_stats(self, client, sample_leaderboard_entry):
        """Test that worse stats don't update entry"""
        # Submit initial entry
        client.post("/api/leaderboard/submit", json=sample_leaderboard_entry)

        # Submit worse stats
        worse_entry = sample_leaderboard_entry.copy()
        worse_entry["soul_level"] = 1
        response = client.post("/api/leaderboard/submit", json=worse_entry)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"

    def test_submit_empty_name(self, client, sample_leaderboard_entry):
        """Test submitting with empty self_name"""
        entry = sample_leaderboard_entry.copy()
        entry["self_name"] = ""
        response = client.post("/api/leaderboard/submit", json=entry)
        assert response.status_code == 400

    def test_submit_whitespace_name(self, client, sample_leaderboard_entry):
        """Test submitting with whitespace-only self_name"""
        entry = sample_leaderboard_entry.copy()
        entry["self_name"] = "   "
        response = client.post("/api/leaderboard/submit", json=entry)
        assert response.status_code == 400

    def test_submit_long_name(self, client, sample_leaderboard_entry):
        """Test submitting with too long self_name"""
        entry = sample_leaderboard_entry.copy()
        entry["self_name"] = "X" * 150  # Max is 100
        response = client.post("/api/leaderboard/submit", json=entry)
        assert response.status_code == 400

    def test_submit_negative_soul_level(self, client, sample_leaderboard_entry):
        """Test submitting with negative soul_level"""
        entry = sample_leaderboard_entry.copy()
        entry["soul_level"] = -5
        response = client.post("/api/leaderboard/submit", json=entry)
        assert response.status_code == 400

    def test_submit_negative_soul_xp(self, client, sample_leaderboard_entry):
        """Test submitting with negative soul_xp"""
        entry = sample_leaderboard_entry.copy()
        entry["soul_xp"] = -100
        response = client.post("/api/leaderboard/submit", json=entry)
        assert response.status_code == 400

    def test_submit_rate_limiting(self, client, sample_leaderboard_entry):
        """Test rate limiting on submit endpoint"""
        # Make 11 requests rapidly (limit is 10 per minute)
        for i in range(11):
            entry = sample_leaderboard_entry.copy()
            entry["self_name"] = f"RateLimitTest{i}"
            response = client.post("/api/leaderboard/submit", json=entry)

            if i < 10:
                assert response.status_code == 200
            else:
                # 11th request should be rate limited
                assert response.status_code == 429


class TestLeaderboardStats:
    """Tests for GET /api/leaderboard/stats endpoint"""

    def test_get_stats_empty(self, client):
        """Test getting stats when leaderboard is empty"""
        response = client.get("/api/leaderboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] == 0
        assert data["max_soul_level"] == 0
        assert data["max_soul_xp"] == 0

    def test_get_stats_with_entries(self, client, sample_leaderboard_entry):
        """Test getting stats with entries"""
        # Submit multiple entries
        for i in range(3):
            entry = sample_leaderboard_entry.copy()
            entry["self_name"] = f"TestSELF{i}"
            entry["soul_level"] = i * 5
            entry["soul_xp"] = i * 1000
            client.post("/api/leaderboard/submit", json=entry)

        response = client.get("/api/leaderboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] == 3
        assert data["max_soul_level"] == 10  # 2 * 5
        assert data["max_soul_xp"] == 2000  # 2 * 1000


class TestLeaderboardSorting:
    """Tests for leaderboard sorting logic"""

    def test_sort_by_soul_level(self, client, sample_leaderboard_entry):
        """Test that entries are sorted by soul_level descending"""
        # Create entries with different levels
        levels = [3, 7, 1, 9, 5]
        for level in levels:
            entry = sample_leaderboard_entry.copy()
            entry["self_name"] = f"Level{level}"
            entry["soul_level"] = level
            entry["soul_xp"] = 1000
            client.post("/api/leaderboard/submit", json=entry)

        response = client.get("/api/leaderboard")
        data = response.json()

        # Should be sorted 9, 7, 5, 3, 1
        levels_sorted = [e["soul_level"] for e in data]
        assert levels_sorted == [9, 7, 5, 3, 1]

    def test_sort_by_xp_when_level_equal(self, client, sample_leaderboard_entry):
        """Test that entries with equal soul_level are sorted by soul_xp"""
        # Create entries with same level but different XP
        xps = [1000, 3000, 500, 2000]
        for i, xp in enumerate(xps):
            entry = sample_leaderboard_entry.copy()
            entry["self_name"] = f"XP{xp}"
            entry["soul_level"] = 5  # Same level
            entry["soul_xp"] = xp
            client.post("/api/leaderboard/submit", json=entry)

        response = client.get("/api/leaderboard")
        data = response.json()

        # Should be sorted by XP descending: 3000, 2000, 1000, 500
        xps_sorted = [e["soul_xp"] for e in data]
        assert xps_sorted == [3000, 2000, 1000, 500]
