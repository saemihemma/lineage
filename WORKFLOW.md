# LINEAGE Development & Deployment Workflow

Complete guide to the development, deployment, and iteration process for LINEAGE web version.

## Architecture Overview

```
┌─────────────────────────────────────┐
│   GitHub Repository                  │
│   (web-version branch)               │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌──────────┐    ┌──────────┐
│ Backend  │    │ Frontend │
│ Railway   │    │ Railway   │
└──────────┘    └──────────┘
```

**Services:**
- **Backend**: `lineage-production.up.railway.app`
  - Root Directory: project root (empty)
  - Build Command: `pip install -r backend/requirements.txt`
  - Start Command: `cd backend && python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT`
  
- **Frontend**: `wonderful-wisdom-production.up.railway.app`
  - Root Directory: `frontend`
  - Build Command: `npm run build`
  - Start Command: `npx serve dist -p $PORT`

---

## Development Workflow

### 1. Making Changes

**When I (AI) make code changes:**
1. I edit files locally in your workspace
2. I commit changes with descriptive messages
3. **You need to push**: `git push origin web-version`

**When you make code changes:**
1. Edit files as needed
2. Commit: `git add . && git commit -m "Your message"`
3. Push: `git push origin web-version`

### 2. Testing Before Push (REQUIRED)

**MANDATORY**: Always run tests before pushing to production!

```bash
# Run all unit tests
python3 scripts/verify.py

# Or run specific test suites
python3 -m unittest discover -v tests/
python3 -m unittest test_frontier.py test_loading_screen.py
```

**Test Enforcement:**
- See `TESTING.md` for details on test requirements
- Tests must pass before pushing to `web-version` branch
- New features require new tests

### 3. Deploying Changes

#### Automatic Deployment (Recommended)

**If Railway is connected to GitHub:**
- ✅ Push to `web-version` branch
- ✅ Railway automatically detects the push
- ✅ Railway rebuilds and redeploys (takes 2-3 minutes)
- ✅ No manual action needed

**To check if auto-deploy is enabled:**
- Railway → Service → Settings → Source
- Should show "Connected to GitHub" and branch name

#### Manual Deployment

If auto-deploy isn't working:
1. Railway → Service → Deployments
2. Click "Deploy Now" or "Redeploy"
3. Wait for build to complete

---

## Step-by-Step: Making and Deploying a Fix

### Scenario: I fix a bug in the frontend

**Step 1: I make the change**
- I edit `frontend/src/api/game.ts` (e.g., add `getTaskStatus()`)
- I commit: `git commit -m "Add getTaskStatus method to game API"`

**Step 2: Run tests**
```bash
python3 scripts/verify.py
```
- If tests fail, fix issues before proceeding

**Step 3: You push to GitHub**
```bash
git push origin web-version
```

**Step 4: Railway auto-deploys**
- Railway detects the push
- Frontend service starts rebuilding
- Takes ~2-3 minutes
- You'll see logs in Railway → Deployments

**Step 5: Verify**
- Check Railway logs for successful build
- Visit frontend URL to test the fix
- Done! ✅

---

## When Rebuilds Are Needed

### Always Requires Rebuild:
- ✅ **Code changes** (Python, TypeScript, React components)
- ✅ **Dependencies** (requirements.txt, package.json changes)
- ✅ **Configuration** (railway.json, Procfile changes)
- ✅ **Environment variables** (changes require redeploy)

### Doesn't Require Rebuild:
- ❌ **Static data files** (if served directly, like `/data/briefing_text.json`)
  - But if they're bundled in the build, they DO need rebuild

### Partial Rebuilds:
- **Backend only**: Only backend service rebuilds
- **Frontend only**: Only frontend service rebuilds
- **Both**: If you change shared code or config

---

## Environment Variables

### Backend (Railway)
- `ENVIRONMENT=production`
- `ALLOWED_ORIGINS=https://wonderful-wisdom-production.up.railway.app`

### Frontend (Railway)
- `VITE_API_URL=https://lineage-production.up.railway.app`

**Important**: If you change environment variables:
1. Update in Railway dashboard
2. **Redeploy** the service (Railway may auto-redeploy, or click "Deploy Now")

**Note**: Vite environment variables are baked into the build at build time. If you change `VITE_API_URL`, you MUST rebuild the frontend.

---

## Quick Reference Commands

### Local Development

```bash
# Run backend locally
cd backend
python3 main.py
# Or: uvicorn main:app --reload

# Run frontend locally
cd frontend
npm run dev
# Frontend at http://localhost:5173

# Sync data files (briefing text, etc.)
npm run sync-data  # (from project root)
```

### Testing

```bash
# Run all tests (REQUIRED before push)
python3 scripts/verify.py

# Run specific test files
python3 -m unittest test_frontier.py -v
python3 -m unittest test_loading_screen.py -v

# Run backend tests
cd backend && python3 -m pytest tests/ -v
```

