"""CSRF (Cross-Site Request Forgery) protection"""
import secrets
import hmac
import hashlib
import time
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# CSRF secret key - load from environment or generate
CSRF_SECRET_KEY = os.getenv("CSRF_SECRET_KEY")

if not CSRF_SECRET_KEY:
    # Generate a secret key for development
    CSRF_SECRET_KEY = secrets.token_hex(32)
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        logger.warning("⚠️  CSRF_SECRET_KEY not set! Using generated key (NOT PRODUCTION SAFE)")
    else:
        logger.info("Development mode: using generated CSRF key")

# Token expiry (1 hour)
CSRF_TOKEN_EXPIRY = 3600


def generate_csrf_token(session_id: str) -> str:
    """
    Generate CSRF token for a session.

    Token format: timestamp|session_id|signature

    Args:
        session_id: Session identifier

    Returns:
        CSRF token string
    """
    timestamp = str(int(time.time()))

    # Create message: timestamp|session_id
    message = f"{timestamp}|{session_id}"

    # Generate HMAC signature
    signature = hmac.new(
        CSRF_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    # Return token: timestamp|session_id|signature
    token = f"{timestamp}|{session_id}|{signature}"

    return token


def validate_csrf_token(token: str, session_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate CSRF token.

    Args:
        token: CSRF token to validate
        session_id: Expected session ID

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not token:
        return False, "CSRF token missing"

    # Parse token
    try:
        parts = token.split("|")
        if len(parts) != 3:
            return False, "Invalid CSRF token format"

        timestamp_str, token_session_id, provided_signature = parts
        timestamp = int(timestamp_str)
    except (ValueError, IndexError):
        return False, "Invalid CSRF token format"

    # Check session ID match
    if token_session_id != session_id:
        return False, "CSRF token session mismatch"

    # Check token expiry
    current_time = int(time.time())
    age = current_time - timestamp

    if age > CSRF_TOKEN_EXPIRY:
        return False, f"CSRF token expired (age: {age}s, max: {CSRF_TOKEN_EXPIRY}s)"

    if age < 0:
        return False, "CSRF token timestamp is in the future"

    # Verify signature
    message = f"{timestamp_str}|{token_session_id}"
    expected_signature = hmac.new(
        CSRF_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison
    if not hmac.compare_digest(provided_signature, expected_signature):
        return False, "CSRF token signature invalid"

    return True, None


def generate_csrf_cookie_value(session_id: str) -> str:
    """
    Generate CSRF token for cookie storage.

    Args:
        session_id: Session identifier

    Returns:
        CSRF token string
    """
    return generate_csrf_token(session_id)
