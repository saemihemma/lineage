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

LINEAGE backend includes comprehensive security hardening to prevent abuse and ensure stability.

#### Rate Limiting

Session-based rate limiting is implemented on all game endpoints to prevent abuse:

**Game API Endpoints:**
- `GET /api/game/state` - 60 requests/minute (state retrieval)
- `POST /api/game/state` - 30 requests/minute (state saving)
- `GET /api/game/tasks/status` - 120 requests/minute (polling endpoint)
- `POST /api/game/gather-resource` - 20 requests/minute
- `POST /api/game/build-womb` - 5 requests/minute
- `POST /api/game/grow-clone` - 10 requests/minute
- `POST /api/game/apply-clone` - 10 requests/minute
- `POST /api/game/run-expedition` - 10 requests/minute
- `POST /api/game/upload-clone` - 10 requests/minute

**Other Endpoints:**
- Leaderboard: 10 requests/minute
- Telemetry: 50 requests/minute

Rate limits are enforced per session ID, providing more accurate tracking than IP-based limiting.
Exceeded limits return HTTP 429 with a `Retry-After` header.

**Note:** Current implementation uses in-memory rate limiting. For multi-instance production deployments, consider using Redis for distributed rate limiting.

#### Security Headers

All responses include security headers to protect against common web vulnerabilities:

- `X-Content-Type-Options: nosniff` - Prevents MIME-type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking attacks
- `X-XSS-Protection: 1; mode=block` - Enables XSS protection
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` - Enforces HTTPS (production only)
- `Content-Security-Policy` - Restricts resource loading to prevent XSS
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer information
- `Permissions-Policy` - Restricts browser features

#### Request Size Limits

Request body sizes are limited to prevent DoS attacks:

- **State saving** (`POST /api/game/state`): Maximum 1MB
- **All other endpoints**: Maximum 10KB

Requests exceeding these limits return HTTP 413 (Payload Too Large).

#### Input Validation

All user inputs are validated and sanitized:

- **Resource types**: Validated against allowed list (Tritanium, Metal Ore, Biomass, Synthetic, Organic, Shilajit)
- **Clone kinds**: Validated against allowed list (BASIC, MINER, VOLATILE)
- **Expedition types**: Validated against allowed list (MINING, COMBAT, EXPLORATION)
- **Clone IDs**: Sanitized to prevent injection attacks, max length 100 characters
- **SQL injection prevention**: All database queries use parameterized statements
- **XSS prevention**: All inputs are sanitized before processing

#### Session Security

Sessions are managed securely with the following features:

- **Session expiration**: 24 hours of inactivity
- **HttpOnly cookies**: Prevents JavaScript access to session cookies
- **SameSite attribute**: Set to `lax` to prevent CSRF attacks
- **Secure flag**: Enabled in production (HTTPS only)
- **Automatic cleanup**: Expired sessions are automatically removed from database

#### Error Message Sanitization

Error messages are sanitized to prevent information leakage:

- **Production mode**: Generic error messages only
- **Development mode**: Detailed error messages for debugging
- **No stack traces**: Never exposed to clients in production
- **Logging**: All errors are logged server-side for monitoring

#### CORS Configuration

CORS is configured based on environment:

- **Production**: Restricted to domains specified in `ALLOWED_ORIGINS` environment variable
- **Development**: Allows localhost on common development ports (3000, 5173, 8080)
- **Methods**: Restricted to GET, POST, OPTIONS only
- **Credentials**: Enabled for session cookie support

#### Additional Security Measures

- **Environment-based configuration**: Security settings adjust based on `ENVIRONMENT` variable
- **Comprehensive logging**: All security events (rate limit violations, invalid inputs) are logged
- **Database security**: All queries use parameterized statements to prevent SQL injection

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
- `ENVIRONMENT`: Environment mode - `production` or `development` (default: `development`)
  - **Production mode**: Enables HSTS, secure cookies, sanitized errors
  - **Development mode**: Detailed error messages, relaxed CORS
- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins (production only)
  - Example: `https://yourdomain.com,https://www.yourdomain.com`
  - Required in production for security

**Client:**
- `LINEAGE_API_URL`: Backend API URL
- `LINEAGE_API_ENABLED`: Enable/disable API (true/false)
- `LINEAGE_API_TIMEOUT`: Request timeout (seconds)

**Security Configuration:**

To enable production security features, set these environment variables:

```bash
export ENVIRONMENT=production
export ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

Or in your hosting platform's environment settings:
- Railway: Settings → Variables
- Render: Environment → Environment Variables
- Fly.io: `fly secrets set ENVIRONMENT=production`

## Testing

### Run Security Tests

LINEAGE includes comprehensive security tests covering rate limiting, input validation, session security, and more.

```bash
cd backend
pytest tests/test_security.py -v
```

The security test suite includes 20+ tests covering:
- Rate limiting enforcement on all endpoints
- Input validation and sanitization
- Security headers presence
- Request size limits
- Session security (HttpOnly, SameSite, isolation)
- Error message sanitization
- CORS configuration

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

# Test rate limiting (should fail after 60 requests)
for i in {1..65}; do
  curl -b cookies.txt -c cookies.txt http://localhost:8000/api/game/state
  echo "Request $i"
done

# Test security headers
curl -I http://localhost:8000/api/health | grep -E "X-|Content-Security"
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

