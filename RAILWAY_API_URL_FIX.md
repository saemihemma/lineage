# Fixing Railway API URL Configuration

## Problem
Frontend is trying to connect to `https://lineage-production.up.railway.app` but getting network errors.

## Solution Steps

### Option 1: Check Railway Backend Service URL

1. Go to Railway dashboard
2. Find your **backend service**
3. Click on it → Settings → Networking
4. Find the **Public Domain** or **Custom Domain**
5. Copy the full URL (e.g., `https://wonderful-wisdom-production.up.railway.app`)

### Option 2: Set VITE_API_URL on Frontend Service

1. In Railway dashboard, go to your **frontend service**
2. Go to **Variables** tab
3. Add/update environment variable:
   ```
   VITE_API_URL=https://YOUR-BACKEND-SERVICE.up.railway.app
   ```
   Replace `YOUR-BACKEND-SERVICE` with your actual backend service URL

4. **Redeploy** the frontend service (Railway should auto-redeploy when you change env vars)

### Option 3: Use Railway Service URL (Internal Network)

If your frontend and backend are in the same Railway project, you can use the internal service URL:

1. In backend service → Settings → Networking
2. Find the **Private Network** or **Service URL**
3. Use that as `VITE_API_URL` (e.g., `http://backend-service:8000`)
   - **Note**: This only works if both services are in the same Railway project

### Option 4: Check Both Services Are Deployed

1. Verify backend service is **running** and **deployed successfully**
2. Verify frontend service is **running** and **deployed successfully**
3. Check backend logs for any startup errors
4. Check frontend build logs for any errors

## Quick Debug Steps

1. **Test backend directly**: Open `https://YOUR-BACKEND-URL/api/health` in browser
   - Should return: `{"status":"healthy"}`

2. **Check CORS**: Backend should allow your frontend URL in `ALLOWED_ORIGINS`

3. **Check Railway logs**: 
   - Backend logs → Look for "Application startup complete"
   - Frontend logs → Look for build success and `VITE_API_URL` value

4. **Verify environment variables**:
   - Frontend service should have `VITE_API_URL` set
   - Backend service should have `ALLOWED_ORIGINS` including your frontend URL

## Common Issues

- **Wrong URL**: `VITE_API_URL` points to non-existent or wrong service
- **CORS blocked**: Backend doesn't allow frontend origin
- **Service not running**: Backend service crashed or failed to deploy
- **Port mismatch**: Backend uses different port than expected (Railway usually handles this automatically)

