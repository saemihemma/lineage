# Session Cookie Fix - Cross-Origin Development Issue

## Problem

When running:
- Frontend on `http://localhost:5173` (Vite dev server)
- Backend on `http://localhost:8000` (FastAPI)

**Symptoms:**
- Build womb completes but state isn't saved
- Can't build clone after womb completes
- Username doesn't show in top panel
- Each action creates a new session

**Root Cause:**
Cookies with `SameSite=lax` are **blocked in cross-origin requests**.

```python
# backend/routers/game.py (current setting)
response.set_cookie(
    key="session_id",
    value=sid,
    httponly=True,
    samesite="lax",  # ← Blocks cross-origin cookies!
    secure=IS_PRODUCTION
)
```

## Solution 1: Access Frontend via Backend (RECOMMENDED)

The backend already serves the frontend at `/simulation`.

**Instead of:**
```
http://localhost:5173  ← Cross-origin, cookies don't work
```

**Use:**
```
http://localhost:8000/simulation  ← Same-origin, cookies work!
```

### Steps:
1. Build frontend: `cd frontend && npm run build`
2. Start backend: `python3 backend/main.py`
3. Access: `http://localhost:8000/simulation`

**Benefits:**
- No cross-origin issues
- Same as production
- No code changes needed

## Solution 2: Fix Cookie Settings for Cross-Origin Development

If you must use Vite dev server (localhost:5173), fix cookie settings:

### A. Update Cookie Settings

```python
# backend/routers/game.py

# Add at top of file:
import os
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"
IS_DEVELOPMENT = not IS_PRODUCTION

# Update all set_cookie calls:
response.set_cookie(
    key="session_id",
    value=sid,
    httponly=True,
    samesite="none" if IS_DEVELOPMENT else "lax",  # ← FIX: none for dev
    secure=False if IS_DEVELOPMENT else True,       # ← FIX: false for dev (HTTP)
    max_age=SESSION_EXPIRY
)

# Do the same for csrf_token cookie
response.set_cookie(
    key="csrf_token",
    value=csrf_token,
    httponly=False,
    samesite="none" if IS_DEVELOPMENT else "lax",  # ← FIX
    secure=False if IS_DEVELOPMENT else True,       # ← FIX
    max_age=SESSION_EXPIRY
)
```

### B. Update CORS to Allow Credentials

```python
# backend/main.py

# CORS middleware (already correct)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # ← Required for cookies
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"],  # ← Required for CSRF
)
```

### C. Update Frontend API URL

```typescript
// frontend/.env.development (create this file)
VITE_API_URL=http://localhost:8000
```

## Testing the Fix

### Test Cross-Origin Cookies:

1. Open browser DevTools → Application → Cookies
2. Access `http://localhost:5173`
3. Click "Build Womb"
4. Check cookies:
   - ✅ Should see `session_id` cookie
   - ✅ Should see `csrf_token` cookie
   - ✅ Both should have `SameSite=None` in development

### Test Session Persistence:

1. Build womb → Wait for completion
2. Refresh page
3. Username should still show in top panel ✅
4. Womb should still be built ✅
5. Resources should be correct ✅

## Recommended Approach

**For Development:**
Use Solution 1 (access via backend) - simplest and matches production.

**For Production:**
- Frontend served by backend at `/simulation`
- `SameSite=lax` is correct (same-origin)
- `Secure=true` required (HTTPS)

## Browser DevTools Checks

Open DevTools → Application → Cookies → `http://localhost:8000` or `http://localhost:5173`

**Should see:**
```
Name: session_id
Value: <uuid>
Domain: localhost
Path: /
Expires: 24 hours from now
HttpOnly: ✅ Yes
Secure: ❌ No (dev) / ✅ Yes (prod)
SameSite: None (dev) / Lax (prod)
```

```
Name: csrf_token
Value: <timestamp|uuid|signature>
Domain: localhost
Path: /
Expires: 24 hours from now
HttpOnly: ❌ No (client needs to read it)
Secure: ❌ No (dev) / ✅ Yes (prod)
SameSite: None (dev) / Lax (prod)
```

## Common Issues

### Issue: Cookies not appearing
**Cause:** `credentials: 'include'` not set in fetch
**Fix:** Already set in `frontend/src/api/game.ts:27`

### Issue: CORS error
**Cause:** Backend not allowing credentials
**Fix:** Already fixed in `backend/main.py` (`allow_credentials=True`)

### Issue: Session resets on refresh
**Cause:** Cookie not persisting (SameSite issue)
**Fix:** Use Solution 1 or Solution 2

### Issue: "Build womb" works once, then fails
**Cause:** New session created on each request (cookie not sent)
**Fix:** Cookies need `SameSite=none` for cross-origin or use Solution 1

## Security Note

**Development:**
- `SameSite=none` + `Secure=false` is OK for localhost development
- Allows cross-origin testing with Vite dev server

**Production:**
- `SameSite=lax` + `Secure=true` is REQUIRED
- Prevents CSRF attacks
- Requires HTTPS

## Summary

| Setup | Frontend URL | Backend URL | Cookie Settings | Works? |
|-------|-------------|-------------|-----------------|--------|
| Production | https://example.com/simulation | https://example.com/api | SameSite=lax, Secure=true | ✅ Yes |
| Dev (Recommended) | http://localhost:8000/simulation | http://localhost:8000/api | SameSite=lax, Secure=false | ✅ Yes |
| Dev (Vite server) | http://localhost:5173 | http://localhost:8000/api | SameSite=lax, Secure=false | ❌ No |
| Dev (Vite + Fix) | http://localhost:5173 | http://localhost:8000/api | SameSite=none, Secure=false | ✅ Yes |

**Recommendation:** Use "Dev (Recommended)" setup - access frontend via backend.
