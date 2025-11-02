# Railway Persistent Volume Setup for SQLite

To keep user progress across redeployments, we need to set up a persistent volume for the SQLite database.

## Quick Setup (5 minutes)

### Step 1: Create Volume in Railway

1. Go to your Railway project dashboard
2. Click on your backend service
3. Go to **Volumes** tab (or **Settings** → **Volumes**)
4. Click **+ New Volume**
5. Name it: `lineage-data`
6. Mount path: `/app/data`
7. Click **Add**

### Step 2: Set Environment Variable

1. Still in your backend service settings
2. Go to **Variables** tab
3. Add new variable:
   - **Name**: `DATABASE_URL`
   - **Value**: `sqlite:////app/data/lineage.db`
   - (Note the 4 slashes: `sqlite:////` = protocol + absolute path)
4. Click **Add**

### Step 3: Redeploy

1. Railway will automatically detect the new volume mount
2. Trigger a redeploy (or wait for auto-deploy if enabled)
3. The database will now persist in `/app/data/lineage.db`

## Verification

After redeploy:

1. Check logs to confirm database path:
   ```
   grep -i "database\|lineage.db" railway logs
   ```
   Should see references to `/app/data/lineage.db`

2. Test: Create a game state, then redeploy. The state should persist.

## Alternative: Using Railway's DATABASE_URL Environment Variable

If Railway auto-provides `DATABASE_URL` (for PostgreSQL), make sure to override it with the SQLite path above, or the database connection code will auto-detect and use the volume path.

## Current Database Configuration

The database code (`backend/database.py`) will:
1. Check for `DATABASE_URL` environment variable
2. If not set, default to `sqlite:///lineage.db` (relative path)
3. Convert `sqlite:///` URLs to file paths

With the volume setup above:
- `DATABASE_URL=sqlite:////app/data/lineage.db` → `/app/data/lineage.db` (persistent)
- This file survives redeployments because it's on a mounted volume

## Troubleshooting

### Database file not found after redeploy
- Check volume is mounted: Railway dashboard → Volumes
- Verify `DATABASE_URL` points to volume path: `/app/data/lineage.db`
- Check volume mount path matches what's in Railway settings

### Permission errors
- Railway volumes should have correct permissions automatically
- If issues, check logs for permission errors

### Data still lost after redeploy
- Verify volume is actually mounted (check Railway dashboard)
- Check that `DATABASE_URL` environment variable is set correctly
- Ensure database code is reading from the volume path (check logs)

## Notes

- **Volume size**: Railway volumes start small and expand as needed
- **Backups**: SQLite doesn't auto-backup. Consider periodic backups or upgrade to PostgreSQL later
- **Performance**: SQLite is fine for MVP, but PostgreSQL is better for production scale

## Migration Path (Future)

When ready to upgrade to PostgreSQL:
1. Add Railway PostgreSQL service
2. Railway provides `DATABASE_URL` automatically (PostgreSQL connection string)
3. Remove volume mount (no longer needed)
4. Update `DATABASE_URL` to use PostgreSQL connection string
5. Database migration happens automatically (code supports both SQLite and PostgreSQL)

