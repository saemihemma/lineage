# Database Persistence Guide - Prevent Progress Loss on Redeployment

## 🚨 The Problem

**Currently:** SQLite database is stored in **ephemeral storage** (temporary filesystem)

**What this means:**
- ✅ Works fine while app is running
- ❌ **Database wiped on every redeploy**
- ❌ All player progress lost on code updates
- ❌ Sessions expire after redeploy

**Why it happens:**
Railway's default filesystem is ephemeral - it gets recreated on every deployment. The `lineage.db` file is created in the app directory, which gets wiped.

---

## ✅ Solution 1: Railway Volumes (Quick Fix for SQLite)

**Best for:** Development, small-scale deployments, quick fix

Railway provides persistent volumes that survive redeployments.

### Step-by-Step Setup

#### 1. Create a Volume in Railway

1. Go to your Railway project
2. Click your backend service
3. Go to **"Variables"** tab
4. Scroll down to **"Volumes"**
5. Click **"+ New Volume"**
6. Configure:
   - **Mount Path**: `/app/data`
   - **Size**: 1GB (should be plenty for game states)
7. Click **"Add"**

#### 2. Update Backend to Use Volume

Update `backend/database.py` to use the volume:

```python
# At the top of database.py, modify the default path:
if db_path is None:
    # Check if we're on Railway with a volume
    if os.path.exists("/app/data"):
        db_path = "/app/data/lineage.db"
    else:
        db_path = os.getenv("DATABASE_URL", "sqlite:///lineage.db")
    # ... rest of existing code
```

Or simpler - set environment variable in Railway:

```bash
DATABASE_URL=sqlite:////app/data/lineage.db
```

#### 3. Redeploy

```bash
git push origin web-version
```

Railway will:
1. Create the volume
2. Mount it at `/app/data`
3. Database will be created at `/app/data/lineage.db`
4. **Database persists across redeployments!**

### Pros & Cons

**Pros:**
- ✅ Quick and easy (5 minutes setup)
- ✅ No code changes needed (just env var)
- ✅ Free on Railway
- ✅ Keeps SQLite (no migration needed)

**Cons:**
- ⚠️ Limited to 1GB storage
- ⚠️ SQLite doesn't handle high concurrency well
- ⚠️ Volume is tied to single Railway instance (no multi-region)
- ⚠️ Manual backups required

---

## ✅ Solution 2: PostgreSQL (Recommended for Production)

**Best for:** Production, scaling, reliability

Railway provides managed PostgreSQL that's persistent by default.

### Step-by-Step Migration

#### 1. Add PostgreSQL to Railway Project

1. In Railway dashboard, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway will:
   - Create a PostgreSQL instance
   - Generate connection credentials
   - Set `DATABASE_URL` environment variable automatically

#### 2. Install PostgreSQL Driver

Update `backend/requirements.txt`:

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.4.2
httpx==0.27.0
python-multipart==0.0.6
psycopg2-binary==2.9.9  # ADD THIS LINE
```

#### 3. Update Database Code (Already Compatible!)

Good news: Your `backend/database.py` already supports PostgreSQL via `DATABASE_URL` environment variable. No code changes needed!

The existing code:
```python
db_path = os.getenv("DATABASE_URL", "sqlite:///lineage.db")
```

Will automatically work with PostgreSQL connection strings like:
```
postgresql://user:pass@host:5432/dbname
```

#### 4. Deploy

```bash
# Add psycopg2 to requirements
echo "psycopg2-binary==2.9.9" >> backend/requirements.txt

# Commit and push
git add backend/requirements.txt
git commit -m "feat: add PostgreSQL support for persistent database"
git push origin web-version
```

Railway will:
1. Detect new PostgreSQL dependency
2. Use `DATABASE_URL` from PostgreSQL service
3. Create tables automatically on first run
4. **Database persists forever!**

### Pros & Cons

**Pros:**
- ✅ Professional production database
- ✅ Handles high concurrency
- ✅ Automatic backups by Railway
- ✅ Scales better
- ✅ No storage limits (pay as you grow)
- ✅ Survives redeployments automatically

**Cons:**
- ⚠️ Costs money after free tier (~$5/month on Railway)
- ⚠️ Slightly more complex setup
- ⚠️ Need to migrate existing data (if any)

---

## 🔄 Migrating Existing Data (SQLite → PostgreSQL)

If you already have player data in SQLite and want to migrate:

### Option A: Export/Import Script

Create `scripts/migrate_db.py`:

```python
import sqlite3
import psycopg2
import os
import json

# Connect to SQLite
sqlite_conn = sqlite3.connect('lineage.db')
sqlite_conn.row_factory = sqlite3.Row

# Connect to PostgreSQL
pg_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
pg_cursor = pg_conn.cursor()

# Create tables in PostgreSQL (run backend once to create schema)
# Then migrate data

# Migrate game_states
sqlite_cursor = sqlite_conn.cursor()
sqlite_cursor.execute("SELECT * FROM game_states")
for row in sqlite_cursor.fetchall():
    pg_cursor.execute(
        "INSERT INTO game_states (session_id, state_data, created_at, updated_at) VALUES (%s, %s, %s, %s)",
        (row['session_id'], row['state_data'], row['created_at'], row['updated_at'])
    )

