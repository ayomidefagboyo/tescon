# Render Environment Variables for Kaggle Auto-Trigger

Add these environment variables to your Render deployment:

## Required for Kaggle Auto-Trigger

```bash
# Enable automatic Kaggle triggering
KAGGLE_AUTO_TRIGGER_ENABLED=true

# Kaggle notebook details
KAGGLE_USERNAME=ayomidefagboyo
KAGGLE_NOTEBOOK_SLUG=daily-enhanced-rembg-processor

# Timing settings
KAGGLE_CHECK_INTERVAL=300        # Check every 5 minutes
KAGGLE_JOB_AGE_THRESHOLD=120     # Process jobs older than 2 minutes

# Webhook for completion notifications (your Render app URL)
RENDER_WEBHOOK_URL=https://your-app.onrender.com/api/jobs/complete
```

## Required R2 Secrets (already set up)

```bash
# These should already be configured in your Render deployment
R2_ENDPOINT=your-account.r2.cloudflarestorage.com
R2_ACCESS_KEY=your_r2_access_key
R2_SECRET_KEY=your_r2_secret_key
R2_BUCKET=your_bucket_name
```

## Kaggle API Credentials (Manual Setup)

Since Kaggle CLI requires API credentials, you'll need to:

1. **Get Kaggle API credentials**:
   - Go to https://www.kaggle.com/settings/account
   - Click "Create New API Token"
   - Download `kaggle.json`

2. **Add to Render deployment**:
   ```bash
   # Option A: Set as environment variables
   KAGGLE_USERNAME=your_kaggle_username
   KAGGLE_KEY=your_kaggle_key

   # Option B: Mount as secret file (preferred)
   # Upload kaggle.json as a secret file in Render
   ```

## Kaggle Notebook Secrets Setup

In your Kaggle notebook, add these secrets:

1. Go to your notebook: https://www.kaggle.com/code/ayomidefagboyo/daily-enhanced-rembg-processor
2. Click "Add Data" → "Secrets"
3. Add these secrets:

```
R2_ENDPOINT = your-account.r2.cloudflarestorage.com
R2_ACCESS_KEY = your_r2_access_key
R2_SECRET_KEY = your_r2_secret_key
R2_BUCKET = your_bucket_name
```

## How It Works

1. **Mobile App** → uploads images to R2 `raw_images/`
2. **Render Backend** → creates job in `jobs/queued/`
3. **Auto-Trigger Service** → detects job after 2 minutes
4. **Kaggle Notebook** → automatically triggered via API
5. **Processing Complete** → results in `processed_images/`
6. **Webhook Notification** → Render app notified

## Testing the Auto-Trigger

1. **Enable in Render**: Set `KAGGLE_AUTO_TRIGGER_ENABLED=true`
2. **Deploy to Render**: Redeploy with new environment variables
3. **Upload via Mobile**: Use your mobile app to upload images
4. **Monitor Logs**: Check Render logs for auto-trigger activity:
   ```
   [14:30:15] INFO: Found 1 jobs ready for processing
   [14:30:16] INFO: Triggering Kaggle processing for job: job_20250130_143015
   [14:30:18] INFO: Successfully triggered Kaggle for job: job_20250130_143015
   ```

## Manual Trigger (Backup)

If auto-trigger fails, you can still manually trigger:

```bash
# Run locally
python auto_kaggle_trigger.py

# Or use the Kaggle CLI directly
kaggle kernels push --path /path/to/notebook/files
```

## Troubleshooting

### Auto-trigger not working:
- Check Render logs for errors
- Verify `KAGGLE_AUTO_TRIGGER_ENABLED=true`
- Ensure Kaggle API credentials are correct

### Kaggle notebook fails:
- Check Kaggle notebook execution logs
- Verify R2 secrets are set in Kaggle
- Ensure R2 bucket permissions allow access

### No jobs detected:
- Check if jobs are in `jobs/queued/` folder in R2
- Verify job age > 2 minutes (configurable)
- Check R2 connection from Render

## Cost Savings

With auto-trigger enabled:
- **Mobile Upload** → **Immediate queuing** → **Automatic processing** → **Results ready**
- **Zero manual intervention** required
- **$6,900 savings** over 77 days vs PicWish API
- **Processing time**: 2-10 minutes per batch

Perfect hands-off workflow! 🚀