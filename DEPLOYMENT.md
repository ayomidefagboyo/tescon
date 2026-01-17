# TESCON Deployment Guide - Free/Cheap Hosting

This guide covers deploying TESCON without Docker using free/cheap hosting services.

## Architecture Overview

- **Backend**: Deploy to Railway or Render (Python/FastAPI)
- **Frontend**: Deploy to Vercel or Netlify (React/Vite)
- **Cost**: **FREE** (with free tier limits)

---

## Option 1: Railway (Recommended - Easiest)

### Backend on Railway

**Railway offers $5 free credit/month** - enough for small to medium usage.

1. **Sign up**: Go to [railway.app](https://railway.app) and sign up with GitHub

2. **Create New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your repository
   - Select the `backend` folder as root

3. **Configure Environment Variables**:
   - Go to your service → Variables tab
   - Add:
     ```
     PICWISH_API_KEY=your_api_key_here
     UPLOAD_DIR=uploads
     PROCESSED_DIR=processed
     CLEANUP_TTL_HOURS=24
     MAX_FILE_SIZE=100
     
     # Google Sheets & Drive (for simplified workflow)
     GOOGLE_SHEETS_ID=your_sheet_id_here
     GOOGLE_SHEETS_TAB_NAME=Sheet1
     GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
     GOOGLE_CREDENTIALS_JSON=base64_encoded_credentials_json
     ```
   - See `backend/GOOGLE_CLOUD_SETUP.md` for detailed setup instructions

4. **Set Start Command**:
   - Go to Settings → Deploy
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Railway automatically sets `$PORT` environment variable

5. **Add Persistent Volume** (for file storage):
   - Go to your service → Settings → Volumes
   - Add volume: `/app/uploads` and `/app/processed`
   - This ensures files persist between deployments

6. **Deploy**:
   - Railway will auto-deploy on git push
   - Copy your backend URL (e.g., `https://tescon-backend.railway.app`)

### Frontend on Vercel (Free)

1. **Sign up**: Go to [vercel.com](https://vercel.com) and sign up with GitHub

2. **Import Project**:
   - Click "Add New Project"
   - Import your GitHub repository
   - Root Directory: `frontend`

3. **Configure Build Settings**:
   - Framework Preset: Vite
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`

4. **Set Environment Variables**:
   - Go to Settings → Environment Variables
   - Add:
     ```
     VITE_API_URL=https://your-backend-url.railway.app/api
     ```
   - Replace with your actual Railway backend URL

5. **Deploy**:
   - Click "Deploy"
   - Vercel will give you a URL like `https://tescon.vercel.app`

**Done!** Your app is live and free.

---

## Option 2: Render (Alternative)

### Backend on Render

1. **Sign up**: Go to [render.com](https://render.com) and sign up

2. **Create New Web Service**:
   - Connect your GitHub repository
   - Root Directory: `backend`
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

3. **Environment Variables**:
   ```
   PICWISH_API_KEY=your_api_key_here
   UPLOAD_DIR=uploads
   PROCESSED_DIR=processed
   ```

4. **Add Persistent Disk** (for file storage):
   - Go to Settings → Persistent Disk
   - Mount paths: `/opt/render/project/src/uploads` and `/opt/render/project/src/processed`
   - Size: 1GB (free tier)

5. **Deploy**: Render will auto-deploy

### Frontend on Netlify (Free)

1. **Sign up**: Go to [netlify.com](https://netlify.com) and sign up

2. **Add New Site**:
   - Connect to Git → Select your repo
   - Base directory: `frontend`
   - Build command: `npm run build`
   - Publish directory: `frontend/dist`

3. **Environment Variables**:
   - Site settings → Environment variables
   - Add: `VITE_API_URL=https://your-backend-url.onrender.com/api`

4. **Deploy**: Netlify will auto-deploy

---

## Option 3: All-in-One on Railway

Deploy both backend and frontend on Railway:

### Backend Service
- Follow Railway backend steps above

### Frontend Service
1. Create another service in the same Railway project
2. Root Directory: `frontend`
3. Build Command: `npm install && npm run build`
4. Start Command: `npx serve -s dist -l $PORT`
5. Environment Variable: `VITE_API_URL=https://your-backend-service.railway.app/api`

---

## Environment Variables Reference

### Backend (Required)
- `PICWISH_API_KEY` - Your PicWish API key (get from https://picwish.com/api-pricing)

### Backend (Optional)
- `UPLOAD_DIR` - Upload directory (default: `uploads`)
- `PROCESSED_DIR` - Processed directory (default: `processed`)
- `CLEANUP_TTL_HOURS` - Hours before cleanup (default: `24`)
- `MAX_FILE_SIZE` - Max file size in MB (default: `100`)
- `BATCH_SIZE` - Images per batch (default: `500`)
- `MAX_CONCURRENT` - Concurrent API requests (default: `10`)

### Frontend (Required)
- `VITE_API_URL` - Backend API URL (e.g., `https://backend.railway.app/api`)

---

## Free Tier Limits

### Railway
- **$5 free credit/month**
- ~500 hours of runtime (enough for 24/7 small app)
- 512MB RAM, 1GB disk
- **Best for**: Small to medium teams

### Render
- **Free tier available** (sleeps after 15min inactivity)
- 512MB RAM, 1GB disk
- **Best for**: Development/testing

### Vercel
- **Free tier**: Unlimited projects
- 100GB bandwidth/month
- **Best for**: Frontend hosting

### Netlify
- **Free tier**: Unlimited sites
- 100GB bandwidth/month
- **Best for**: Frontend hosting

---

## Quick Start (Railway + Vercel)

1. **Backend**:
   ```bash
   # Push your code to GitHub
   git add .
   git commit -m "Ready for deployment"
   git push
   
   # Go to railway.app, create project from GitHub repo
   # Set backend folder as root
   # Add PICWISH_API_KEY environment variable
   # Deploy
   ```

2. **Frontend**:
   ```bash
   # Go to vercel.com, import GitHub repo
   # Set frontend folder as root
   # Add VITE_API_URL environment variable
   # Deploy
   ```

3. **Share URL**: Give your team the Vercel frontend URL!

---

## Troubleshooting

### Backend Issues

**Port binding error**:
- Make sure you use `--port $PORT` (Railway/Render set this automatically)

**Files not persisting**:
- Add persistent volumes/disks for `uploads` and `processed` directories

**API key not working**:
- Double-check `PICWISH_API_KEY` is set correctly in environment variables

### Frontend Issues

**API calls failing**:
- Check `VITE_API_URL` is set correctly
- Make sure backend URL includes `/api` at the end
- Check CORS settings (backend should allow your frontend domain)

**Build fails**:
- Make sure `npm install` runs before `npm run build`
- Check Node version (should be 18+)

---

## Cost Comparison

| Service | Free Tier | Paid Tier | Best For |
|---------|-----------|-----------|----------|
| Railway | $5/month credit | $20+/month | Backend (easiest) |
| Render | Free (sleeps) | $7+/month | Backend (alternative) |
| Vercel | Free | $20/month | Frontend (best) |
| Netlify | Free | $19/month | Frontend (alternative) |

**Recommended**: Railway backend + Vercel frontend = **FREE** for small teams!

---

## Security Notes

- These are public URLs - anyone with the link can access
- For internal use only, consider:
  - Adding basic auth (Railway/Render support this)
  - Using VPN/private network
  - Adding authentication middleware

---

## Next Steps

1. Choose your hosting (Railway + Vercel recommended)
2. Deploy backend first, get the URL
3. Deploy frontend with backend URL
4. Test and share with your team!
