#!/usr/bin/env python3
"""
local_processor.py
==================
Runs the image processing pipeline locally on your laptop.

- Uses the SAME rembg background-removal + e-commerce layout as GitHub Actions
- Automatically detects Apple Silicon (MPS) / NVIDIA GPU / CPU
- Picks up queued jobs from R2 and uploads processed images back
- Respects a --daily-limit so you don't over-queue in one session

Usage:
    python3 backend/local_processor.py                         # auto-pick next queued job
    python3 backend/local_processor.py --job-id job_proxy_20260622
    python3 backend/local_processor.py --daily-limit 100      # max 100 symbols
    python3 backend/local_processor.py --dry-run              # see what would run

Speed estimates (per image):
    Apple M1/M2/M3 (MPS) : ~3-5 seconds
    Intel/AMD CPU only    : ~10-20 seconds
    300 images on M2      : ~20-25 minutes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_ROOT.parent

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "enhanced-rembg-processor"))

import boto3
from botocore.config import Config

# ---------------------------------------------------------------------------
# R2 client with explicit timeouts so DNS hangs fail fast
# ---------------------------------------------------------------------------
def make_r2_client():
    account_id  = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    access_key  = os.getenv("CLOUDFLARE_ACCESS_KEY_ID")
    secret_key  = os.getenv("CLOUDFLARE_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("CLOUDFLARE_BUCKET_NAME", "tescon-images")

    if not all([account_id, access_key, secret_key]):
        raise RuntimeError("Missing R2 credentials in backend/.env")

    client = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
        config=Config(
            connect_timeout=10,
            read_timeout=60,
            retries={"max_attempts": 3},
            signature_version="s3v4",
        ),
    )
    return client, bucket_name


# ---------------------------------------------------------------------------
# Hardware detection
# ---------------------------------------------------------------------------
def detect_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            print(f"  🟢 CUDA GPU detected: {torch.cuda.get_device_name(0)}")
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            print("  🟢 Apple Silicon (MPS) detected — using Metal GPU")
            return "mps"
    except ImportError:
        pass
    print("  🟡 No GPU detected — using CPU (slower but works fine)")
    return "cpu"


# ---------------------------------------------------------------------------
# Processing — reuses the existing rembg_processor from the repo
# ---------------------------------------------------------------------------
def process_single_image(raw_bytes: bytes, symbol_number: str,
                         part_info: dict, view_num: int) -> bytes:
    """Remove background and apply e-commerce layout, return PNG bytes."""
    try:
        # Use the existing processor from the repo
        sys.path.insert(0, str(PROJECT_ROOT / "enhanced-rembg-processor"))
        from app.processing.rembg_processor import process_image
        result = process_image(
            raw_bytes,
            output_format="PNG",
            white_background=True,
            use_ecommerce_layout=True,
            symbol_number=symbol_number,
            desc1=part_info.get("desc1", ""),
            desc2=part_info.get("desc2", ""),
            long_description=part_info.get("long_desc", ""),
            part_number=part_info.get("part_number", ""),
            manufacturer=part_info.get("manufacturer", ""),
            compression_quality=95,
        )
        return result.read()
    except Exception:
        # Fallback: rembg directly if the enhanced processor isn't available
        from rembg import remove
        from PIL import Image
        img = Image.open(BytesIO(raw_bytes)).convert("RGBA")
        out = remove(img)
        # White background
        bg = Image.new("RGBA", out.size, (255, 255, 255, 255))
        bg.paste(out, mask=out.split()[3])
        buf = BytesIO()
        bg.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Load part info from master catalog
# ---------------------------------------------------------------------------
def load_catalog_lookup() -> dict:
    catalog_path = BACKEND_ROOT / "Total EGTL Photo Project.xlsx"
    if not catalog_path.exists():
        print("  ⚠️  Master catalog not found — descriptions won't be embedded")
        return {}

    print(f"  Loading catalog for descriptions…")
    import pandas as pd
    df = pd.read_excel(catalog_path, sheet_name="Photo Data")
    lookup = {}
    for _, row in df.iterrows():
        sym = str(row.get("Symbol Number", "")).strip()
        if sym:
            lookup[sym] = {
                "desc1":        str(row.get("Desc1", "") or ""),
                "desc2":        str(row.get("Desc2", "") or ""),
                "long_desc":    str(row.get("Long Text Desc", "") or ""),
                "part_number":  str(row.get("Part No", "") or ""),
                "manufacturer": str(row.get("Mfg Name", "") or ""),
            }
    print(f"  → {len(lookup):,} parts indexed")
    return lookup


# ---------------------------------------------------------------------------
# Job management
# ---------------------------------------------------------------------------
def list_queued_jobs(r2, bucket: str) -> list[str]:
    paginator = r2.get_paginator("list_objects_v2")
    jobs = []
    for page in paginator.paginate(Bucket=bucket, Prefix="jobs/queued/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".json"):
                jobs.append(key.split("/")[-1].replace(".json", ""))
    return jobs


def load_job(r2, bucket: str, job_id: str) -> dict:
    resp = r2.get_object(Bucket=bucket, Key=f"jobs/queued/{job_id}.json")
    return json.loads(resp["Body"].read().decode())


def mark_job_complete(r2, bucket: str, job_id: str, job_data: dict,
                      processed: int, failed: int):
    job_data["status"] = "completed"
    job_data["completed_at"] = datetime.now(timezone.utc).isoformat()
    job_data["processed_files_count"] = processed
    job_data["failed_files_count"] = failed
    job_data["processing_method"] = "local_laptop"

    r2.put_object(
        Bucket=bucket,
        Key=f"jobs/completed/{job_id}.json",
        Body=json.dumps(job_data, indent=2),
        ContentType="application/json",
    )
    try:
        r2.delete_object(Bucket=bucket, Key=f"jobs/queued/{job_id}.json")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", help="Specific job ID to process (default: auto-pick next queued)")
    parser.add_argument("--daily-limit", type=int, default=100,
                        help="Max symbols to process in this run (default: 100 ≈ 300 images)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be processed without touching R2")
    args = parser.parse_args()

    print("🖥️  Local Image Processor")
    print("=" * 50)

    # Detect hardware
    print("\n📟 Hardware:")
    device = detect_device()

    # Connect to R2
    print("\n☁️  Connecting to R2…")
    try:
        r2, bucket = make_r2_client()
        r2.head_bucket(Bucket=bucket)
        print(f"  ✅ Connected to bucket: {bucket}")
    except Exception as e:
        print(f"  ❌ R2 connection failed: {e}")
        return 1

    # Load catalog
    print("\n📚 Master Catalog:")
    catalog = load_catalog_lookup()

    # Find job
    print("\n📋 Jobs:")
    if args.job_id:
        job_id = args.job_id
    else:
        queued = list_queued_jobs(r2, bucket)
        if not queued:
            print("  ℹ️  No queued jobs found. Run proxy_capture.py first.")
            return 0
        # Prefer proxy jobs, then most recent
        proxy = [j for j in queued if "proxy" in j]
        job_id = proxy[0] if proxy else queued[0]
        print(f"  Auto-selected job: {job_id}  ({len(queued)} total queued)")

    try:
        job_data = load_job(r2, bucket, job_id)
    except Exception as e:
        print(f"  ❌ Could not load job {job_id}: {e}")
        return 1

    parts = job_data.get("parts", [])
    print(f"  Job: {job_id}")
    print(f"  Parts in job: {len(parts):,}")

    # Apply daily limit
    if len(parts) > args.daily_limit:
        print(f"  ⚠️  Capping to --daily-limit {args.daily_limit} (of {len(parts)} parts)")
        parts_to_process = parts[:args.daily_limit]
        remaining_parts  = parts[args.daily_limit:]
    else:
        parts_to_process = parts
        remaining_parts  = []

    total_images = sum(len(p.get("raw_file_paths", [])) for p in parts_to_process)
    est_seconds  = total_images * (5 if device == "mps" else 15 if device == "cuda" else 20)
    est_mins     = est_seconds / 60

    print(f"\n  Will process : {len(parts_to_process)} symbols / {total_images} images")
    print(f"  Remaining    : {len(remaining_parts)} symbols (re-queue next run)")
    print(f"  Estimated    : ~{est_mins:.0f} minutes on this hardware")

    if args.dry_run:
        print("\n🔍 DRY-RUN — no changes made")
        for p in parts_to_process[:10]:
            print(f"  {p['symbol_number']}  ({len(p.get('raw_file_paths',[]))} images)")
        return 0

    # -----------------------------------------------------------------------
    # Process
    # -----------------------------------------------------------------------
    print("\n🎨 Processing…")
    successful = 0
    failed = 0
    start = time.time()

    for i, part in enumerate(parts_to_process, 1):
        symbol_number = part["symbol_number"]
        raw_paths     = part.get("raw_file_paths", [])
        part_info     = catalog.get(symbol_number, {})

        desc_short = part_info.get("desc1", "")[:35] or "—"
        print(f"\n  [{i:3d}/{len(parts_to_process)}] {symbol_number}  {desc_short}")

        for view_num, file_info in enumerate(raw_paths[:3], start=1):
            r2_key   = file_info["r2_key"]
            filename = file_info["filename"]

            try:
                # Download raw image
                resp      = r2.get_object(Bucket=bucket, Key=r2_key)
                raw_bytes = resp["Body"].read()

                # Process
                t0          = time.time()
                png_bytes   = process_single_image(raw_bytes, symbol_number, part_info, view_num)
                elapsed_img = time.time() - t0

                # Build output filename: {symbol}_{view}_{DESC1}.png
                clean_desc = "".join(
                    c if c.isalnum() or c == "_" else "_"
                    for c in part_info.get("desc1", "part")
                ).strip("_")[:40]
                out_filename = f"{symbol_number}_{view_num}_{clean_desc}.png"
                out_key      = f"parts/{symbol_number}/{out_filename}"

                # Upload
                r2.put_object(
                    Bucket=bucket,
                    Key=out_key,
                    Body=png_bytes,
                    ContentType="image/png",
                )

                successful += 1
                print(f"       ✅ view {view_num}: {out_filename}  ({elapsed_img:.1f}s)")

            except Exception as e:
                failed += 1
                print(f"       ❌ view {view_num} {filename}: {e}")

    # -----------------------------------------------------------------------
    # If we capped, save remaining back to a new job
    # -----------------------------------------------------------------------
    if remaining_parts:
        remainder_job_id = f"{job_id}_remainder"
        remainder_data   = dict(job_data)
        remainder_data["job_id"]     = remainder_job_id
        remainder_data["parts"]      = remaining_parts
        remainder_data["status"]     = "queued"
        remainder_data["created_at"] = datetime.now(timezone.utc).isoformat()
        r2.put_object(
            Bucket=bucket,
            Key=f"jobs/queued/{remainder_job_id}.json",
            Body=json.dumps(remainder_data, indent=2),
            ContentType="application/json",
        )
        print(f"\n  ♻️  {len(remaining_parts)} remaining parts saved → {remainder_job_id}")

    # Mark original job complete
    mark_job_complete(r2, bucket, job_id, job_data, successful, failed)

    elapsed_total = time.time() - start
    print("\n" + "=" * 50)
    print("✅ DONE")
    print(f"   Processed  : {successful} images")
    print(f"   Failed     : {failed} images")
    print(f"   Time taken : {elapsed_total/60:.1f} minutes")
    if remaining_parts:
        print(f"   Next run   : python3 backend/local_processor.py --job-id {job_id}_remainder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
