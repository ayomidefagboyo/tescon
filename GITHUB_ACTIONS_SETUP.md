# GitHub Actions Environment Variables for Render

## Required Variables

Add these to your Render service environment variables:

### GitHub Configuration
```bash
# GitHub Personal Access Token (with workflow permissions)
GITHUB_TOKEN=ghp_your_personal_access_token_here

# Repository information
GITHUB_REPO_OWNER=ayomidefagboyo
GITHUB_REPO_NAME=tescon
GITHUB_WORKFLOW_FILE=process-images.yml
```

### Processing Strategy
```bash
# Options: 'github_actions', 'kaggle', or 'both'
# 'github_actions' - Use only GitHub Actions
# 'kaggle' - Use only Kaggle (current behavior)
# 'both' - Try GitHub Actions first, fallback to Kaggle
PROCESSING_STRATEGY=both
```

### Keep Existing Variables
```bash
# These remain unchanged
KAGGLE_AUTO_TRIGGER_ENABLED=true
KAGGLE_CHECK_INTERVAL=300
KAGGLE_JOB_AGE_THRESHOLD=120
KAGGLE_USERNAME=ayomidefagboyo
KAGGLE_NOTEBOOK_SLUG=daily-enhanced-rembg-processor

# R2 credentials (unchanged)
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_ACCESS_KEY_ID=your_access_key
CLOUDFLARE_SECRET_ACCESS_KEY=your_secret_key
CLOUDFLARE_BUCKET_NAME=your_bucket_name

# Webhook for completion notifications
RENDER_WEBHOOK=https://your-app.onrender.com/api/jobs/complete
```

## GitHub Secrets Setup

Add these secrets to your GitHub repository:

1. Go to: https://github.com/ayomidefagboyo/tescon/settings/secrets/actions
2. Click "New repository secret"
3. Add each of these:

```bash
R2_ENDPOINT=your-account.r2.cloudflarestorage.com
R2_ACCESS_KEY=your_r2_access_key
R2_SECRET_KEY=your_r2_secret_key
R2_BUCKET=your_bucket_name
RENDER_WEBHOOK=https://your-app.onrender.com/api/jobs/complete
```

## Creating GitHub Personal Access Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name: "Tescon Image Processing"
4. Expiration: No expiration (or 1 year)
5. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
6. Click "Generate token"
7. Copy the token (starts with `ghp_`)
8. Add to Render as `GITHUB_TOKEN`

## Deployment Steps

### 1. Push Code to GitHub
```bash
cd /Users/admin/tescon
git add .github/workflows/process-images.yml
git add backend/app/services/github_actions_service.py
git add backend/app/services/kaggle_trigger_service.py
git commit -m "Add GitHub Actions integration"
git push origin main
```

### 2. Add GitHub Secrets
- Follow "GitHub Secrets Setup" section above

### 3. Update Render Environment Variables
- Add all variables from "Required Variables" section
- Set `PROCESSING_STRATEGY=both` for safe rollout

### 4. Restart Render Service
```bash
# Render will automatically restart when you update env vars
# Or manually restart from Render dashboard
```

## Testing

### Test GitHub Actions Workflow
```bash
# Trigger manually from GitHub UI
# Go to: https://github.com/ayomidefagboyo/tescon/actions/workflows/process-images.yml
# Click "Run workflow"
# Enter a test job_id
```

### Monitor Execution
- **GitHub Actions**: https://github.com/ayomidefagboyo/tescon/actions
- **Render Logs**: Check your Render service logs
- **R2 Storage**: Verify processed images appear in `parts/` folder

## Rollout Strategy

### Phase 1: Parallel Testing (Week 1)
```bash
PROCESSING_STRATEGY=both
```
- Both GitHub Actions and Kaggle process jobs
- Compare results
- Monitor success rates

### Phase 2: GitHub Primary (Week 2)
```bash
PROCESSING_STRATEGY=both
```
- GitHub Actions handles most jobs
- Kaggle only used if GitHub fails
- Continue monitoring

### Phase 3: GitHub Only (Week 3+)
```bash
PROCESSING_STRATEGY=github_actions
```
- Disable Kaggle completely
- GitHub Actions is sole processor

## Troubleshooting

### GitHub Actions not triggering
- Check `GITHUB_TOKEN` is valid
- Verify repository name is correct
- Check GitHub Actions logs

### Workflow fails
- Check GitHub Secrets are set correctly
- Verify R2 credentials
- Review workflow logs in GitHub Actions UI

### Fallback to Kaggle not working
- Ensure `PROCESSING_STRATEGY=both`
- Check Kaggle CLI is still configured
- Verify Kaggle credentials

## Monitoring

### Success Metrics
- Check Render logs for: `✅ GitHub Actions triggered`
- Monitor GitHub Actions success rate
- Compare processing times (GitHub vs Kaggle)

### Key Logs to Watch
```
Trigger service initialized (enabled: true, strategy: both)
Triggering job {job_id} with strategy: both
✅ GitHub Actions triggered for job {job_id} (run: {run_id})
```