### Git Commands

```bash
# Check status
git status

# Stage all changes
git add .

# Commit with message
git commit -m "Description of changes"

# Push to web-version branch (AFTER tests pass!)
git push origin web-version

# See recent commits
git log --oneline -5
```

### Railway Commands (via Dashboard)

1. **Check deployment status**: Railway → Service → Deployments
2. **View logs**: Railway → Service → Logs
3. **Redeploy**: Railway → Service → Deployments → "Deploy Now"
4. **Check environment variables**: Railway → Service → Settings → Variables

---

## Troubleshooting

### "Changes aren't showing up"

1. **Did you push?**
   ```bash
   git push origin web-version
   ```

2. **Is Railway auto-deploying?**
   - Check Railway → Deployments for latest deployment
   - If no new deployment, trigger manually

3. **Did the build succeed?**
   - Check Railway → Logs for errors
   - Red X means build failed

4. **Environment variable change?**
   - Vite env vars require rebuild
   - Update variable → Redeploy

### "Backend not responding"

1. Check backend logs in Railway
2. Verify backend is running (green status)
3. Test: `https://lineage-production.up.railway.app/api/health`

### "CORS errors"

1. Check `ALLOWED_ORIGINS` includes frontend URL
2. Ensure `ENVIRONMENT=production`
3. Redeploy backend after changing CORS settings

### "Tests failing"

1. Read error messages carefully
2. Fix failing tests before pushing
3. See `TESTING.md` for test requirements

---

## Development Best Practices

### Before Pushing:
1. ✅ **Run tests** (`python3 scripts/verify.py`)
2. ✅ Test changes locally if possible
3. ✅ Commit with clear messages
4. ✅ Check `git status` to see what's changed

### After Pushing:
1. ✅ Monitor Railway deployment logs
2. ✅ Test on live URL
3. ✅ Check browser console for errors

### For Frontend Changes:
- Frontend rebuilds take ~1-2 minutes
- Changes are visible immediately after deployment

### For Backend Changes:
- Backend rebuilds take ~2-3 minutes
- No downtime (Railway does rolling deployments)

### For New Features:
- ✅ Write tests for new functionality
- ✅ Run tests before committing
- ✅ Tests must pass before pushing

---

## File Structure Impact

```
project/
├── backend/          → Backend service (Root Dir: empty, cd backend && ...)
│   ├── main.py       → Changes need backend rebuild
│   └── requirements.txt → Changes need backend rebuild
│
├── frontend/         → Frontend service (Root Dir: frontend)
│   ├── src/          → Changes need frontend rebuild
│   └── package.json  → Changes need frontend rebuild
│
├── game/             → Shared (backend imports this)
│   └── state.py      → Changes need backend rebuild
│
├── core/             → Shared (backend imports this)
│   └── ...           → Changes need backend rebuild
│
├── railway.json      → Changes need rebuild (both services)
└── Procfile          → Changes need rebuild (both services)
```

---

## Typical Workflow Examples

### Example 1: Fix Frontend Bug

```
1. I edit frontend/src/api/game.ts
2. I run tests: python3 scripts/verify.py
3. I commit: "Fix getTaskStatus method"
4. You run: git push origin web-version
5. Railway auto-detects push
6. Frontend service rebuilds (2 min)
7. Fix is live!
```

### Example 2: Add Backend Endpoint

```
1. I edit backend/routers/game.py
2. I write tests for new endpoint
3. I run tests: python3 scripts/verify.py
4. I commit: "Add new endpoint with tests"
5. You run: git push origin web-version
6. Railway auto-detects push
7. Backend service rebuilds (3 min)
8. New endpoint is live!
```

### Example 3: Update Environment Variable

```
1. You edit Railway → Settings → Variables
2. Add/update VITE_API_URL
3. Railway asks: "Redeploy?" → Yes
4. Frontend rebuilds (env vars baked in)
5. Change is live!
```

---

## Summary: The Golden Path

1. **Make changes** (code, config, env vars)
2. **Write/update tests** (if new features)
3. **Run tests** → `python3 scripts/verify.py` ✅
4. **Commit** (if code changed)
5. **Push** (if code changed) → `git push origin web-version`
6. **Railway auto-deploys** (or manually trigger)
7. **Wait for build** (~2-3 minutes)
8. **Test on live URL**
9. **Done!** ✅

**Key Points**: 
- Railway watches GitHub, so pushing = deploying (usually)
- **Tests are mandatory** before pushing to production
- New features require new tests

---

## Need Help?

- **Git issues**: Check `git status` and `git log`
- **Railway issues**: Check Railway logs and deployment status
- **Build failures**: Check Railway build logs for error messages
- **Runtime errors**: Check Railway runtime logs and browser console
- **Test failures**: See `TESTING.md` for requirements

