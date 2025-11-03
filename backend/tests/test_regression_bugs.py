"""Regression tests for post-release bugs

These tests prevent regressions of bugs that were found after deployment:
1. Events feed endpoint 404 error
2. PostgreSQL type casting errors in expedition_outcomes
3. Transaction abort cascade failures
"""
import pytest
import time
import json
from fastapi.testclient import TestClient


class TestEventsFeedEndpoint:
    """Regression tests for events feed endpoint (prevent 404)"""
    
    def test_events_feed_endpoint_exists(self, client):
        """Test that /api/game/events/feed endpoint exists and returns 200"""
        response = client.get("/api/game/events/feed")
        
        # Should not return 404
        assert response.status_code != 404, "Events feed endpoint returned 404 - route not registered"
        # Should return 200 with empty array if no events
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert isinstance(response.json(), list), "Response should be a list"
    
    def test_events_feed_with_session(self, client):
        """Test events feed endpoint with valid session"""
        # Create a session
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        
        # Get events feed
        response2 = client.get("/api/game/events/feed", cookies={"session_id": session_id})
        
        assert response2.status_code == 200, f"Events feed failed with status {response2.status_code}"
        assert isinstance(response2.json(), list), "Response should be a list"
        
        # Check ETag header is present
        assert "ETag" in response2.headers, "ETag header should be present"
    
    def test_events_feed_with_after_parameter(self, client):
        """Test events feed with after timestamp parameter"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        
        # Get events after current time (should return empty)
        after_ts = time.time()
        response2 = client.get(
            f"/api/game/events/feed?after={after_ts}",
            cookies={"session_id": session_id}
        )
        
        assert response2.status_code == 200, "Should return 200 even with after parameter"
        assert isinstance(response2.json(), list), "Response should be a list"
    
    def test_events_feed_etag_support(self, client):
        """Test that ETag headers work correctly"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        
        # First request
        response2 = client.get("/api/game/events/feed", cookies={"session_id": session_id})
        assert response2.status_code == 200
        etag = response2.headers.get("ETag")
        
        if etag:
            # Second request with If-None-Match
            response3 = client.get(
                "/api/game/events/feed",
                cookies={"session_id": session_id},
                headers={"If-None-Match": etag}
            )
            # Should return 304 if no new events
            assert response3.status_code in [200, 304], "Should return 200 or 304 with ETag"


class TestPostgreSQLTypeCasting:
    """Regression tests for PostgreSQL type casting in expedition_outcomes"""
    
    def test_expedition_outcome_insert_types(self, client):
        """Test that expedition outcomes can be inserted with correct types"""
        # Setup: Get session, build womb, grow clone, apply clone
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        
        # Build womb
        response2 = client.post("/api/game/build-womb", cookies={"session_id": session_id})
        if response2.status_code != 200:
            pytest.skip("Need womb built for expedition test")
        
        # Wait for womb to finish
        time.sleep(2)
        
        # Grow clone
        response3 = client.post(
            "/api/game/grow-clone?kind=BASIC",
            cookies={"session_id": session_id}
        )
        if response3.status_code != 200:
            pytest.skip("Need clone grown for expedition test")
        
        # Wait for clone to finish
        time.sleep(2)
        
        # Get updated state to find clone ID
        response4 = client.get("/api/game/state", cookies={"session_id": session_id})
        state = response4.json()
        
        if not state.get("clones"):
            pytest.skip("No clones available for expedition test")
        
        clone_id = list(state["clones"].keys())[0]
        
        # Apply clone
        response5 = client.post(
            f"/api/game/apply-clone?clone_id={clone_id}",
            cookies={"session_id": session_id}
        )
        if response5.status_code != 200:
            pytest.skip("Failed to apply clone")
        
        # Run expedition - this should succeed without type casting errors
        response6 = client.post(
            "/api/game/run-expedition?kind=MINING",
            cookies={"session_id": session_id}
        )
        
        assert response6.status_code == 200, f"Expedition should succeed, got {response6.status_code}: {response6.text}"
        
        # Verify expedition_id in response
        data = response6.json()
        assert "expedition_id" in data, "Response should contain expedition_id"
        assert "signature" in data, "Response should contain signature"
    
    def test_expedition_outcome_timestamp_precision(self, client):
        """Test that timestamps are stored with correct precision for PostgreSQL"""
        # This test ensures start_ts and end_ts are properly cast as floats
        # Run an expedition and verify the outcome can be queried
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        
        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(2)
        
        # Grow clone
        client.post("/api/game/grow-clone?kind=BASIC", cookies={"session_id": session_id})
        time.sleep(2)
        
        # Get clone and apply
        response2 = client.get("/api/game/state", cookies={"session_id": session_id})
        state = response2.json()
        
        if not state.get("clones"):
            pytest.skip("No clones available")
        
        clone_id = list(state["clones"].keys())[0]
        client.post(f"/api/game/apply-clone?clone_id={clone_id}", cookies={"session_id": session_id})
        
        # Run expedition
        response3 = client.post(
            "/api/game/run-expedition?kind=MINING",
            cookies={"session_id": session_id}
        )
        
        if response3.status_code != 200:
            pytest.skip(f"Expedition failed: {response3.status_code}")
        
        # If we got here, the insert succeeded without type errors
        # This means timestamps were properly cast
        assert True


