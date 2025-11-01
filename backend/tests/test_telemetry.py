"""Comprehensive tests for telemetry endpoints"""
import pytest
from fastapi.testclient import TestClient


class TestTelemetryUpload:
    """Tests for POST /api/telemetry endpoint"""

    def test_upload_single_event(self, client):
        """Test uploading a single telemetry event"""
        events = [
            {
                "session_id": "test-session",
                "event_type": "game_start",
                "data": {"version": "1.0.0"}
            }
        ]
        response = client.post("/api/telemetry", json=events)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 1
        assert data["total_received"] == 1

    def test_upload_multiple_events(self, client, sample_telemetry_events):
        """Test uploading multiple telemetry events"""
        response = client.post("/api/telemetry", json=sample_telemetry_events)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 2
        assert data["total_received"] == 2

    def test_upload_empty_list(self, client):
        """Test uploading empty event list"""
        response = client.post("/api/telemetry", json=[])
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 0

    def test_upload_too_many_events(self, client):
        """Test that uploading >100 events is rejected"""
        # Create 101 events
        events = [
            {
                "session_id": f"session-{i}",
                "event_type": "test_event",
                "data": {}
            }
            for i in range(101)
        ]
        response = client.post("/api/telemetry", json=events)
        assert response.status_code == 400

    def test_upload_with_custom_timestamp(self, client):
        """Test uploading event with custom timestamp"""
        events = [
            {
                "session_id": "test-session",
                "event_type": "test_event",
                "data": {"key": "value"},
                "timestamp": "2024-01-01T12:00:00"
            }
        ]
        response = client.post("/api/telemetry", json=events)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

    def test_upload_skips_invalid_events(self, client):
        """Test that invalid events are skipped but others are processed"""
        events = [
            {
                "session_id": "test-session",
                "event_type": "valid_event",
                "data": {"key": "value"}
            },
            {
                "session_id": "test-session",
                # Missing event_type
                "data": {"key": "value"}
            },
            {
                "session_id": "test-session",
                "event_type": "",  # Empty event type
                "data": {"key": "value"}
            },
            {
                "session_id": "test-session",
                "event_type": "another_valid_event",
                "data": {"key": "value"}
            }
        ]
        response = client.post("/api/telemetry", json=events)
        assert response.status_code == 200
        data = response.json()
        # Only 2 valid events should be inserted
        assert data["count"] == 2
        assert data["total_received"] == 4

    def test_upload_rate_limiting(self, client):
        """Test rate limiting on telemetry upload"""
        # Telemetry has higher limit (50 requests per minute)
        # Make 51 requests
        for i in range(51):
            events = [{"session_id": f"session-{i}", "event_type": "test", "data": {}}]
            response = client.post("/api/telemetry", json=events)

            if i < 50:
                assert response.status_code == 200
            else:
                # 51st request should be rate limited
                assert response.status_code == 429


class TestTelemetryStats:
    """Tests for GET /api/telemetry/stats endpoint"""

    def test_get_stats_empty(self, client):
        """Test getting stats when no telemetry data"""
        response = client.get("/api/telemetry/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 0
        assert data["top_event_types"] == []

    def test_get_stats_with_events(self, client, sample_telemetry_events):
        """Test getting stats with telemetry data"""
        # Upload some events
        client.post("/api/telemetry", json=sample_telemetry_events)

        response = client.get("/api/telemetry/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 2
        assert len(data["top_event_types"]) == 2

    def test_get_stats_top_event_types(self, client):
        """Test that top event types are correctly aggregated"""
        # Create events with different types
        events = []
        for i in range(5):
            events.append({
                "session_id": "test-session",
                "event_type": "event_A",
                "data": {}
            })
        for i in range(3):
            events.append({
                "session_id": "test-session",
                "event_type": "event_B",
                "data": {}
            })
        events.append({
            "session_id": "test-session",
            "event_type": "event_C",
            "data": {}
        })

        client.post("/api/telemetry", json=events)

        response = client.get("/api/telemetry/stats")
        data = response.json()

        # Should be sorted by count
        top_events = data["top_event_types"]
        assert top_events[0]["event_type"] == "event_A"
        assert top_events[0]["count"] == 5
        assert top_events[1]["event_type"] == "event_B"
        assert top_events[1]["count"] == 3
        assert top_events[2]["event_type"] == "event_C"
        assert top_events[2]["count"] == 1


class TestTelemetryDataStorage:
    """Tests for telemetry data storage and retrieval"""

    def test_event_data_json_storage(self, client):
        """Test that complex event data is stored correctly"""
        events = [
            {
                "session_id": "test-session",
                "event_type": "complex_event",
                "data": {
                    "nested": {
                        "key": "value",
                        "number": 123,
                        "array": [1, 2, 3]
                    },
                    "boolean": True,
                    "null_value": None
                }
            }
        ]
        response = client.post("/api/telemetry", json=events)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

    def test_event_with_missing_data_field(self, client):
        """Test uploading event without data field (should default to {})"""
        events = [
            {
                "session_id": "test-session",
                "event_type": "minimal_event"
                # No data field
            }
        ]
        response = client.post("/api/telemetry", json=events)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
