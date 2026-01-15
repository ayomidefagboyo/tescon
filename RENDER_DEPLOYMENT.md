# Deploy Backend to Render - Step by Step Guide

## Prerequisites

1. GitHub account with your code pushed to a repository
2. Render account (sign up at https://render.com - free tier available)
3. PicWish API key (get from https://picwish.com/api-pricing)

## Step 1: Prepare Your Repository

Make sure your code is pushed to GitHub:

```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

**Important**: Ensure `.env` file is in `.gitignore` (never commit API keys!)

## Step 2: Create Render Account

1. Go to https://render.com
2. Sign up with GitHub (recommended for easy repo connection)
3. Verify your email

## Step 3: Deploy Using render.yaml (Recommended)

### Option A: Automatic Deployment with render.yaml

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +"** → **"Blueprint"**
3. **Connect your GitHub repository**
4. **Select your repository** (`tescon`)
5. **Render will detect `render.yaml`** and configure everything automatically
6. **Add Environment Variable**:
   - Click on the service
   - Go to "Environment" tab
   - Add: `PICWISH_API_KEY` = `your_api_key_here`
   - Click "Save Changes"
7. **Deploy**: Render will automatically deploy

### Option B: Manual Web Service Creation

If you prefer manual setup:

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +"** → **"Web Service"**
3. **Connect GitHub** and select your repository
4. **Configure Service**:
   - **Name**: `tescon-backend`
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **Add Environment Variables**:
   ```
   PICWISH_API_KEY=your_api_key_here
   UPLOAD_DIR=uploads
   PROCESSED_DIR=processed
   CLEANUP_TTL_HOURS=24
   MAX_FILE_SIZE=100
   BATCH_SIZE=500
   MAX_CONCURRENT=10
   ```
6. **Add Persistent Disk** (for file storage):
   - Go to "Disks" tab
   - Click "Create Disk"
   - Name: `tescon-storage`
   - Mount Path: `/opt/render/project/src`
   - Size: 1GB (free tier)
7. **Click "Create Web Service"**

## Step 4: Wait for Deployment

- Render will build and deploy your service
- First deployment takes 5-10 minutes
- You'll see build logs in real-time
- Once deployed, you'll get a URL like: `https://tescon-backend.onrender.com`

## Step 5: Verify Deployment

1. **Check Health Endpoint**:
   ```
   https://your-service-name.onrender.com/health
   ```
   Should return: `{"status":"healthy","gpu_available":false,"model_loaded":true}`

2. **Check API Docs**:
   ```
   https://your-service-name.onrender.com/docs
   ```
   Should show Swagger UI

## Step 6: Update Frontend (if needed)

If your frontend needs to connect to the Render backend:

1. Update frontend environment variable:
   ```
   VITE_API_URL=https://your-service-name.onrender.com/api
   ```

## Troubleshooting

### Build Fails

- Check build logs in Render dashboard
- Ensure `requirements.txt` is in the `backend` directory
- Verify Python version in `runtime.txt` (should be `python-3.11`)

### Service Crashes

- Check logs in Render dashboard
- Verify `PICWISH_API_KEY` is set correctly
- Check that port is using `$PORT` environment variable

### Files Not Persisting

- Ensure persistent disk is mounted correctly
- Check disk mount path matches in settings

### API Key Issues

- Verify `PICWISH_API_KEY` is set in Environment Variables
- Check it's not in `.env` file (which shouldn't be committed)
- Re-deploy after adding environment variables

## Render Free Tier Limits

- **512MB RAM**
- **0.1 CPU**
- **1GB Persistent Disk**
- **Service sleeps after 15 minutes of inactivity** (wakes on first request)
- **750 hours/month free** (enough for 24/7 small app)

## Cost

- **Free tier**: $0/month (with limits above)
- **Starter plan**: $7/month (no sleep, more resources)

## Next Steps

After backend is deployed:

1. Note your backend URL (e.g., `https://tescon-backend.onrender.com`)
2. Deploy frontend to Vercel/Netlify
3. Update frontend `VITE_API_URL` to point to Render backend
4. Test the full application

## Support

- Render Docs: https://render.com/docs
- Render Status: https://status.render.com
- Render Community: https://community.render.com