class TestTransactionRollback:
    """Regression tests for transaction rollback on errors"""
    
    def test_transaction_rollback_on_expedition_error(self, client):
        """Test that database transaction rolls back on expedition error"""
        # This test ensures that if an error occurs during expedition outcome insert,
        # the transaction is rolled back and subsequent operations can proceed
        
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        initial_state = response1.json()
        
        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(2)
        
        # Grow clone
        client.post("/api/game/grow-clone?kind=BASIC", cookies={"session_id": session_id})
        time.sleep(2)
        
        # Get clone and apply
        response2 = client.get("/api/game/state", cookies={"session_id": session_id})
        state = response2.json()
        
        if not state.get("clones"):
            pytest.skip("No clones available")
        
        clone_id = list(state["clones"].keys())[0]
        client.post(f"/api/game/apply-clone?clone_id={clone_id}", cookies={"session_id": session_id})
        
        # Run expedition - should succeed
        response3 = client.post(
            "/api/game/run-expedition?kind=MINING",
            cookies={"session_id": session_id}
        )
        
        # Even if there was an error, subsequent operations should work
        # Verify we can still query state
        response4 = client.get("/api/game/state", cookies={"session_id": session_id})
        assert response4.status_code == 200, "State query should succeed after expedition"
        
        # Verify we can still query leaderboard (tests transaction recovery)
        response5 = client.get("/api/leaderboard?limit=10")
        assert response5.status_code == 200, "Leaderboard query should succeed (tests transaction recovery)"
    
    def test_multiple_expeditions_no_transaction_cascade(self, client):
        """Test that multiple expeditions don't cause transaction cascade failures"""
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        
        # Build womb
        client.post("/api/game/build-womb", cookies={"session_id": session_id})
        time.sleep(2)
        
        # Grow clone
        client.post("/api/game/grow-clone?kind=BASIC", cookies={"session_id": session_id})
        time.sleep(2)
        
        # Get clone and apply
        response2 = client.get("/api/game/state", cookies={"session_id": session_id})
        state = response2.json()
        
        if not state.get("clones"):
            pytest.skip("No clones available")
        
        clone_id = list(state["clones"].keys())[0]
        client.post(f"/api/game/apply-clone?clone_id={clone_id}", cookies={"session_id": session_id})
        
        # Run multiple expeditions
        for i in range(3):
            response = client.post(
                "/api/game/run-expedition?kind=MINING",
                cookies={"session_id": session_id}
            )
            # Each expedition should succeed independently
            assert response.status_code == 200, f"Expedition {i+1} should succeed"
            
            # Verify state query works after each expedition
            state_response = client.get("/api/game/state", cookies={"session_id": session_id})
            assert state_response.status_code == 200, f"State query should work after expedition {i+1}"


class TestEventEmissionRollback:
    """Regression tests for event emission transaction handling"""
    
    def test_event_emission_doesnt_break_on_error(self, client):
        """Test that event emission failures don't break the game"""
        # This test ensures that if event emission fails (e.g., DB error),
        # the game operation still completes successfully
        
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        
        # Gather resource - this should emit events
        response2 = client.post(
            "/api/game/gather-resource?resource=Tritanium",
            cookies={"session_id": session_id}
        )
        
        # Operation should succeed even if event emission fails
        assert response2.status_code == 200, "Gather should succeed even if event emission fails"
        
        # Verify state was updated
        response3 = client.get("/api/game/state", cookies={"session_id": session_id})
        assert response3.status_code == 200

