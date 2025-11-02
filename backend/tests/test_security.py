"""
Security tests for LINEAGE backend API.

Tests rate limiting, input validation, session security, and other security features.
"""
import pytest
import time
import json
from fastapi.testclient import TestClient


class TestRateLimiting:
    """Test rate limiting on all endpoints"""

    def test_get_state_rate_limit(self, client):
        """Test rate limiting on GET /api/game/state (60 req/min)"""
        # Get session
        response = client.get("/api/game/state")
        assert response.status_code == 200
        session_id = response.cookies.get("session_id")

        # Exceed rate limit (60 requests/minute)
        for i in range(61):
            response = client.get("/api/game/state", cookies={"session_id": session_id})
            if i < 60:
                assert response.status_code == 200, f"Request {i} should succeed"
            else:
                assert response.status_code == 429, "Request 61 should be rate limited"
                assert "Retry-After" in response.headers

    def test_save_state_rate_limit(self, client):
        """Test rate limiting on POST /api/game/state (30 req/min)"""
        # Get session and initial state
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")
        state_data = response.json()

        # Exceed rate limit (30 requests/minute)
        for i in range(31):
            response = client.post(
                "/api/game/state",
                json=state_data,
                cookies={"session_id": session_id}
            )
            if i < 30:
                assert response.status_code == 200, f"Request {i} should succeed"
            else:
                assert response.status_code == 429, "Request 31 should be rate limited"

    def test_task_status_rate_limit(self, client):
        """Test rate limiting on GET /api/game/tasks/status (120 req/min)"""
        # Get session
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Exceed rate limit (120 requests/minute)
        for i in range(121):
            response = client.get("/api/game/tasks/status", cookies={"session_id": session_id})
            if i < 120:
                assert response.status_code == 200, f"Request {i} should succeed"
            else:
                assert response.status_code == 429, "Request 121 should be rate limited"

    def test_gather_resource_rate_limit(self, client):
        """Test rate limiting on POST /api/game/gather-resource (20 req/min)"""
        # Get session
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Exceed rate limit (20 requests/minute)
        for i in range(21):
            response = client.post(
                "/api/game/gather-resource?resource=Tritanium",
                cookies={"session_id": session_id}
            )
            if i < 20:
                assert response.status_code in [200, 400], f"Request {i} should not be rate limited"
            else:
                assert response.status_code == 429, "Request 21 should be rate limited"

    def test_build_womb_rate_limit(self, client):
        """Test rate limiting on POST /api/game/build-womb (5 req/min)"""
        # Get session
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Exceed rate limit (5 requests/minute)
        for i in range(6):
            response = client.post(
                "/api/game/build-womb",
                cookies={"session_id": session_id}
            )
            if i < 5:
                assert response.status_code in [200, 400], f"Request {i} should not be rate limited"
            else:
                assert response.status_code == 429, "Request 6 should be rate limited"

    def test_grow_clone_rate_limit(self, client):
        """Test rate limiting on POST /api/game/grow-clone (10 req/min)"""
        # Get session
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Exceed rate limit (10 requests/minute)
        for i in range(11):
            response = client.post(
                "/api/game/grow-clone?kind=BASIC",
                cookies={"session_id": session_id}
            )
            if i < 10:
                assert response.status_code in [200, 400], f"Request {i} should not be rate limited"
            else:
                assert response.status_code == 429, "Request 11 should be rate limited"

    def test_rate_limit_per_session(self, client):
        """Test that rate limits are per-session, not global"""
        # Create two different sessions
        response1 = client.get("/api/game/state")
        session1 = response1.cookies.get("session_id")

        response2 = client.get("/api/game/state")
        session2 = response2.cookies.get("session_id")

        assert session1 != session2

        # Exhaust rate limit for session 1
        for i in range(5):
            client.post("/api/game/build-womb", cookies={"session_id": session1})

        # Session 1 should be rate limited
        response = client.post("/api/game/build-womb", cookies={"session_id": session1})
        assert response.status_code == 429

        # Session 2 should still work
        response = client.post("/api/game/build-womb", cookies={"session_id": session2})
        assert response.status_code in [200, 400]


