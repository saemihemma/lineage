# LINEAGE Security Configuration Quick Reference

## Rate Limits

### Game API Endpoints
```
GET  /api/game/state              → 60 requests/minute
POST /api/game/state              → 30 requests/minute
GET  /api/game/tasks/status       → 120 requests/minute
POST /api/game/gather-resource    → 20 requests/minute
POST /api/game/build-womb         → 5 requests/minute
POST /api/game/grow-clone         → 10 requests/minute
POST /api/game/apply-clone        → 10 requests/minute
POST /api/game/run-expedition     → 10 requests/minute
POST /api/game/upload-clone       → 10 requests/minute
```

### Other Endpoints
```
Leaderboard endpoints  → 10 requests/minute
Telemetry endpoints    → 50 requests/minute
```

## Security Headers

All responses include:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()

# Production only:
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

## Request Size Limits

```
POST /api/game/state  → 1MB maximum
All other endpoints   → 10KB maximum
```

## Input Validation

### Valid Resource Types
```
Tritanium, Metal Ore, Biomass, Synthetic, Organic, Shilajit
```

### Valid Clone Kinds
```
BASIC, MINER, VOLATILE
```

### Valid Expedition Types
```
MINING, COMBAT, EXPLORATION
```

### Clone ID Rules
- Alphanumeric characters, dashes, underscores only
- Maximum 100 characters
- No special characters or SQL/XSS attempts

## Session Configuration

```
Expiration:     24 hours
Cookie flags:   HttpOnly, SameSite=lax, Secure (production)
Isolation:      Per-session data isolation
Cleanup:        Automatic removal of expired sessions
```

## Environment Variables

### Production Setup
```bash
export ENVIRONMENT=production
export ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
export DATABASE_URL=your_database_url
export PORT=8000
```

### Development Setup
```bash
export ENVIRONMENT=development
# ALLOWED_ORIGINS not required (defaults to localhost)
```

## Error Handling

### Production Mode (ENVIRONMENT=production)
- Generic error messages only
- No stack traces
- All errors logged server-side

### Development Mode (ENVIRONMENT=development)
- Detailed error messages
- Error type included
- Full error context for debugging

## Testing

### Run All Security Tests
```bash
cd backend
pytest tests/test_security.py -v
```

### Test Specific Security Feature
```bash
# Rate limiting
pytest tests/test_security.py::TestRateLimiting -v

# Input validation
pytest tests/test_security.py::TestInputValidation -v

# Security headers
pytest tests/test_security.py::TestSecurityHeaders -v

# Session security
pytest tests/test_security.py::TestSessionSecurity -v
```

### Manual Testing
```bash
# Test rate limiting
for i in {1..65}; do curl -b cookies.txt -c cookies.txt http://localhost:8000/api/game/state; done

# Test security headers
curl -I http://localhost:8000/api/health | grep -E "X-|Content-Security"

# Test input validation
curl -X POST "http://localhost:8000/api/game/gather-resource?resource=InvalidResource" -b cookies.txt

# Test request size limit
dd if=/dev/zero bs=1M count=2 | base64 > large.txt
curl -X POST http://localhost:8000/api/game/state -H "Content-Type: application/json" -d @large.txt
```

## Monitoring

### Log Patterns to Watch

**Rate Limit Violations:**
```
WARNING:backend.routers.game:Rate limit exceeded for session <id> on <endpoint>
```

**Invalid Input Attempts:**
```
ERROR:backend.routers.game:Error <action> for session <id>: Invalid <type>
```

**Expired Sessions:**
```
INFO:backend.routers.game:Cleaned up expired session <id>
```

**Large Request Attempts:**
```
WARNING:backend.main:Request too large: <size> bytes from <ip> to <path>
```

## Response Codes

```
200 OK                  - Success
400 Bad Request         - Invalid input
404 Not Found           - Endpoint doesn't exist
413 Payload Too Large   - Request exceeds size limit
429 Too Many Requests   - Rate limit exceeded (includes Retry-After header)
500 Internal Error      - Server error (sanitized in production)
```

## Quick Deployment Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Configure `ALLOWED_ORIGINS` with your domain(s)
- [ ] Verify HTTPS is enabled
- [ ] Run security tests: `pytest tests/test_security.py`
- [ ] Test rate limiting manually
- [ ] Verify security headers are present
- [ ] Enable logging and monitoring
- [ ] Configure database backups
- [ ] Test error handling doesn't leak info
- [ ] Verify session cookies have secure flags

## Security Contact

For security issues or questions:
1. Review `/SECURITY_HARDENING_SUMMARY.md`
2. Check `/DEPLOYMENT.md` security section
3. Run security tests for validation
4. Monitor logs for suspicious activity
