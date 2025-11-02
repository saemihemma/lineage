"""CSRF protection middleware for FastAPI"""
import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from core.csrf import validate_csrf_token

logger = logging.getLogger(__name__)

# Methods that require CSRF protection
PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths exempt from CSRF (e.g., login endpoints, public APIs)
EXEMPT_PATHS = {
    "/api/telemetry",  # Telemetry can be called from anywhere
}


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce CSRF token validation on state-changing requests.

    CSRF tokens are required for POST/PUT/PATCH/DELETE requests to prevent
    cross-site request forgery attacks.
    """

    async def dispatch(self, request: Request, call_next):
        # Only check state-changing methods
        if request.method not in PROTECTED_METHODS:
            return await call_next(request)

        # Check if path is exempt
        path = request.url.path
        if any(path.startswith(exempt) for exempt in EXEMPT_PATHS):
            return await call_next(request)

        # Get session ID from cookie
        session_id = request.cookies.get("session_id")
        if not session_id:
            # No session = create new one, no CSRF needed yet
            return await call_next(request)

        # Get CSRF token from header
        csrf_token = request.headers.get("X-CSRF-Token")

        if not csrf_token:
            # Also check cookie (for same-origin requests)
            csrf_token = request.cookies.get("csrf_token")

        # Validate CSRF token
        is_valid, error_message = validate_csrf_token(csrf_token or "", session_id)

        if not is_valid:
            logger.warning(
                f"CSRF validation failed for {request.method} {path}: {error_message} "
                f"(session: {session_id[:8]}...)"
            )
            raise HTTPException(
                status_code=403,
                detail=f"CSRF validation failed: {error_message}"
            )

        # CSRF token is valid, proceed
        response = await call_next(request)
        return response