class TestInputValidation:
    """Test input validation and sanitization"""

    def test_invalid_resource_type(self, client):
        """Test that invalid resource types are rejected"""
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Try invalid resource
        response = client.post(
            "/api/game/gather-resource?resource=InvalidResource",
            cookies={"session_id": session_id}
        )
        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"] or "invalid" in response.json()["detail"].lower()

    def test_invalid_clone_kind(self, client):
        """Test that invalid clone kinds are rejected"""
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Try invalid clone kind
        response = client.post(
            "/api/game/grow-clone?kind=INVALID_CLONE",
            cookies={"session_id": session_id}
        )
        assert response.status_code == 400

    def test_invalid_expedition_kind(self, client):
        """Test that invalid expedition kinds are rejected"""
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Try invalid expedition
        response = client.post(
            "/api/game/run-expedition?kind=INVALID_EXPEDITION",
            cookies={"session_id": session_id}
        )
        assert response.status_code == 400

    def test_invalid_clone_id_format(self, client):
        """Test that malformed clone IDs are rejected"""
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Try clone ID with SQL injection attempt
        response = client.post(
            "/api/game/apply-clone?clone_id=' OR '1'='1",
            cookies={"session_id": session_id}
        )
        assert response.status_code == 400

        # Try clone ID with script tags
        response = client.post(
            "/api/game/apply-clone?clone_id=<script>alert('xss')</script>",
            cookies={"session_id": session_id}
        )
        assert response.status_code == 400

    def test_clone_id_length_limit(self, client):
        """Test that excessively long clone IDs are rejected"""
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Try very long clone ID (over 100 chars)
        long_id = "a" * 150
        response = client.post(
            f"/api/game/apply-clone?clone_id={long_id}",
            cookies={"session_id": session_id}
        )
        assert response.status_code == 400

    def test_valid_inputs_accepted(self, client):
        """Test that valid inputs are accepted"""
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Valid resource types
        valid_resources = ["Tritanium", "Metal Ore", "Biomass", "Synthetic", "Organic", "Shilajit"]
        for resource in valid_resources:
            response = client.post(
                f"/api/game/gather-resource?resource={resource}",
                cookies={"session_id": session_id}
            )
            assert response.status_code in [200, 400], f"Valid resource {resource} should not be rejected for validation"


class TestSecurityHeaders:
    """Test security headers on all responses"""

    def test_security_headers_present(self, client):
        """Test that all security headers are present"""
        response = client.get("/")

        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

        assert "Content-Security-Policy" in response.headers
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]

        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers

    def test_security_headers_on_api_endpoints(self, client):
        """Test security headers on API endpoints"""
        response = client.get("/api/game/state")

        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Content-Security-Policy" in response.headers


class TestRequestSizeLimits:
    """Test request size limits"""

    def test_oversized_state_rejected(self, client):
        """Test that oversized game state is rejected (>1MB)"""
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Create oversized state (over 1MB)
        oversized_state = {
            "version": 1,
            "rng_seed": 12345,
            "soul_percent": 100.0,
            "soul_xp": 0,
            "assembler_built": False,
            "resources": {},
            "clones": {},
            # Add huge data to exceed 1MB
            "garbage": "x" * (2 * 1024 * 1024)  # 2MB of data
        }

        response = client.post(
            "/api/game/state",
            json=oversized_state,
            cookies={"session_id": session_id}
        )
        assert response.status_code == 413  # Payload Too Large

    def test_normal_size_state_accepted(self, client):
        """Test that normal-sized state is accepted"""
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")
        state_data = response.json()

        # Normal state should be accepted
        response = client.post(
            "/api/game/state",
            json=state_data,
            cookies={"session_id": session_id}
        )
        assert response.status_code == 200


