# Simplified Deployment Guide - Single Service

## Overview

Run everything in **one Render service** - no separate background worker needed!

---

## Step 1: Create GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Settings:
   - **Scopes:** ✅ `repo` + ✅ `workflow`
4. **Copy the token** (starts with `ghp_`)

---

## Step 2: Configure GitHub Secrets

Go to: `https://github.com/ayomidefagboyo/tescon/settings/secrets/actions`

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `R2_ENDPOINT` | `your-account.r2.cloudflarestorage.com` |
| `R2_ACCESS_KEY` | Your R2 access key |
| `R2_SECRET_KEY` | Your R2 secret key |
| `R2_BUCKET` | Your bucket name |
| `RENDER_WEBHOOK` | `https://your-app.onrender.com/api/jobs/complete` |

---

## Step 3: Push Code to GitHub

```bash
cd /Users/admin/tescon

git add .github/workflows/process-images.yml
git add backend/app/services/github_actions_service.py
git add backend/app/services/github_trigger_service.py
git add backend/app/main.py
git add DEPLOYMENT_GUIDE_SIMPLE.md

git commit -m "Add GitHub Actions image processing"
git push origin main
```

---

## Step 4: Update Render Environment Variables

In your **existing Render backend service**, add these variables:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO_OWNER=ayomidefagboyo
GITHUB_REPO_NAME=tescon
GITHUB_WORKFLOW_FILE=process-images.yml

# GitHub Trigger Settings
GITHUB_AUTO_TRIGGER_ENABLED=true
GITHUB_CHECK_INTERVAL=300
GITHUB_JOB_AGE_THRESHOLD=120

# Keep existing R2 credentials (no changes)
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_ACCESS_KEY_ID=...
CLOUDFLARE_SECRET_ACCESS_KEY=...
CLOUDFLARE_BUCKET_NAME=...
RENDER_WEBHOOK=...
```

**That's it!** Render will auto-restart and the GitHub trigger service will start automatically.

---

## Step 5: Test

### Quick Test

1. Upload images via your frontend
2. Check Render logs for:
   ```
   ✓ GitHub Actions trigger service started
   Found 1 jobs ready for processing
   ✅ GitHub Actions triggered for job {job_id}
   ```
3. Check GitHub Actions: https://github.com/ayomidefagboyo/tescon/actions
4. Verify processed images in R2: `parts/{symbol_number}/`

---

## Architecture

```
┌─────────────────────────────────────┐
│   Single Render Service             │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │ FastAPI      │  │ Background  │ │
│  │ Web Server   │  │ Trigger     │ │
│  │ (handles API)│  │ (polls R2)  │ │
│  └──────────────┘  └─────────────┘ │
│         │                  │        │
└─────────┼──────────────────┼────────┘
          │                  │
          ▼                  ▼
    Frontend           GitHub Actions
                       (processes images)
```

**Benefits:**
- ✅ **One service** = simpler, cheaper
- ✅ **No extra cost** = stays on free tier
- ✅ **Same reliability** = GitHub Actions still does processing

---

## Troubleshooting

### "GitHub Actions not configured"
- Check `GITHUB_TOKEN` is set in Render
- Verify token has `workflow` permission

### Jobs not being triggered
- Check Render logs for "GitHub Actions trigger service started"
- Verify `GITHUB_AUTO_TRIGGER_ENABLED=true`
- Ensure jobs exist in R2 `jobs/queued/`

### Workflow fails
- Check GitHub Secrets are set correctly
- Review GitHub Actions logs

---

## What You DON'T Need

- ❌ Separate background worker service
- ❌ Kaggle CLI or credentials
- ❌ Extra Render costs

## What You DO Need

- ✅ GitHub Personal Access Token
- ✅ GitHub Secrets configured
- ✅ Updated Render environment variables

---

**Total Cost:** $0 (stays on Render free tier + GitHub Actions free tier)

**Total Services:** 1 (just your existing Render backend)

**Deployment Time:** ~15 minutes
