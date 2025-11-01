"""FastAPI application for LINEAGE backend"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

from backend.routers import leaderboard, telemetry
from backend.database import get_db

# Create FastAPI app
app = FastAPI(
    title="LINEAGE API",
    description="Backend API for LINEAGE game - leaderboard and telemetry",
    version="1.0.0"
)

# CORS middleware - allow requests from game client
# In production, restrict origins to your game's domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For MVP, allow all. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leaderboard.router)
app.include_router(telemetry.router)


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

