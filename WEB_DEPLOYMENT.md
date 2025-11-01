# LINEAGE Web Deployment Guide

Complete guide to deploy LINEAGE game for web playability.

## Overview

LINEAGE consists of:
- **Backend API** (FastAPI) - Game logic, state management, leaderboard
- **Frontend** (React + TypeScript) - Web UI, runs in browser

Both need to be deployed and configured to work together.

---

## Part 1: Backend Deployment (Railway)

### Prerequisites
- Railway account (railway.app)
- GitHub repository connected

### Step 1: Create Railway Service

1. Go to Railway dashboard → **New Project**
2. Select **GitHub** → Choose your repository
3. Railway will auto-detect the project
4. **Important**: Click on the service → **Settings** → **Source**

### Step 2: Configure Root Directory

In Railway dashboard:

1. Go to your service → **Settings** → **Source**
2. Find **"Root Directory"** field
3. Set it to: `backend`
4. **Save** (this is critical - prevents PIL errors!)

### Step 3: Configure Start Command

Railway should auto-detect from `Procfile`, but verify:

1. Go to **Settings** → **Deploy**
2. **Start Command** should be:
   ```
   python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
   Or Railway will use the `Procfile` automatically.

### Step 4: Set Environment Variables

Go to **Settings** → **Variables** and add:

```
ENVIRONMENT=production
ALLOWED_ORIGINS=https://your-frontend-url.railway.app,https://your-frontend-url.vercel.app
```

**Note**: Replace with your actual frontend URL(s). You can add multiple URLs separated by commas.

### Step 5: Deploy

1. Railway will auto-deploy on git push
2. Or click **Deploy** → **Deploy Now**
3. Wait for build to complete

### Step 6: Verify Backend

1. Go to **Deployments** → Click latest deployment
2. Copy the **Public URL** (e.g., `https://your-app.up.railway.app`)
3. Test in browser:
   ```
   https://your-backend-url/api/health
   ```
   Should return: `{"status": "healthy", "database": "connected"}`

4. Check **Logs** tab - should see:
   ```
   INFO:backend.main:Production mode: allowing specified origins
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

✅ **Backend is ready!** Copy the public URL for frontend configuration.

---

## Part 2: Frontend Deployment

You have two options:

### Option A: Vercel (Recommended - Fastest Iteration)

1. Go to [vercel.com](https://vercel.com)
2. **New Project** → Import from GitHub
3. Select your repository
4. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build` (auto-detected)
   - **Output Directory**: `dist` (auto-detected)
5. **Environment Variables**:
   ```
   VITE_API_URL=https://your-backend-url.railway.app
   ```
   (Replace with your Railway backend URL)
6. **Deploy**

### Option B: Netlify