# Migrate leaderboard
sqlite_cursor.execute("SELECT * FROM leaderboard")
for row in sqlite_cursor.fetchall():
    pg_cursor.execute(
        "INSERT INTO leaderboard (id, self_name, soul_level, soul_xp, clones_uploaded, total_expeditions, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (row['id'], row['self_name'], row['soul_level'], row['soul_xp'], row['clones_uploaded'], row['total_expeditions'], row['created_at'], row['updated_at'])
    )

pg_conn.commit()
print("Migration complete!")
```

### Option B: Start Fresh

Since this is a prototype, you might just:
1. Set up PostgreSQL
2. Redeploy
3. Let players start fresh (it's a game, they expect resets in beta)

---

## 💾 Backup Strategy

### SQLite with Volume

**Manual Backups:**

```bash
# SSH into Railway container (if possible)
railway run bash

# Copy database file
cp /app/data/lineage.db /app/data/lineage.db.backup

# Download to local machine
railway run cat /app/data/lineage.db > lineage.db.local
```

**Automated Backups:**

Add to `backend/main.py`:

```python
import shutil
from pathlib import Path
from datetime import datetime

@app.on_event("startup")
async def backup_database():
    """Create daily backup of database"""
    db_path = Path("/app/data/lineage.db")
    if db_path.exists():
        backup_dir = Path("/app/data/backups")
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"lineage_backup_{timestamp}.db"

        shutil.copy(db_path, backup_path)
        logger.info(f"Database backed up to {backup_path}")

        # Keep only last 7 days
        backups = sorted(backup_dir.glob("*.db"))
        for old_backup in backups[:-7]:
            old_backup.unlink()
```

### PostgreSQL with Railway

**Automatic Backups:**
- Railway automatically backs up PostgreSQL databases
- Retention: 7 days on free tier, 30 days on paid

**Manual Backup:**

```bash
# From Railway dashboard
# Go to PostgreSQL service → Data → "Create Backup"

# Or via CLI
railway run pg_dump $DATABASE_URL > backup.sql
```

**Restore:**

```bash
railway run psql $DATABASE_URL < backup.sql
```

---

## 📋 Recommended Approach

### For Development/Prototype (Now)
**Use Solution 1: Railway Volume**
- Quick setup (5 minutes)
- Free
- Good enough for testing

### For Production/Launch (Later)
**Migrate to Solution 2: PostgreSQL**
- Professional setup
- Scales properly
- Automatic backups
- Worth the $5/month

---

## 🚀 Quick Start: Implement Right Now

### Fastest Fix (Railway Volume)

1. **In Railway Dashboard:**
   - Go to your backend service
   - Variables → Volumes → + New Volume
   - Mount path: `/app/data`
   - Size: 1GB

2. **Set Environment Variable:**
   ```
   DATABASE_URL=sqlite:////app/data/lineage.db
   ```

3. **Redeploy** (just click "Redeploy" in Railway)

**Done!** Database now persists across redeployments.

---

## 🔍 Verify Persistence

### Test It

1. Deploy with volume configured
2. Play the game (build womb, create clones)
3. Trigger a redeployment:
   ```bash
   git commit --allow-empty -m "test: verify database persistence"
   git push origin web-version
   ```
4. Wait for redeploy to complete
5. Open game
6. **Expected:** Your progress is still there! ✅

---

## 📊 Comparison

| Feature | SQLite (Ephemeral) | SQLite + Volume | PostgreSQL |
|---------|-------------------|-----------------|------------|
| **Persists on redeploy** | ❌ | ✅ | ✅ |
| **Setup time** | 0 min | 5 min | 15 min |
| **Cost** | Free | Free | ~$5/mo |
| **Concurrent users** | ~10 | ~10 | 1000+ |
| **Automatic backups** | ❌ | ❌ | ✅ |
| **Storage limit** | N/A | 1GB | Unlimited* |
| **Production ready** | ❌ | ⚠️ | ✅ |

*Unlimited but costs scale with size

---

## 🎯 Action Items

**To prevent database wipes, do ONE of these:**

### Option 1: Quick Fix (5 minutes)
```bash
# In Railway:
# 1. Add volume at /app/data
# 2. Set DATABASE_URL=sqlite:////app/data/lineage.db
# 3. Redeploy
```

### Option 2: Production Setup (15 minutes)
```bash
# In Railway:
# 1. Add PostgreSQL service
# 2. Add psycopg2-binary to requirements.txt
# 3. Redeploy (DATABASE_URL auto-set)
```

**Choose based on:**
- Testing/development → Option 1
- Going to production → Option 2

---

## 📞 Need Help?

Common issues:

**"Volume not mounting"**
- Check Railway logs for mount errors
- Verify mount path is exactly `/app/data`

**"PostgreSQL connection failed"**
- Check `DATABASE_URL` is set correctly
- Ensure `psycopg2-binary` is in requirements.txt
- Check PostgreSQL service is running

**"Data still wiped"**
- Verify database path is in volume mount
- Check Railway logs for database location
- Ensure `DATABASE_URL` env var is correct

---

Let me know which option you want to implement and I can help set it up! 🚀
