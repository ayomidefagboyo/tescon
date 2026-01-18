# Cloudflare R2 Setup Guide

This guide walks you through setting up Cloudflare R2 cloud storage for TESCON image processing.

## Why Cloudflare R2?

✅ **Simple Setup**: Just 4 environment variables
✅ **Free Tier**: 10GB storage, 1M requests/month (handles 10,000+ images)
✅ **S3 Compatible**: Uses standard boto3 library
✅ **Fast & Reliable**: Global CDN, 99.9% uptime
✅ **No OAuth Complexity**: No redirect URIs or authentication flows

## Step 1: Create Cloudflare Account

1. Visit [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Sign up for free account
3. Verify your email

## Step 2: Enable R2 Storage

1. In Cloudflare Dashboard, go to **R2 Object Storage** (sidebar)
2. Click **"Purchase R2"** (it's free to start)
3. Accept the terms

## Step 3: Create Storage Bucket

1. Click **"Create bucket"**
2. **Bucket name**: `tescon-images` (or your preferred name)
3. **Location**: Auto (recommended)
4. Click **"Create bucket"**

## Step 4: Generate API Token

1. Go to **"Manage R2 API tokens"**
2. Click **"Create API token"**
3. Choose **"Custom token"**
4. **Token name**: `tescon-backend`
5. **Permissions**:
   - `R2:Object:Read`
   - `R2:Object:Write`
   - `R2:Bucket:Read`
6. **Account resources**: Include - All accounts
7. **Zone resources**: Include - All zones (or skip if no domains)
8. Click **"Continue to summary"**
9. Click **"Create token"**

## Step 5: Get Credentials

After creating the token, you'll see:

- **Access Key ID**: Something like `a1b2c3d4e5f6g7h8i9j0`
- **Secret Access Key**: Something like `abc123def456ghi789jkl012mno345pqr678stu901vwx234`
- **Account ID**: In the dashboard sidebar (like `1a2b3c4d5e6f7g8h9i0j`)

## Step 6: Update Environment Variables

Edit `/Users/admin/tescon/backend/.env`:

```env
# Cloudflare R2 Storage
CLOUDFLARE_ACCOUNT_ID=1a2b3c4d5e6f7g8h9i0j
CLOUDFLARE_ACCESS_KEY_ID=a1b2c3d4e5f6g7h8i9j0
CLOUDFLARE_SECRET_ACCESS_KEY=abc123def456ghi789jkl012mno345pqr678stu901vwx234
CLOUDFLARE_BUCKET_NAME=tescon-images
```

## Step 7: Test the Setup

1. Restart your FastAPI server:
   ```bash
   # Stop the current server (Ctrl+C)
   # Then restart:
   source venv/bin/activate
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

2. Test the debug endpoint:
   ```bash
   curl http://localhost:8001/api/debug/env
   ```

3. You should see:
   ```json
   {
     "r2_service_status": "success",
     "r2_storage_stats": {
       "total_objects": 0,
       "total_size_mb": 0,
       "bucket_name": "tescon-images"
     }
   }
   ```

## Step 8: Process Your First Image

1. Go to your frontend: `http://localhost:4173`
2. Upload an image for any part number
3. The image will be processed and uploaded to R2
4. Check your R2 bucket - you'll see the organized files:

```
parts/
├── 58018612/
│   ├── 58018612_1_BALL_INERT_3_4_IN_DIA.jpg
│   └── 58018612_2_BALL_INERT_3_4_IN_DIA.jpg
└── 58023823/
    └── 58023823_1_MOTOR_ELECTRIC_AC_60_HP.jpg
```

## Production Deployment

For Render/Vercel deployment, add these environment variables in your hosting dashboard:

```env
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_ACCESS_KEY_ID=your_access_key
CLOUDFLARE_SECRET_ACCESS_KEY=your_secret_key
CLOUDFLARE_BUCKET_NAME=tescon-images
```

## File Organization

Images are automatically organized as:
- **Path**: `parts/{part_number}/{filename}`
- **Filename**: `{part_number}_{view_number}_{description}.jpg`
- **Metadata**: Part number, description, source tagged
- **Public URLs**: Available immediately after upload

## Free Tier Limits

- **Storage**: 10GB (≈10,000 processed images)
- **Requests**: 1M/month (way more than you need)
- **Bandwidth**: 100GB/month egress

Perfect for your 200-600 images/day workflow!

## Troubleshooting

### "Missing credentials" error
- Check environment variables are set correctly
- Restart FastAPI server after updating .env

### "Bucket not found" error
- Verify bucket name matches `CLOUDFLARE_BUCKET_NAME`
- Check bucket was created in correct account

### "Permission denied" error
- Verify API token has correct permissions
- Make sure token is not expired