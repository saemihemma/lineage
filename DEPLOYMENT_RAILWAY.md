# Railway Deployment Guide for LINEAGE Web Version

## Quick Setup

### 1. In Railway Dashboard

When setting up your Railway service:

**Important Settings:**
- **Root Directory**: Set to `backend/` (this is critical!)
  - This tells Railway to only look in the `backend/` folder
  - Prevents it from finding root `main.py` (desktop version)
- **Start Command**: Railway will auto-detect from `Procfile` or you can set:
  ```
  python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT
  ```

### 2. Environment Variables

Set these in Railway dashboard:

```
ENVIRONMENT=production
ALLOWED_ORIGINS=https://your-frontend-url.railway.app,https://your-frontend-url.vercel.app
PORT=8000
```

### 3. Verify Deployment

1. Check Railway logs - should see:
   ```
   INFO:backend.main:Production mode: allowing specified origins
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

2. Test backend:
   ```bash
   curl https://your-backend-url.railway.app/api/health
   ```

### 4. Frontend Deployment

Deploy frontend separately (Vercel/Netlify recommended):

1. Set environment variable:
   ```
   VITE_API_URL=https://your-backend-url.railway.app
   ```

2. Build and deploy

## Troubleshooting

### "ModuleNotFoundError: No module named 'PIL'"

**Cause**: Railway is running root `main.py` instead of backend

**Fix**: 
1. In Railway dashboard → Settings → Service Settings
2. Set **Root Directory** to: `backend`
3. Redeploy

### Procfile Not Detected

Railway should auto-detect, but if not:
1. Check Root Directory is set to `backend/`
2. Verify `Procfile` is in project root (it will work from backend/ directory too)
3. Or set Start Command manually in Railway dashboard

## Alternative: Explicit Start Command

If Procfile still doesn't work, set this in Railway dashboard:

**Start Command:**
```
cd backend && python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT
```

Or if Root Directory is set to `backend/`:
```
python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT
```