1. Go to [netlify.com](https://netlify.com)
2. **Add new site** → **Import from Git**
3. Select repository
4. Configure:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/dist`
5. **Environment Variables**:
   ```
   VITE_API_URL=https://your-backend-url.railway.app
   ```
6. **Deploy**

### Option C: Railway Static (Same Service)

1. Add **Static Files** service in Railway
2. Point to `frontend/dist`
3. Or serve via FastAPI (add static file serving in `backend/main.py`)

**Recommendation**: Use **Vercel** for frontend - fastest deploys, automatic on git push.

---

## Part 3: Configuration

### Backend Environment Variables (Railway)

```
ENVIRONMENT=production
ALLOWED_ORIGINS=https://your-frontend.vercel.app,https://your-frontend.netlify.app
PORT=8000  # Auto-set by Railway
```

### Frontend Environment Variables (Vercel/Netlify)

```
VITE_API_URL=https://your-backend.railway.app
```

**Important**: 
- Vercel/Netlify use `VITE_` prefix for environment variables
- They're baked into the build at build time
- Redeploy frontend after changing environment variables

---

## Part 4: Testing Deployment

### Test Backend

```bash
# Health check
curl https://your-backend.railway.app/api/health

# Create game state
curl https://your-backend.railway.app/api/game/state
```

### Test Frontend

1. Open frontend URL in browser
2. Navigate through screens:
   - Briefing → Loading → Simulation
3. Try game actions:
   - Gather resources
   - Build Womb
   - Grow clones
   - Run expeditions

### Check for Errors

**Backend logs** (Railway → Logs):
- Should see FastAPI startup messages
- No PIL/Tkinter errors
- API requests logged

**Frontend console** (Browser DevTools → Console):
- Should see API calls to backend
- No CORS errors
- No 404s for API endpoints

---

## Part 5: Iteration Workflow

### Quick Iteration Cycle

1. **Make code changes** (frontend or backend)
2. **Commit and push** to GitHub:
   ```bash
   git add .
   git commit -m "Your changes"
   git push
   ```
3. **Automatic deployment**:
   - Railway auto-deploys backend (1-2 minutes)
   - Vercel auto-deploys frontend (30 seconds)
4. **Test changes** on live URL

### Frontend Changes (Fast)

- Edit React components
- Push to GitHub
- Vercel redeploys automatically (~30s)
- Changes live immediately

### Backend Changes (Slower)

- Edit Python code
- Push to GitHub  
- Railway rebuilds and redeploys (~2-3 min)
- Check Railway logs for errors

### Game Data Changes

If you update `data/briefing_text.json` or other data:

```bash
# Sync to frontend
npm run sync-data  # (from project root)
# Or manually:
./scripts/sync_data_to_frontend.sh
```

Then commit and push - frontend will pick up changes.

---

## Troubleshooting

### Backend Issues

**"ModuleNotFoundError: No module named 'PIL'"**
- ✅ **Fix**: Set Root Directory to `backend/` in Railway Settings

**"ModuleNotFoundError: No module named 'backend'"**
- ✅ **Fix**: Already fixed in code - ensure you've pushed latest commits

**CORS errors in browser**
- ✅ **Fix**: Add frontend URL to `ALLOWED_ORIGINS` environment variable

**Database errors**
- ✅ **Fix**: SQLite file should be created automatically. For PostgreSQL, set `DATABASE_URL` env var.

### Frontend Issues

**"Failed to fetch" or CORS errors**
- ✅ **Fix**: Check `VITE_API_URL` is correct
- ✅ **Fix**: Check backend `ALLOWED_ORIGINS` includes frontend URL

**404 errors for API calls**
- ✅ **Fix**: Verify backend URL is correct in `VITE_API_URL`
- ✅ **Fix**: Check backend is actually running (test `/api/health`)

**Game state not saving**
- ✅ **Fix**: Check browser allows cookies (not in incognito mode)
- ✅ **Fix**: Verify backend is storing state (check Railway logs)

---

## Architecture

```
┌─────────────────────────────────────┐
│         User's Browser              │
│  ┌───────────────────────────────┐  │
│  │   Frontend (React/Vite)       │  │
│  │   - Briefing Screen           │  │
│  │   - Loading Screen            │  │
│  │   - Simulation Screen         │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│              │ HTTPS API Calls       │
│              │ (with cookies)       │
└──────────────┼───────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    Backend API (Railway)             │
│  ┌───────────────────────────────┐  │
│  │   FastAPI Server              │  │
│  │   - Game endpoints            │  │
│  │   - Leaderboard API           │  │
│  │   - Telemetry API             │  │
│  │   - SQLite/PostgreSQL DB     │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## URLs After Deployment

After deployment, you'll have:

- **Backend API**: `https://your-backend.railway.app`
  - Health: `https://your-backend.railway.app/api/health`
  - Docs: `https://your-backend.railway.app/docs`

- **Frontend**: `https://your-frontend.vercel.app`
  - Main game: Just open the URL!

---

## Next Steps for Iteration

1. **Deploy backend** → Get backend URL
2. **Deploy frontend** → Point to backend URL
3. **Test end-to-end** → Play the game
4. **Iterate** → Make changes, push, auto-deploy
5. **Monitor** → Check logs for errors

## Tips

- **Fast frontend iteration**: Vercel deploys in ~30 seconds
- **Backend logging**: Check Railway logs for API issues
- **Environment variables**: Change in dashboard, then redeploy
- **Database**: SQLite works for MVP, upgrade to PostgreSQL if needed
- **CORS**: Always include frontend URL in `ALLOWED_ORIGINS`

---

## Quick Reference

**Backend URL Format:**
```
https://[service-name].up.railway.app
```

**Frontend URL Format (Vercel):**
```
https://[project-name].vercel.app
```

**Test Backend:**
```bash
curl https://your-backend.railway.app/api/health
```

**Update CORS (after deploying frontend):**
1. Railway → Variables → `ALLOWED_ORIGINS`
2. Add frontend URL
3. Redeploy backend

---

That's it! Your game should now be playable on the web. 🎮

