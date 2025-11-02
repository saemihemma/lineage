"""FastAPI application for LINEAGE backend"""
import sys
from pathlib import Path

# Add project root to Python path when running from backend/ directory (Railway)
# This allows imports from game/, core/, etc. to work
backend_dir = Path(__file__).parent
project_root = backend_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
import os
import logging
import time

from routers import leaderboard, telemetry, game
from database import get_db
from middleware.csrf import CSRFMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment check
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"

# Request size limits (in bytes)
MAX_REQUEST_SIZE = {
    "default": 10 * 1024,  # 10KB for most endpoints
    "state": 1 * 1024 * 1024,  # 1MB for state saving
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HSTS (only in production with HTTPS)
        if IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp

        # Additional security headers
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent DoS attacks"""

    async def dispatch(self, request: Request, call_next):
        # Get content length
        content_length = request.headers.get("content-length")

        if content_length:
            content_length = int(content_length)

            # Determine size limit based on endpoint
            if "/api/game/state" in request.url.path and request.method == "POST":
                max_size = MAX_REQUEST_SIZE["state"]
            else:
                max_size = MAX_REQUEST_SIZE["default"]

            # Check if request is too large
            if content_length > max_size:
                logger.warning(
                    f"Request too large: {content_length} bytes from {request.client.host} "
                    f"to {request.url.path}"
                )
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body too large. Maximum size: {max_size} bytes"}
                )

        return await call_next(request)


# Create FastAPI app
app = FastAPI(
    title="LINEAGE API",
    description="Backend API for LINEAGE game - leaderboard, telemetry, and gameplay",
    version="1.0.0"
)

# CORS configuration - environment-based for security
def get_allowed_origins() -> list:
    """Get allowed CORS origins from environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        # In production, only allow specific domains
        origins_str = os.getenv("ALLOWED_ORIGINS", "")
        if origins_str:
            origins = [origin.strip() for origin in origins_str.split(",")]
            logger.info(f"Production CORS origins: {origins}")
            return origins
        else:
            logger.warning("Production mode but no ALLOWED_ORIGINS set!")
            return []
    else:
        # Development: allow localhost and common dev ports
        logger.info("Development mode: allowing common localhost origins")
        return [
            "http://localhost:3000",
            "http://localhost:5173",  # Vite default
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8080",
        ]

allowed_origins = get_allowed_origins()

# Add security middleware (order matters - security headers should be last in chain)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(CSRFMiddleware)  # CSRF protection for state-changing requests
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Restrict to needed methods
    allow_headers=["*", "X-CSRF-Token"],  # Allow CSRF token header
    expose_headers=["X-CSRF-Token"],  # Expose CSRF token to client
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Include routers
app.include_router(leaderboard.router)
app.include_router(telemetry.router)
app.include_router(game.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LINEAGE API",
        "version": "1.0.0",
        "status": "online"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        from database import execute_query
        db = get_db()
        execute_query(db, "SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler - sanitizes errors in production.
    """
    # Log the actual error for debugging
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)

    # Return sanitized error message
    if IS_PRODUCTION:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    else:
        # Include error details in development
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "type": type(exc).__name__
            }
        )


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)

