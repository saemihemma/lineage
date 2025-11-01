# LINEAGE Backend API

FastAPI backend server for LINEAGE game leaderboard and telemetry.

## Features

- **Leaderboard API**: Submit and retrieve SELF rankings
- **Telemetry API**: Collect game analytics data
- **Rate Limiting**: IP-based rate limiting to prevent abuse
- **SQLite Database**: Simple database for MVP (can upgrade to PostgreSQL)

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Database

By default, the backend uses SQLite with a local file `lineage.db`.

To use a different database:
- Set `DATABASE_URL` environment variable
- For PostgreSQL: `DATABASE_URL=postgresql://user:pass@host/dbname`
- For SQLite: `DATABASE_URL=sqlite:///path/to/db.db`

### 3. Run Server

**Development:**
```bash
python backend/main.py
```

**Production (with uvicorn):**
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

### Leaderboard

- `GET /api/leaderboard` - Get leaderboard entries
  - Query params: `limit` (default 100), `offset` (default 0)
  
- `POST /api/leaderboard/submit` - Submit SELF stats
  - Body: `{ "self_name": "...", "soul_level": 1, "soul_xp": 0, ... }`
  
- `GET /api/leaderboard/stats` - Get leaderboard statistics

### Telemetry

- `POST /api/telemetry` - Upload telemetry events
  - Body: Array of event objects
  
- `GET /api/telemetry/stats` - Get telemetry statistics

### Health

- `GET /api/health` - Health check endpoint
- `GET /` - Root endpoint with service info

## Environment Variables

- `DATABASE_URL` - Database connection string
- `PORT` - Server port (default: 8000)
- `HOST` - Server host (default: 0.0.0.0)

## Deployment

### Railway

1. Create new project on Railway
2. Connect GitHub repository
3. Set root directory to `backend/`
4. Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add PostgreSQL database (optional, upgrade from SQLite)
6. Deploy

### Render

1. Create new Web Service on Render
2. Connect GitHub repository
3. Set root directory to `backend/`
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
6. Add PostgreSQL database (optional)
7. Deploy

### Docker (Optional)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Security Notes

- Currently allows CORS from all origins (for MVP)
- Rate limiting: 10 requests/minute per IP for leaderboard
- Rate limiting: 50 requests/minute per IP for telemetry
- Input validation on all endpoints
- For production, consider:
  - Restrict CORS origins
  - Add authentication (API keys, JWT)
  - Use HTTPS only
  - Upgrade to PostgreSQL
  - Add request logging
  - Implement proper rate limiting (Redis)

## Database Schema

### leaderboard
- `id` (TEXT PRIMARY KEY)
- `self_name` (TEXT, indexed)
- `soul_level` (INTEGER)
- `soul_xp` (INTEGER)
- `clones_uploaded` (INTEGER)
- `total_expeditions` (INTEGER)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### telemetry_events
- `id` (TEXT PRIMARY KEY)
- `session_id` (TEXT, indexed)
- `event_type` (TEXT)
- `data` (TEXT, JSON)
- `timestamp` (TIMESTAMP)

## Testing

Test the API with curl:

```bash
# Health check
curl http://localhost:8000/api/health

# Get leaderboard
curl http://localhost:8000/api/leaderboard

# Submit to leaderboard
curl -X POST http://localhost:8000/api/leaderboard/submit \
  -H "Content-Type: application/json" \
  -d '{"self_name": "TestSELF", "soul_level": 5, "soul_xp": 500, "clones_uploaded": 3, "total_expeditions": 10}'
```

## Client Configuration

The game client should set these environment variables:

- `LINEAGE_API_URL` - API base URL (default: http://localhost:8000)
- `LINEAGE_API_ENABLED` - Enable/disable API (default: true)
- `LINEAGE_API_TIMEOUT` - Request timeout in seconds (default: 5.0)

Or configure in `core/api_config.py`.

