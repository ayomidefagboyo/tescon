# GitHub Actions Deployment Guide

## Overview

This guide will help you deploy the simplified GitHub Actions-based image processing system.

---

## Prerequisites

1. **GitHub Account** with repository access
2. **Render Account** with your backend deployed
3. **Cloudflare R2** bucket configured

---

## Step 1: Create GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Settings:
   - **Name:** `Tescon Image Processing`
   - **Expiration:** No expiration (or 1 year)
   - **Scopes:**
     - ✅ `repo` (Full control of private repositories)
     - ✅ `workflow` (Update GitHub Action workflows)
4. Click **"Generate token"**
5. **Copy the token** (starts with `ghp_`) - you'll need this for Render

---

## Step 2: Configure GitHub Secrets

1. Go to your repository settings:
   ```
   https://github.com/ayomidefagboyo/tescon/settings/secrets/actions
   ```

2. Click **"New repository secret"** and add each of these:

   | Secret Name | Value | Example |
   |-------------|-------|---------|
   | `R2_ENDPOINT` | Your R2 endpoint | `abc123.r2.cloudflarestorage.com` |
   | `R2_ACCESS_KEY` | Your R2 access key | `a1b2c3d4e5f6...` |
   | `R2_SECRET_KEY` | Your R2 secret key | `x1y2z3...` |
   | `R2_BUCKET` | Your R2 bucket name | `tescon-images` |
   | `RENDER_WEBHOOK` | Your Render webhook URL | `https://your-app.onrender.com/api/jobs/complete` |

---

## Step 3: Push Code to GitHub

```bash
cd /Users/admin/tescon

# Add new files
git add .github/workflows/process-images.yml
git add backend/app/services/github_actions_service.py
git add backend/app/services/github_trigger_service.py
git add backend/github_worker.py
git add DEPLOYMENT_GUIDE.md

# Commit
git commit -m "Implement GitHub Actions image processing"

# Push
git push origin main
```

---

## Step 4: Configure Render Environment Variables

### For Your Main Backend Service

Add these environment variables in Render dashboard:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_your_personal_access_token_here
GITHUB_REPO_OWNER=ayomidefagboyo
GITHUB_REPO_NAME=tescon
GITHUB_WORKFLOW_FILE=process-images.yml

# GitHub Trigger Settings
GITHUB_AUTO_TRIGGER_ENABLED=true
GITHUB_CHECK_INTERVAL=300
GITHUB_JOB_AGE_THRESHOLD=120

# Keep existing R2 credentials
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_ACCESS_KEY_ID=your_access_key
CLOUDFLARE_SECRET_ACCESS_KEY=your_secret_key
CLOUDFLARE_BUCKET_NAME=your_bucket_name

# Webhook for completion notifications
RENDER_WEBHOOK=https://your-app.onrender.com/api/jobs/complete
```

### Create New Background Worker Service

1. In Render dashboard, click **"New +"** → **"Background Worker"**
2. Settings:
   - **Name:** `tescon-github-worker`
   - **Environment:** Python 3
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `python backend/github_worker.py`
3. Add the **same environment variables** as above
4. Click **"Create Background Worker"**

---

## Step 5: Test the System

### Test 1: Manual Workflow Trigger

1. Go to GitHub Actions:
   ```
   https://github.com/ayomidefagboyo/tescon/actions/workflows/process-images.yml
   ```

2. Click **"Run workflow"**
3. Enter a test `job_id` (you can use a dummy ID for testing)
4. Click **"Run workflow"**
5. Monitor the execution - it should complete in 2-5 minutes

### Test 2: End-to-End Flow

1. **Upload images** via your frontend
2. **Check Render logs** for:
   ```
   GitHub trigger service initialized (enabled: true)
   Found 1 jobs ready for processing
   ✅ GitHub Actions triggered for job {job_id} (run: {run_id})
   ```
3. **Monitor GitHub Actions**: https://github.com/ayomidefagboyo/tescon/actions
4. **Verify R2**: Check `parts/{symbol_number}/` for processed images
5. **Check frontend**: Processed images should appear

---

## Step 6: Monitor and Verify

### Check Render Logs

```bash
# Main service logs
- Look for: "GitHub trigger service initialized"
- Look for: "✅ GitHub Actions triggered"

# Background worker logs  
- Look for: "GitHub Actions Background Worker Starting"
- Look for: "Found X jobs ready for processing"
```

### Check GitHub Actions

- Go to: https://github.com/ayomidefagboyo/tescon/actions
- Green checkmarks = success
- Click on runs to see detailed logs

### Check R2 Storage

```
r2://your-bucket/
├── jobs/
│   ├── queued/          # Should be empty after processing
│   └── completed/       # Completed jobs here
└── parts/
    └── {symbol_number}/
        └── *.jpg        # Processed images
```

---

## Troubleshooting

### Issue: "GitHub Actions not configured"

**Solution:**
- Verify `GITHUB_TOKEN` is set in Render
- Check token has `workflow` permission
- Ensure token hasn't expired

### Issue: Workflow fails with "Secrets not found"

**Solution:**
- Go to GitHub repository settings → Secrets
- Verify all 5 secrets are added correctly
- Check for typos in secret names

### Issue: Background worker not starting

**Solution:**
- Check Render background worker logs
- Verify `github_worker.py` exists in repo
- Ensure all dependencies are installed

### Issue: Jobs not being triggered

**Solution:**
- Check `GITHUB_AUTO_TRIGGER_ENABLED=true`
- Verify background worker is running
- Check R2 has jobs in `jobs/queued/`

---

## Success Metrics

| Metric | Target | How to Check |
|--------|--------|--------------|
| **Success Rate** | >95% | GitHub Actions success % |
| **Processing Time** | <5 min | Workflow execution time |
| **Cost** | $0 | Both platforms are free |
| **Uptime** | 99%+ | Monitor Render + GitHub status |

---

## What Was Removed

- ❌ All Kaggle-related code
- ❌ Kaggle CLI dependencies
- ❌ Kaggle notebook generation
- ❌ Complex fallback logic

## What Stayed

- ✅ Render backend API
- ✅ R2 storage structure
- ✅ Frontend (no changes needed)
- ✅ Excel metadata integration

---

## Next Steps After Deployment

1. **Monitor for 1 week** - Track success rate and performance
2. **Optimize if needed** - Adjust caching, timeouts, etc.
3. **Scale up** - Process your 69,000 images
4. **Save $6,900** - Celebrate avoiding PicWish costs!

---

## Support

If you encounter issues:
1. Check Render logs first
2. Check GitHub Actions logs
3. Verify all environment variables
4. Review R2 bucket structure

The system is now **simple, reliable, and cost-effective**!
