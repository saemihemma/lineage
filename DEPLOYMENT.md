# LINEAGE Deployment Guide

This guide covers deploying LINEAGE for web deployment with leaderboard and telemetry features.

## Architecture Overview

LINEAGE consists of:
1. **Game Client** (Desktop): Tkinter-based desktop application
2. **Backend API**: FastAPI server for leaderboard and telemetry
3. **Database**: SQLite (MVP) or PostgreSQL (production)

## Quick Start

### 1. Backend Setup

```bash
# Install backend dependencies
cd backend
pip install -r requirements.txt

# Run backend server
python main.py
# Or: uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Backend API will be available at `http://localhost:8000`

### 2. Game Client Setup

```bash
# Install game dependencies
pip install -r requirements.txt

# Configure API URL (optional, defaults to localhost:8000)
export LINEAGE_API_URL="http://localhost:8000"

# Run game
python main.py
```

## Client Configuration

The game client reads API configuration from environment variables:

- `LINEAGE_API_URL`: Backend API base URL (default: `http://localhost:8000`)
- `LINEAGE_API_ENABLED`: Enable/disable API features (default: `true`)
- `LINEAGE_API_TIMEOUT`: Request timeout in seconds (default: `5.0`)

Or edit `core/api_config.py` directly.

## Backend Deployment

### Railway

1. Create account at [railway.app](https://railway.app)
2. Create new project
3. Connect GitHub repository
4. Add new service → Select repository
5. Set root directory: `backend/`
6. Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
7. (Optional) Add PostgreSQL database
8. Set environment variables if needed
9. Deploy

### Render

1. Create account at [render.com](https://render.com)
2. New → Web Service
3. Connect GitHub repository
4. Settings:
   - Root Directory: `backend/`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. (Optional) Add PostgreSQL database
6. Set environment variables
7. Deploy

### Fly.io

1. Install flyctl: `brew install flyctl` (Mac) or see [fly.io docs](https://fly.io/docs/getting-started/installing-flyctl/)
2. Login: `flyctl auth login`
3. In `backend/` directory, initialize: `flyctl launch`
4. Deploy: `flyctl deploy`

## Production Considerations

### Security

- **CORS**: Update `backend/main.py` to restrict allowed origins
- **HTTPS**: Always use HTTPS in production
- **API Keys**: Consider adding authentication for leaderboard submissions
- **Rate Limiting**: Current implementation uses in-memory rate limiting. For production, use Redis.

### Database

**MVP (SQLite)**:
- Good for development and small deployments
- File-based, no separate database server needed
- Limited concurrency

**Production (PostgreSQL)**:
- Better performance and concurrency
- Recommended for production deployments
- Update `DATABASE_URL` environment variable

### Environment Variables

**Backend:**
- `DATABASE_URL`: Database connection string
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)

**Client:**
- `LINEAGE_API_URL`: Backend API URL
- `LINEAGE_API_ENABLED`: Enable/disable API (true/false)
- `LINEAGE_API_TIMEOUT`: Request timeout (seconds)

## Testing

### Test Backend API

```bash
# Health check
curl http://localhost:8000/api/health

# Get leaderboard
curl http://localhost:8000/api/leaderboard

# Submit entry
curl -X POST http://localhost:8000/api/leaderboard/submit \
  -H "Content-Type: application/json" \
  -d '{
    "self_name": "TestSELF",
    "soul_level": 5,
    "soul_xp": 500,
    "clones_uploaded": 3,
    "total_expeditions": 10
  }'
```

### Test Game Client

1. Start backend server
2. Set `LINEAGE_API_URL` environment variable
3. Run game: `python main.py`
4. Set SELF name in loading screen
5. Play game, build up stats
6. Click "Submit to Leaderboard" button
7. Click "Leaderboard" button to view rankings

## API Documentation

When backend is running, visit:
- **Swagger UI**: `http://your-api-url/docs`
- **ReDoc**: `http://your-api-url/redoc`

## Troubleshooting

### Backend won't start
- Check database permissions
- Verify `DATABASE_URL` is correct
- Check port is not already in use

### Client can't connect to API
- Verify `LINEAGE_API_URL` is correct
- Check backend is running
- Check firewall/network settings
- Test with `curl` from command line

### Leaderboard not showing
- Check backend is online: `curl http://your-api-url/api/health`
- Verify API URL in client configuration
- Check browser/network console for errors

## Next Steps

1. Deploy backend to hosting provider
2. Update `LINEAGE_API_URL` in client configuration
3. Test end-to-end flow
4. Monitor API usage and performance
5. Consider upgrading to PostgreSQL for production
6. Add authentication if needed
7. Implement proper logging and monitoring

