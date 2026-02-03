# Tracker Accuracy Issue - Root Cause & Fix

## Problem Identified

The `parts_tracker.json` is **not being updated accurately** because:

### 1. **Missing `queued_parts` Field**
Your current tracker file is missing the `queued_parts` array, which was added in recent updates but the file wasn't migrated.

**Current structure:**
```json
{
  "processed_parts": ["TEST567"],
  "failed_parts": {},
  "part_stats": {...},
  "total_parts": 20651,
  "last_updated": "2026-01-25T13:31:07.875907"
}
```

**Missing:** `"queued_parts": []`

---

### 2. **Tracker Not Updated After GitHub Actions Processing**
When images are processed by GitHub Actions (`.github/workflows/process-images.yml`), the tracker is **NEVER updated**. Here's the actual flow:

```
User uploads images via /process/part/async
↓
Backend marks part as "queued" in tracker ✅
↓
Images uploaded to R2 storage (raw/) ✅
↓
Job metadata saved to R2 (jobs/queued/) ✅
↓
GitHub Actions triggered (manually via workflow_dispatch)
↓
GitHub Actions downloads images from R2
↓
GitHub Actions processes images with rembg
↓
GitHub Actions uploads to R2 (parts/) ✅
↓
GitHub Actions moves job to jobs/completed/ ✅
↓
GitHub Actions sends webhook to RENDER_WEBHOOK
↓
❌ NO WEBHOOK ENDPOINT EXISTS IN BACKEND ❌
↓
❌ TRACKER NEVER UPDATED ❌
```

**Result**: Parts stay in "queued" status forever, and "processed" count never increases.

---

### 3. **No Webhook Endpoint to Receive Completion Notifications**

GitHub Actions sends a webhook (line 283-298 in process-images.yml):
```python
requests.post(
    RENDER_WEBHOOK,
    json={
        'job_id': JOB_ID,
        'status': 'completed',
        'processor': 'github_actions',
        'processed_count': job_data.get('processed_files_count', 0)
    }
)
```

**But there's NO endpoint in `routes.py` to receive this!**

---

### 4. **No Sync Between R2 Storage and Tracker**
The tracker relies on manual updates from the API, but there's no mechanism to:
- Check R2 for already-processed parts
- Sync tracker with actual R2 storage state
- Update tracker when GitHub Actions completes jobs

---

## How Updates SHOULD Work

### Current Update Points:
1. **Excel Upload** → Sets `total_parts` ✅
2. **Part Upload (async)** → Adds to `queued_parts` ✅
3. **Part Processing (sync via /process/part)** → Marks as `processed` ✅
4. **Processing Failure** → Marks as `failed` ✅

### Missing Update Points:
5. **GitHub Actions Job Completion** → Should mark as `processed` ❌
6. **R2 Sync** → Should reconcile tracker with R2 state ❌
7. **Webhook Handler** → Should receive completion notifications ❌

---

## Solutions

### Solution 1: Add Webhook Endpoint to Receive GitHub Actions Notifications ⭐ CRITICAL
Create `/api/jobs/complete` endpoint that GitHub Actions calls when processing completes.

### Solution 2: Create R2 Sync Script
Build a script that scans R2 storage and updates the tracker based on actual files.

### Solution 3: Fix Missing `queued_parts` Field
Update the tracker structure to include the missing field.

### Solution 4: Add Manual Sync Command
Create a command to immediately sync tracker with R2 state.

---

## Implementation Plan

I'll create:
1. ✅ Fix tracker structure (add `queued_parts`)
2. ✅ Create webhook endpoint `/api/jobs/complete`
3. ✅ Create R2 sync script
4. ✅ Create manual sync command for immediate fix
5. ✅ Update GitHub Actions to call the correct webhook URL
