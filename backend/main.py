"""FastAPI application for LINEAGE backend"""
import sys
from pathlib import Path

# Add project root to Python path when running from backend/ directory (Railway)
# This allows imports from game/, core/, etc. to work
backend_dir = Path(__file__).parent
project_root = backend_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging

from routers import leaderboard, telemetry, game
from database import get_db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LINEAGE API",
    description="Backend API for LINEAGE game - leaderboard and telemetry",
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Restrict to needed methods
    allow_headers=["*"],
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
        db = get_db()
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)