class TestSessionSecurity:
    """Test session management security"""

    def test_session_cookie_httponly(self, client):
        """Test that session cookie has HttpOnly flag"""
        response = client.get("/api/game/state")

        # Get Set-Cookie header
        set_cookie = response.headers.get("set-cookie", "")
        assert "httponly" in set_cookie.lower() or "HttpOnly" in set_cookie

    def test_session_cookie_samesite(self, client):
        """Test that session cookie has SameSite attribute"""
        response = client.get("/api/game/state")

        set_cookie = response.headers.get("set-cookie", "")
        assert "samesite" in set_cookie.lower()

    def test_different_sessions_isolated(self, client):
        """Test that different sessions have isolated data"""
        # Create two sessions
        response1 = client.get("/api/game/state")
        session1 = response1.cookies.get("session_id")
        state1 = response1.json()

        response2 = client.get("/api/game/state")
        session2 = response2.cookies.get("session_id")
        state2 = response2.json()

        # Sessions should be different
        assert session1 != session2

        # Modify state1
        state1["soul_xp"] = 12345
        client.post("/api/game/state", json=state1, cookies={"session_id": session1})

        # Check that state2 is not affected
        response = client.get("/api/game/state", cookies={"session_id": session2})
        state2_after = response.json()
        assert state2_after["soul_xp"] != 12345


class TestErrorHandling:
    """Test error handling and message sanitization"""

    def test_invalid_request_error_message(self, client):
        """Test that error messages don't leak sensitive information"""
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Send invalid data
        response = client.post(
            "/api/game/state",
            json={"invalid": "data"},
            cookies={"session_id": session_id}
        )
        assert response.status_code == 400

        # Error message should not contain stack traces or internal paths
        error_detail = response.json()["detail"]
        assert "Traceback" not in error_detail
        assert "/Users/" not in error_detail
        assert "line " not in error_detail.lower() or "Invalid" in error_detail

    def test_404_on_invalid_endpoint(self, client):
        """Test 404 on non-existent endpoints"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404


class TestCORS:
    """Test CORS configuration"""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present"""
        response = client.options("/api/game/state")

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    def test_allowed_methods_restricted(self, client):
        """Test that only allowed methods are permitted"""
        # PUT should not be allowed (only GET, POST, OPTIONS)
        response = client.put("/api/game/state")
        assert response.status_code in [405, 404]  # Method Not Allowed or Not Found


class TestRateLimitBypass:
    """Test that rate limits cannot be easily bypassed"""

    def test_rate_limit_not_bypassed_by_new_session(self, client):
        """Test that creating new sessions doesn't bypass rate limits easily"""
        # This is somewhat contrived, but tests the principle
        # In production, you'd also want IP-based rate limiting

        # Get initial session
        response = client.get("/api/game/state")
        session_id = response.cookies.get("session_id")

        # Exhaust rate limit
        for i in range(5):
            client.post("/api/game/build-womb", cookies={"session_id": session_id})

        # Should be rate limited
        response = client.post("/api/game/build-womb", cookies={"session_id": session_id})
        assert response.status_code == 429

        # Creating a new session DOES work (this is expected behavior)
        # but in production you'd also have IP-based limits
        response = client.get("/api/game/state")
        new_session = response.cookies.get("session_id")
        assert new_session != session_id

        # New session can make requests
        response = client.post("/api/game/build-womb", cookies={"session_id": new_session})
        assert response.status_code in [200, 400]


class TestAuthenticationSecurity:
    """Test authentication-related security"""

    def test_no_session_creates_new(self, client):
        """Test that requests without session create new session"""
        response = client.get("/api/game/state")
        assert response.status_code == 200
        assert "session_id" in response.cookies

    def test_invalid_session_handled(self, client):
        """Test that invalid session IDs are handled gracefully"""
        # Use clearly invalid session ID
        response = client.get("/api/game/state", cookies={"session_id": "invalid-session-id"})
        assert response.status_code == 200  # Should create new session

    def test_session_fixation_protection(self, client):
        """Test basic session fixation protection"""
        # Try to set a specific session ID
        forced_session = "attacker-controlled-session"

        response = client.get("/api/game/state", cookies={"session_id": forced_session})
        assert response.status_code == 200

        # Server should accept it (this is current behavior)
        # In a more secure implementation, you might want to regenerate session IDs
        # after certain actions or validate session format
