# Railway Persistent Storage Setup for LINEAGE

This guide shows you how to set up persistent storage on Railway so game states survive redeployments.

## Two Options: Volumes (SQLite) or PostgreSQL

You have two options:
1. **SQLite with Volumes** (if Volumes tab is available)
2. **PostgreSQL** (Easier! Recommended - Railway provides it automatically)

Read below for both options.

## Quick Setup (5 minutes)

### Step 1: Create Persistent Volume in Railway

**Step 1A: Check Settings Tab for Volumes**

1. Go to your Railway project dashboard: https://railway.app
2. Click on your **backend service** (the one running the FastAPI server)
3. Click the **Settings** tab (next to Variables, Metrics, etc.)
4. Scroll down in the Settings page
5. Look for a **"Volumes"** or **"Storage"** section
6. If you see it, click **+ New Volume** or **Add Volume**
7. Fill in:
   - **Volume Name**: `lineage-data`
   - **Mount Path**: `/app/data`
8. Click **Add** or **Create**

**Step 1B: If Volumes Section Not in Settings**

Volumes may only be available on certain Railway plans. Try:

**Alternative 1: Check if you need to upgrade**
- Railway Volumes are available on paid plans
- Free tier might not include volumes
- Check Railway pricing: https://railway.app/pricing

**Alternative 2: Use Railway PostgreSQL (Recommended)**
Instead of SQLite with volumes, use Railway's built-in PostgreSQL:
1. In Railway dashboard, click **+ New** → **Database** → **PostgreSQL**
2. Railway auto-creates a PostgreSQL database
3. Railway automatically provides `DATABASE_URL` environment variable
4. The backend code already supports PostgreSQL!
5. No volume setup needed - PostgreSQL persists automatically
6. **This is actually better** than SQLite for production

**Alternative 3: Contact Railway Support**
- If you're on a paid plan but don't see volumes, contact Railway support
- They can help enable it or clarify plan features

### Step 2: Set Database Path Environment Variable

1. Still in your backend service, go to **Variables** tab
2. Click **+ New Variable**
3. Add:
   - **Name**: `DATABASE_URL`
   - **Value**: `sqlite:////app/data/lineage.db`
   - (Note: **4 slashes** - `sqlite:////` means SQLite protocol + absolute path)
4. Click **Add**

### Step 3: Redeploy

1. Railway will automatically detect the new volume
2. Click **Deploy** or **Redeploy** button (or wait for auto-deploy if enabled)
3. The service will restart and use the persistent volume

## How It Works

- **Before**: Database was in `/app/lineage.db` (ephemeral, lost on redeploy)
- **After**: Database is in `/app/data/lineage.db` (persistent, survives redeploy)
- The `/app/data` directory is mounted to a Railway volume
- All files in `/app/data` persist across deployments

## Verification

### Check Volume is Mounted

1. Go to Railway dashboard → Your service → **Volumes**
2. You should see `lineage-data` volume mounted at `/app/data`

### Test Persistence

1. Play the game and create some progress
2. Trigger a redeploy (or wait for auto-deploy)
3. Refresh the game page
4. Your progress should still be there!

### Check Logs (Optional)

After redeploy, check logs for database path:
```
Looking for: "database" or "lineage.db"
Should see references to: /app/data/lineage.db
```

## Troubleshooting

### Issue: Data still lost after redeploy

**Solutions:**
1. **Verify volume exists**: Railway dashboard → Volumes tab → Should see `lineage-data`
2. **Check mount path**: Must be exactly `/app/data` (not `/data` or `/app/storage`)
3. **Verify environment variable**: Variables tab → `DATABASE_URL` must be `sqlite:////app/data/lineage.db`
4. **Check service is using volume**: Look at service configuration → Volumes section

### Issue: Permission errors

**Solutions:**
- Railway volumes should have correct permissions automatically
- If you see permission errors in logs, the volume mount path might be wrong
- Try: Make sure volume mount path is `/app/data` (absolute path)

### Issue: Volume not showing up

**Solutions:**
- Make sure you're in the **backend service** (not frontend service)
- Refresh the Railway dashboard
- Check that Railway plan supports volumes (all paid plans do)

## Current Configuration

The database code (`backend/database.py`) automatically:
- Reads `DATABASE_URL` environment variable
- Creates the directory if it doesn't exist (for volume mounts)
- Falls back to `sqlite:///lineage.db` if not set (relative path, ephemeral)

## What Persists vs What Doesn't

**Persists (on volume):**
- Game states (`game_states` table)
- Leaderboard entries
- Telemetry events
- All SQLite data

**Doesn't Persist (ephemeral):**
- Logs (unless you set up log persistence)
- Temporary files
- Node modules (frontend)
- Build artifacts

## Cost

- Railway volumes: **Free for small sizes** (first few GB)
- Charges apply as volume grows (check Railway pricing)
- For MVP with small user base: **Likely free**

## Future: Upgrade to PostgreSQL

When you need more scale:
1. Add Railway PostgreSQL service (Railway dashboard → + New → PostgreSQL)
2. Railway auto-provides `DATABASE_URL` (PostgreSQL connection string)
3. Remove volume mount (no longer needed)
4. Database code automatically uses PostgreSQL (supports both SQLite and PostgreSQL)
5. No code changes needed!

## Summary

**What you did:**
1. ✅ Created volume: `lineage-data` at `/app/data`
2. ✅ Set environment: `DATABASE_URL=sqlite:////app/data/lineage.db`
3. ✅ Redeployed

**Result:**
- ✅ Game states persist across redeployments
- ✅ Users keep their progress when you deploy updates
- ✅ Database survives server restarts

