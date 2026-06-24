#!/usr/bin/env python3
"""
proxy_capture.py
================
Finds pending symbols that are visually similar to already-captured ones,
copies the donor's raw images into raw/{pending_symbol}/ in R2, and queues
them for background-removal processing — all in a single run.

Logic:
  1. Load master catalog → split into captured vs pending
  2. Strip size tokens from Desc1 to get a "base description"
  3. For each pending symbol, find the best-match captured symbol
     (same base_desc, closest Desc1 string similarity)
     
NOTE: boto3 is configured with explicit timeouts (connect=10s, read=30s)
to avoid silent DNS-hang hangs that can block indefinitely.
  4. Look for raw images under raw/{donor_symbol}/ in R2
  5. Copy them to raw/{pending_symbol}/ with correct key format
  6. Append the pending symbol to today's proxy job in jobs/queued/
  7. Print a full summary report

Usage:
    python3 backend/proxy_capture.py [--dry-run] [--limit N]

Options:
    --dry-run   Show what WOULD be done without touching R2
    --limit N   Only process the first N matched pending symbols (for testing)

Notes:
  - Only copies raw images. Processed (parts/) images are NOT reused.
  - The processing pipeline will re-run background removal and apply the
    correct symbol number / naming convention for each pending item.
  - Items are skipped if no raw images exist for any matching donor.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_ROOT.parent

import boto3
from botocore.config import Config
from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

sys.path.insert(0, str(BACKEND_ROOT))

import pandas as pd
from difflib import SequenceMatcher


# ---------------------------------------------------------------------------
# Build R2 client directly — explicit timeouts prevent DNS hang
# ---------------------------------------------------------------------------
def make_r2_client():
    account_id  = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    access_key  = os.getenv("CLOUDFLARE_ACCESS_KEY_ID")
    secret_key  = os.getenv("CLOUDFLARE_SECRET_ACCESS_KEY")
    bucket      = os.getenv("CLOUDFLARE_BUCKET_NAME", "tescon-images")
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
            read_timeout=30,
            retries={"max_attempts": 3},
            signature_version="s3v4",
        ),
    )
    return client, bucket

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MASTER_CATALOG = BACKEND_ROOT / "Total EGTL Photo Project.xlsx"
REPORT_FILE    = PROJECT_ROOT / "reports" / "proxy_capture_report.xlsx"

# Size/spec tokens to strip when computing base description
SIZE_PATTERN = re.compile(
    r'\b\d[\d./]*\s*(?:MM|CM|IN|FT|LB|KG|NB|BAR|PSI|KPA|DN|PN|SCH|STD|XS|XXS|CLASS|CL|OD|ID|WT|RF|FF|RTJ|SW|BW|THD|MNPT|FNPT|NPT|BSPT|BSP|#)\b'
    r'|["\']',  # bare inch/foot marks
    re.IGNORECASE,
)


def base_desc(text) -> str:
    if pd.isna(text) or not text:
        return ""
    s = SIZE_PATTERN.sub("", str(text))
    s = re.sub(r'\b\d+(?:\.\d+)?(?:/\d+)?\b', "", s)
    return re.sub(r'\s+', " ", s).strip().upper()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


# ---------------------------------------------------------------------------
# Step 1 — Load catalog + split captured / pending
# ---------------------------------------------------------------------------
def load_catalog(captured_symbols: set[str]):
    print(f"Loading master catalog: {MASTER_CATALOG.name}")
    df = pd.read_excel(MASTER_CATALOG, sheet_name="Photo Data")
    df["sym_norm"] = df["Symbol Number"].astype(str).str.strip()
    df["is_captured"] = df["sym_norm"].isin(captured_symbols)
    print(f"  Total: {len(df):,}  Captured: {df['is_captured'].sum():,}  "
          f"Pending: {(~df['is_captured']).sum():,}")
    return df


# ---------------------------------------------------------------------------
# Step 2 — Get current captured symbols from R2 (fast prefix scan)
# ---------------------------------------------------------------------------
def get_captured_symbols(r2, bucket: str) -> set[str]:
    print("Fetching captured and queued symbols from local tracker…")
    from app.services.parts_tracker import get_parts_tracker
    tracker = get_parts_tracker()
    tracker.refresh_from_db()
    captured = tracker.processed_parts.union(tracker.queued_parts)
    print(f"  → {len(captured):,} handled symbols available as donors")
    return captured


# ---------------------------------------------------------------------------
# Step 3 — Match pending to captured by base description
# ---------------------------------------------------------------------------
def find_best_matches(df: pd.DataFrame) -> list[dict]:
    pending  = df[~df["is_captured"]].copy()
    captured = df[df["is_captured"]].copy()

    pending["base"]  = pending["Desc1"].apply(base_desc)
    captured["base"] = captured["Desc1"].apply(base_desc)

    # Build lookup: base -> list of captured rows
    cap_by_base: dict[str, list[dict]] = defaultdict(list)
    for _, row in captured.iterrows():
        b = row["base"]
        if b and len(b) > 5:
            cap_by_base[b].append({
                "symbol": row["sym_norm"],
                "desc1":  str(row.get("Desc1", "")),
            })

    matches = []
    for _, row in pending.iterrows():
        b = row["base"]
        if not b or b not in cap_by_base:
            continue

        pend_desc = str(row.get("Desc1", ""))
        # Pick the captured donor with highest string similarity to pending Desc1
        best = max(cap_by_base[b], key=lambda c: similarity(pend_desc, c["desc1"]))
        matches.append({
            "pending_symbol":   row["sym_norm"],
            "pending_desc1":    pend_desc,
            "donor_symbol":     best["symbol"],
            "donor_desc1":      best["desc1"],
            "similarity":       round(similarity(pend_desc, best["desc1"]), 3),
        })

    print(f"\nMatched {len(matches):,} pending symbols to a captured donor")
    return matches


# ---------------------------------------------------------------------------
# Step 4 — Check R2 for raw images of donor symbol
# ---------------------------------------------------------------------------
def get_raw_keys(r2, bucket: str, symbol: str) -> list[str]:
    """Return list of R2 keys under raw/{symbol}/"""
    res = r2.list_objects_v2(
        Bucket=bucket,
        Prefix=f"raw/{symbol}/",
        MaxKeys=10,
    )
    return [obj["Key"] for obj in res.get("Contents", [])]


# ---------------------------------------------------------------------------
# Step 5 — Copy raw images + queue job
# ---------------------------------------------------------------------------
def copy_and_queue(r2, bucket: str, pending_symbol: str, donor_symbol: str,
                   donor_keys: list[str], job_id: str, dry_run: bool) -> list[str]:
    """
    Copy donor raw images to raw/{pending_symbol}/ and return the new R2 keys.
    The filenames keep the original stem but get the pending_symbol folder.
    """
    new_keys = []
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    for i, src_key in enumerate(donor_keys[:3], start=1):  # max 3 images
        filename = src_key.split("/")[-1]
        dst_key = f"raw/{pending_symbol}/{job_id}_{ts}_{i:02d}_{filename}"
        if not dry_run:
            r2.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": src_key},
                Key=dst_key,
            )
        new_keys.append(dst_key)
    return new_keys


def make_part_entry(pending_symbol: str, raw_keys: list[str]) -> dict:
    """Build the job 'part' entry for one pending symbol (pure, no R2 I/O)."""
    return {
        "symbol_number": pending_symbol,
        "raw_file_paths": [
            {"filename": k.split("/")[-1], "r2_key": k, "content_type": "image/jpeg"}
            for k in raw_keys
        ],
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "proxy_capture": True,
    }


def load_existing_job(r2, bucket: str, job_id: str) -> dict:
    """Read the queued job ONCE at the start (to merge into), or start fresh.

    Previously the job file was re-read and re-written for every single symbol,
    which is O(n^2): the file grows with each append and gets re-uploaded each
    time, so the run slows to a crawl and the half-built job sits in R2 for a
    long time (which is how the nightly trigger caught it mid-build). We now
    read once here and write once at the end instead.
    """
    job_key = f"jobs/queued/{job_id}.json"
    try:
        resp = r2.get_object(Bucket=bucket, Key=job_key)
        job_data = json.loads(resp["Body"].read().decode())
    except Exception:
        job_data = {
            "job_id": job_id,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "parts": [],
        }
    job_data.setdefault("parts", [])
    return job_data


def write_job(r2, bucket: str, job_id: str, job_data: dict) -> None:
    """Write the fully-assembled job to R2 in a single put_object."""
    job_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    r2.put_object(
        Bucket=bucket,
        Key=f"jobs/queued/{job_id}.json",
        Body=json.dumps(job_data, indent=2),
        ContentType="application/json",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview matches without touching R2")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max pending symbols to process (for testing)")
    parser.add_argument("--daily-limit", type=int, default=None,
                        help="Alias for --limit")
    args = parser.parse_args()

    dry_run = args.dry_run
    limit = args.limit or args.daily_limit
    if dry_run:
        print("🔍 DRY-RUN mode — no R2 changes will be made\n")

    print("Step 1/5: Connecting to R2…", flush=True)
    try:
        r2, bucket = make_r2_client()
        # Quick connectivity check with timeout (removed parts/ check as it times out)
        # r2.list_objects_v2(Bucket=bucket, Prefix="parts/", MaxKeys=1)
        print(f"  ✅ Connected to bucket: {bucket}")
    except Exception as e:
        print(f"ERROR: R2 not available — {e}", file=sys.stderr)
        return 1

    # 1. Captured symbols
    captured_syms = get_captured_symbols(r2, bucket)

    # 2. Catalog
    df = load_catalog(captured_syms)

    # 3. Find matches
    matches = find_best_matches(df)

    # Apply limit
    if limit:
        matches = matches[:limit]
        print(f"  (Limited to first {limit} matches)")

    # 4-6. Process each match
    today = datetime.now().strftime("%Y%m%d")
    job_id = f"job_proxy_{today}"

    # Read the queued job ONCE up front, assemble in memory, write ONCE at the end.
    job_data = None if dry_run else load_existing_job(r2, bucket, job_id)
    seen_syms = set() if job_data is None else {p.get("symbol_number") for p in job_data["parts"]}

    results = []
    queued_count = 0
    skipped_no_raw = 0
    skipped_error = 0

    print(f"\nProcessing {len(matches):,} matches → job: {job_id}")
    print("=" * 60)

    for i, m in enumerate(matches, 1):
        pending_sym = m["pending_symbol"]
        donor_sym   = m["donor_symbol"]

        try:
            raw_keys = get_raw_keys(r2, bucket, donor_sym)
            if not raw_keys:
                skipped_no_raw += 1
                results.append({**m, "status": "SKIPPED_NO_RAW", "new_keys": ""})
                continue

            new_keys = copy_and_queue(r2, bucket, pending_sym, donor_sym, raw_keys, job_id, dry_run)

            # Accumulate in memory (dedupe) — no per-symbol R2 read/write
            if job_data is not None and pending_sym not in seen_syms:
                job_data["parts"].append(make_part_entry(pending_sym, new_keys))
                seen_syms.add(pending_sym)

            queued_count += 1
            action = "DRY-RUN" if dry_run else "QUEUED"
            print(f"  [{i:4d}] {action}: {pending_sym} ← {donor_sym}  "
                  f"({m['pending_desc1'][:40]} | sim={m['similarity']})")
            results.append({**m, "status": action, "new_keys": ",".join(new_keys)})

        except Exception as e:
            skipped_error += 1
            print(f"  [{i:4d}] ERROR {pending_sym}: {e}")
            results.append({**m, "status": f"ERROR: {e}", "new_keys": ""})

    # Write the assembled job to R2 in ONE put (was per-symbol before → O(n^2))
    if job_data is not None and job_data["parts"]:
        write_job(r2, bucket, job_id, job_data)
        print(f"\n   Wrote job → jobs/queued/{job_id}.json  ({len(job_data['parts']):,} parts)")

    # 7. Summary
    print("\n" + "=" * 60)
    print("✅ SUMMARY")
    print(f"   Matched:          {len(matches):,}")
    print(f"   Queued:           {queued_count:,}")
    print(f"   Skipped (no raw): {skipped_no_raw:,}")
    print(f"   Errors:           {skipped_error:,}")
    if not dry_run:
        print(f"   Job ID:           {job_id}")

    # Save report
    REPORT_FILE.parent.mkdir(exist_ok=True)
    rdf = pd.DataFrame(results)
    rdf.to_excel(REPORT_FILE, index=False)
    print(f"\n   Full report: {REPORT_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
