# Quick Deployment Guide - 5 Minutes to Live! 🚀

Deploy TESCON for **FREE** without Docker in just 5 minutes.

## Step 1: Backend on Railway (2 minutes)

1. Go to [railway.app](https://railway.app) and sign up with GitHub
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your repository
4. In project settings:
   - **Root Directory**: `backend`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Go to **Variables** tab and add:
   ```
   PICWISH_API_KEY=your_picwish_api_key_here
   ```
6. Copy your backend URL (e.g., `https://tescon-backend.railway.app`)

**Done!** Backend is live.

---

## Step 2: Frontend on Vercel (2 minutes)

1. Go to [vercel.com](https://vercel.com) and sign up with GitHub
2. Click **"Add New Project"** → Import your repository
3. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Go to **Environment Variables** and add:
   ```
   VITE_API_URL=https://your-backend-url.railway.app/api
   ```
   (Replace with your actual Railway backend URL)
5. Click **"Deploy"**

**Done!** Frontend is live.

---

## Step 3: Share with Your Team (1 minute)

Copy your Vercel URL (e.g., `https://tescon.vercel.app`) and share it!

---

## That's It! 🎉

Your app is now live and **FREE**:
- ✅ Backend: Railway (free $5/month credit)
- ✅ Frontend: Vercel (free tier)
- ✅ No Docker needed
- ✅ Auto-deploys on git push

---

## Troubleshooting

**Backend not working?**
- Check `PICWISH_API_KEY` is set correctly
- Make sure root directory is `backend`
- Check Railway logs for errors

**Frontend can't connect to backend?**
- Make sure `VITE_API_URL` includes `/api` at the end
- Check backend URL is correct (no trailing slash)
- Verify backend is running (check Railway dashboard)

**Need help?** See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.
