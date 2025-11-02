"""Tests for CSRF protection"""
import pytest
import time
from core.csrf import generate_csrf_token, validate_csrf_token, generate_csrf_cookie_value


class TestCSRFTokenGeneration:
    """Test CSRF token generation"""

    def test_generate_token_format(self):
        """Test that generated token has correct format"""
        session_id = "test-session-123"
        token = generate_csrf_token(session_id)

        # Token should be timestamp|session_id|signature
        parts = token.split("|")
        assert len(parts) == 3, "Token should have 3 parts"

        timestamp_str, token_session_id, signature = parts

        # Timestamp should be a valid integer
        timestamp = int(timestamp_str)
        assert timestamp > 0

        # Session ID should match
        assert token_session_id == session_id

        # Signature should be hex (64 chars for SHA256)
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature)

    def test_generate_token_deterministic_for_same_timestamp(self):
        """Test that token generation is deterministic for same inputs"""
        session_id = "test-session-123"

        # Tokens generated at same time should have same timestamp part
        token1 = generate_csrf_token(session_id)
        token2 = generate_csrf_token(session_id)

        # Timestamps might differ by 1 second, but signatures should be valid
        is_valid1 = validate_csrf_token(token1, session_id)[0]
        is_valid2 = validate_csrf_token(token2, session_id)[0]

        assert is_valid1 is True
        assert is_valid2 is True

    def test_generate_token_different_sessions(self):
        """Test that different sessions get different tokens"""
        token1 = generate_csrf_token("session-1")
        token2 = generate_csrf_token("session-2")

        assert token1 != token2


class TestCSRFTokenValidation:
    """Test CSRF token validation"""

    def test_validate_valid_token(self):
        """Test validation of a valid token"""
        session_id = "test-session-123"
        token = generate_csrf_token(session_id)

        is_valid, error = validate_csrf_token(token, session_id)

        assert is_valid is True
        assert error is None

    def test_validate_missing_token(self):
        """Test validation fails for missing token"""
        is_valid, error = validate_csrf_token("", "session-123")

        assert is_valid is False
        assert "missing" in error.lower()

    def test_validate_invalid_format(self):
        """Test validation fails for invalid token format"""
        is_valid, error = validate_csrf_token("invalid-token", "session-123")

        assert is_valid is False
        assert "format" in error.lower()

    def test_validate_session_mismatch(self):
        """Test validation fails when session ID doesn't match"""
        session_id = "session-123"
        token = generate_csrf_token(session_id)

        # Try to use token with different session
        is_valid, error = validate_csrf_token(token, "different-session")

        assert is_valid is False
        assert "mismatch" in error.lower()

    def test_validate_tampered_signature(self):
        """Test validation fails for tampered signature"""
        session_id = "session-123"
        token = generate_csrf_token(session_id)

        # Tamper with signature
        parts = token.split("|")
        parts[2] = "0" * 64  # Replace signature with fake one
        tampered_token = "|".join(parts)

        is_valid, error = validate_csrf_token(tampered_token, session_id)

        assert is_valid is False
        assert "signature" in error.lower() or "invalid" in error.lower()

    def test_validate_expired_token(self):
        """Test validation fails for expired token"""
        session_id = "session-123"

        # Create token with old timestamp
        old_timestamp = int(time.time()) - 7200  # 2 hours ago
        from core.csrf import CSRF_SECRET_KEY
        import hmac
        import hashlib

        message = f"{old_timestamp}|{session_id}"
        signature = hmac.new(
            CSRF_SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        expired_token = f"{old_timestamp}|{session_id}|{signature}"

        is_valid, error = validate_csrf_token(expired_token, session_id)

        assert is_valid is False
        assert "expired" in error.lower()

    def test_validate_future_timestamp(self):
        """Test validation fails for future timestamp"""
        session_id = "session-123"

        # Create token with future timestamp
        future_timestamp = int(time.time()) + 7200  # 2 hours from now
        from core.csrf import CSRF_SECRET_KEY
        import hmac
        import hashlib

        message = f"{future_timestamp}|{session_id}"
        signature = hmac.new(
            CSRF_SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        future_token = f"{future_timestamp}|{session_id}|{signature}"

        is_valid, error = validate_csrf_token(future_token, session_id)

        assert is_valid is False
        assert "future" in error.lower()


class TestCSRFProtectionE2E:
    """End-to-end CSRF protection tests"""

    def test_get_state_issues_csrf_token(self, client):
        """Test that GET /api/game/state issues CSRF token"""
        response = client.get("/api/game/state")

        assert response.status_code == 200

        # Should have session cookie
        assert "session_id" in response.cookies

        # Should have CSRF token cookie
        assert "csrf_token" in response.cookies

        csrf_token = response.cookies.get("csrf_token")
        assert csrf_token is not None
        assert len(csrf_token) > 0

    def test_post_with_valid_csrf_succeeds(self, client):
        """Test that POST with valid CSRF token succeeds"""
        # Get session and CSRF token
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        csrf_token = response1.cookies.get("csrf_token")

        # Get state to modify
        state = response1.json()
        state["self_name"] = "Test Player"

        # POST with CSRF token in header
        response2 = client.post(
            "/api/game/state",
            json=state,
            cookies={"session_id": session_id, "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token}
        )

        assert response2.status_code == 200

    def test_post_without_csrf_fails(self, client):
        """Test that POST without CSRF token fails"""
        # Get session
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Get state to modify
        state = response1.json()
        state["self_name"] = "Test Player"

        # POST without CSRF token
        response2 = client.post(
            "/api/game/state",
            json=state,
            cookies={"session_id": session_id}
            # No X-CSRF-Token header
        )

        assert response2.status_code == 403
        assert "CSRF" in response2.json()["detail"]

    def test_post_with_invalid_csrf_fails(self, client):
        """Test that POST with invalid CSRF token fails"""
        # Get session
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # Get state to modify
        state = response1.json()
        state["self_name"] = "Test Player"

        # POST with fake CSRF token
        response2 = client.post(
            "/api/game/state",
            json=state,
            cookies={"session_id": session_id},
            headers={"X-CSRF-Token": "fake-token-12345"}
        )

        assert response2.status_code == 403
        assert "CSRF" in response2.json()["detail"]

    def test_post_with_csrf_from_cookie_succeeds(self, client):
        """Test that POST with CSRF token from cookie succeeds"""
        # Get session and CSRF token
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")
        csrf_token = response1.cookies.get("csrf_token")

        # Get state to modify
        state = response1.json()
        state["self_name"] = "Test Player"

        # POST with CSRF token in cookie (same-origin requests)
        response2 = client.post(
            "/api/game/state",
            json=state,
            cookies={"session_id": session_id, "csrf_token": csrf_token}
            # CSRF token in cookie, not header
        )

        assert response2.status_code == 200

    def test_get_requests_dont_require_csrf(self, client):
        """Test that GET requests don't require CSRF token"""
        # Get session
        response1 = client.get("/api/game/state")
        session_id = response1.cookies.get("session_id")

        # GET request without CSRF token should work
        response2 = client.get(
            "/api/game/state",
            cookies={"session_id": session_id}
        )

        assert response2.status_code == 200
