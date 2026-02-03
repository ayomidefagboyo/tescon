# How to Fix Tracker Accuracy

## Quick Fix (Run This Now!)

```bash
cd /Users/admin/tescon/backend
python sync_tracker.py
```

This will:
1. ✅ Add missing `queued_parts` field to tracker
2. ✅ Scan R2 storage for actual processed/queued parts
3. ✅ Update tracker to match reality
4. ✅ Display accurate statistics

---

## What Was Wrong

### Problem 1: Missing Webhook Endpoint
- GitHub Actions was sending completion notifications to `RENDER_WEBHOOK`
- **But no endpoint existed to receive them!**
- Result: Tracker never updated after processing

### Problem 2: Missing `queued_parts` Field
- Tracker file was created before `queued_parts` was added
- Old structure didn't track queued parts

### Problem 3: No R2 Sync
- No way to reconcile tracker with actual R2 storage state
- Tracker could drift from reality

---

## What's Been Fixed

### 1. ✅ Added Webhook Endpoint
**New endpoint:** `POST /api/jobs/complete`

GitHub Actions now calls this when processing completes, and it:
- Fetches job metadata from R2
- Checks which parts were successfully processed
- Updates tracker for each part
- Marks parts as processed/failed based on R2 state

### 2. ✅ Added R2 Sync Endpoint
**New endpoint:** `POST /api/tracker/sync-from-r2`

This endpoint:
- Scans R2 `parts/` folder for processed parts
- Scans R2 `raw/` folder for queued parts
- Clears and rebuilds tracker from R2 state
- Ensures tracker matches reality

### 3. ✅ Created Manual Sync Script
**Script:** `sync_tracker.py`

Run this anytime to fix tracker accuracy.

---

## How to Use Going Forward

### Option 1: Manual Sync (Immediate Fix)
```bash
cd /Users/admin/tescon/backend
python sync_tracker.py
```

### Option 2: API Sync (From Frontend/Postman)
```bash
curl -X POST http://localhost:8002/api/tracker/sync-from-r2
```

### Option 3: Automatic (GitHub Actions Webhook)
**Update your GitHub Actions secrets:**

1. Go to GitHub repo → Settings → Secrets
2. Update `RENDER_WEBHOOK` to:
   ```
   https://your-backend-url.onrender.com/api/jobs/complete
   ```

Now GitHub Actions will automatically update the tracker!

---

## Verify It's Working

### 1. Check Tracker File
```bash
cat /Users/admin/tescon/backend/parts_tracker.json
```

Should now have:
```json
{
  "processed_parts": [...],
  "failed_parts": {},
  "queued_parts": [...],  ← THIS SHOULD BE PRESENT
  "part_stats": {...},
  "total_parts": 23032,
  "last_updated": "2026-02-03T..."
}
```

### 2. Check Dashboard
Visit: `http://localhost:5174` (or your frontend URL)

Numbers should now be accurate!

### 3. Test Webhook
```bash
curl -X POST "http://localhost:8002/api/jobs/complete?job_id=job_daily_20260203&status=completed&processor=github_actions&processed_count=5"
```

---

## Troubleshooting

### Tracker still shows wrong numbers?
Run the sync script:
```bash
python sync_tracker.py
```

### GitHub Actions not updating tracker?
1. Check `RENDER_WEBHOOK` secret in GitHub
2. Should be: `https://your-backend.onrender.com/api/jobs/complete`
3. Test webhook manually (see above)

### Want to reset tracker completely?
```bash
curl -X POST http://localhost:8002/api/tracker/reset
python sync_tracker.py
```

---

## Summary

**Before:**
- Tracker: 23,032 total, 1 processed, 23,031 remaining ❌
- Reality: Unknown (tracker out of sync)

**After:**
- Tracker syncs with R2 storage ✅
- GitHub Actions updates tracker automatically ✅
- Manual sync available anytime ✅
- Accurate dashboard numbers ✅
