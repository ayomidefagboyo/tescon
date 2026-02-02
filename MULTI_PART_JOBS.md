# Multi-Part Daily Batch Processing

## Overview

The system now supports processing multiple parts (symbol numbers) in a single daily batch job. This is optimized for handling 300+ uploads per day efficiently.

## Job Format

### New Multi-Part Format (Recommended)

```json
{
  "job_id": "job_daily_20260201",
  "created_at": "2026-02-01T19:00:00Z",
  "status": "queued",
  "parts": [
    {
      "symbol_number": "58018612",
      "raw_file_paths": [
        {
          "filename": "IMG_1234.jpg",
          "r2_key": "raw/58018612/job_uuid_01_IMG_1234.jpg",
          "content_type": "image/jpeg"
        },
        {
          "filename": "IMG_1235.jpg",
          "r2_key": "raw/58018612/job_uuid_02_IMG_1235.jpg",
          "content_type": "image/jpeg"
        }
      ]
    },
    {
      "symbol_number": "26062392",
      "raw_file_paths": [
        {
          "filename": "IMG_5678.jpg",
          "r2_key": "raw/26062392/job_uuid_03_IMG_5678.jpg",
          "content_type": "image/jpeg"
        }
      ]
    }
    // ... up to 300 parts
  ]
}
```

### Old Single-Part Format (Still Supported)

```json
{
  "job_id": "job_20260201_123456",
  "symbol_number": "58018612",
  "created_at": "2026-02-01T12:34:56Z",
  "status": "queued",
  "raw_file_paths": [
    {
      "filename": "IMG_1234.jpg",
      "r2_key": "raw/58018612/job_uuid_01_IMG_1234.jpg",
      "content_type": "image/jpeg"
    }
  ]
}
```

The workflow automatically converts old format to new format for backward compatibility.

## Processing Schedule

**Daily at 7:00 PM:**
1. System checks `jobs/queued/` for all pending jobs
2. Triggers GitHub Actions workflow for each job
3. Each job processes all parts and their images
4. Results organized by symbol number in R2

## Output Structure

```
parts/
├── 58018612/
│   ├── 58018612_1_BALL_INERT_3_4_IN_DIA.png
│   ├── 58018612_2_BALL_INERT_3_4_IN_DIA.png
│   └── 58018612_3_BALL_INERT_3_4_IN_DIA.png
├── 26062392/
│   ├── 26062392_1_VALVE_ASSEMBLY.png
│   ├── 26062392_2_VALVE_ASSEMBLY.png
│   └── 26062392_3_VALVE_ASSEMBLY.png
└── ... (up to 300 folders)
```

## Capacity

### Single Daily Job:
- **300 parts** (symbol numbers)
- **900 images** (3 per part)
- **Processing time:** ~15 minutes
- **GitHub Actions usage:** 450 min/month
- **Cost:** $0 (within free tier)

### Multiple Jobs Per Day:
- Can create multiple jobs if needed
- Each job processes independently
- All jobs triggered at 7 PM

## Manual Trigger

To process a specific job before 7 PM:

1. Go to: https://github.com/ayomidefagboyo/tescon/actions/workflows/process-images.yml
2. Click "Run workflow"
3. Enter job_id (e.g., `job_daily_20260201`)
4. Click "Run workflow"

## Example Workflow Logs

```
🚀 GitHub Actions Processing - Job: job_daily_20260201
💰 Saving $4.95 vs PicWish API (900 images × 0.5 credits × $0.011)

📥 Downloading images for 300 parts...
  Part 58018612: 3 images
    ✅ image1.jpg
    ✅ image2.jpg
    ✅ image3.jpg
  Part 26062392: 3 images
    ✅ image1.jpg
    ...

✅ Loaded 23032 parts from catalog

🎨 Processing 900 images across multiple parts...
Processing 300 different parts

📦 Part 58018612: 3 images
  [1/3] Processing image1.jpg...
    ✅ Uploaded to parts/58018612/58018612_1_BALL_INERT_3_4_IN_DIA.png
  [2/3] Processing image2.jpg...
    ✅ Uploaded to parts/58018612/58018612_2_BALL_INERT_3_4_IN_DIA.png
  [3/3] Processing image3.jpg...
    ✅ Uploaded to parts/58018612/58018612_3_BALL_INERT_3_4_IN_DIA.png

📦 Part 26062392: 3 images
  ...

✅ Job status updated
✅ Render notified successfully

🎉 PROCESSING COMPLETE!
   ✅ Successful: 900
   ❌ Failed: 0
   ⏱️  Time: 14.5 min
   💰 Saved: $4.95 vs PicWish (0.5 credits/image × $0.011)
```

## Cost Comparison

### PicWish API Pricing
- **Rate:** $0.011 per credit
- **Background Removal:** 0.5 credits per image
- **Effective cost:** $0.0055 per image ($0.011 × 0.5)
- **Package:** 30,000 credits for $319.95

### Your GitHub Actions Solution

#### Per Batch (900 images):
- **PicWish Cost:** 900 images × 0.5 credits × $0.011 = **$4.95**
- **GitHub Actions Cost:** **$0.00** (within free tier)
- **Savings per batch:** **$4.95**

#### Monthly (30 batches):
- **PicWish Cost:** 27,000 images × 0.5 credits × $0.011 = **$148.50**
- **GitHub Actions Cost:** **$0.00** (450 min/month well within 2,000 min free tier)
- **Monthly savings:** **$148.50**

#### Yearly:
- **PicWish Cost:** 324,000 images × 0.5 credits × $0.011 = **$1,782.00**
- **GitHub Actions Cost:** **$0.00**
- **Annual savings:** **$1,782.00**

### ROI Summary
✅ **100% cost savings** on image processing  
✅ **Zero infrastructure costs** (using free tier)  
✅ **Scalable** up to 2,000 minutes/month free  
✅ **No per-image fees** regardless of volume

## Benefits

✅ **Efficient:** Process all daily uploads in one batch  
✅ **Cost-effective:** Well within GitHub Actions free tier  
✅ **Organized:** Proper folder structure by symbol number  
✅ **Scalable:** Handle 300+ parts per day  
✅ **Reliable:** 95%+ success rate  
✅ **Predictable:** Runs at 7 PM daily
