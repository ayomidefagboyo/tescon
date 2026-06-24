#!/usr/bin/env python3
"""
check_queue_state.py — Ground-truth report of the R2 job queue.

Answers:
  * What is still in jobs/queued/  (waiting to be processed)
  * What is in jobs/processing/ or jobs/failed/ (stuck / errored)
  * Which recently-"completed" jobs actually had image FAILURES
    (symbols that did NOT go through even though the job was marked done)
  * With --verify: for every job from the last 2 days, check whether each
    symbol now has an image under parts/{symbol}/ in R2 — the real
    "did it go through?" test.

Run:
    python3 backend/check_queue_state.py
    python3 backend/check_queue_state.py --verify
"""
import os, json, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import boto3
from botocore.config import Config
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent
load_dotenv(BACKEND / ".env")

acct = os.getenv("CLOUDFLARE_ACCOUNT_ID")
s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{acct}.r2.cloudflarestorage.com",
    aws_access_key_id=os.getenv("CLOUDFLARE_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("CLOUDFLARE_SECRET_ACCESS_KEY"),
    region_name="auto",
    config=Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 3}),
)
B = os.getenv("CLOUDFLARE_BUCKET_NAME", "tescon-images")


def scan(prefix):
    p = s3.get_paginator("list_objects_v2")
    out = []
    for pg in p.paginate(Bucket=B, Prefix=prefix):
        out += pg.get("Contents", [])
    return [o for o in out if o["Key"].endswith(".json")]


def get_job(key):
    r = s3.get_object(Bucket=B, Key=key)
    return json.loads(r["Body"].read().decode())


def has_image(symbol):
    r = s3.list_objects_v2(Bucket=B, Prefix=f"parts/{symbol}/", MaxKeys=1)
    return r.get("KeyCount", 0) > 0


ap = argparse.ArgumentParser()
ap.add_argument("--verify", action="store_true",
                help="check parts/ coverage for jobs from the last 2 days")
args = ap.parse_args()

print(f"\nR2 bucket: {B}")
print("=" * 70)

# 1) Active states — these should be SMALL
for pre in ["jobs/queued/", "jobs/processing/", "jobs/failed/"]:
    objs = scan(pre)
    print(f"\n=== {pre}  ({len(objs)} job file(s)) ===")
    if not objs:
        print("   (none)")
    for o in sorted(objs, key=lambda x: x["LastModified"]):
        try:
            jd = get_job(o["Key"]); n = len(jd.get("parts", [])); st = jd.get("status", "?")
        except Exception as e:
            n, st = "?", f"read-err {e}"
        print(f"   {o['LastModified']:%Y-%m-%d %H:%M}  parts={n:<5} status={st}  {o['Key'].split('/')[-1]}")

# 2) Completed — surface failures and anything not from today
comp = scan("jobs/completed/")
print(f"\n=== jobs/completed/  ({len(comp)} job file(s)) — 25 most recent ===")
flagged = []
for o in sorted(comp, key=lambda x: x["LastModified"])[-25:]:
    try:
        jd = get_job(o["Key"])
        n = len(jd.get("parts", []))
        proc = jd.get("processed_files_count", "?")
        fail = jd.get("failed_files_count", "?")
        st = jd.get("status", "?")
    except Exception as e:
        n = proc = fail = st = "?"
    mark = "  <== HAS FAILURES" if isinstance(fail, int) and fail > 0 else ""
    print(f"   {o['LastModified']:%Y-%m-%d %H:%M}  parts={n:<5} ok={proc} fail={fail} {st}{mark}  {o['Key'].split('/')[-1]}")
    if isinstance(fail, int) and fail > 0:
        flagged.append(o["Key"].split("/")[-1])

if flagged:
    print(f"\n   completed-with-failures: {', '.join(flagged)}")

# 3) Optional deep check: did each symbol actually land in parts/ ?
if args.verify:
    cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    pool = scan("jobs/queued/") + scan("jobs/processing/") + comp
    targets = [o for o in pool if o["LastModified"] >= cutoff]
    print(f"\n=== parts/ coverage for {len(targets)} job(s) from the last 2 days ===")
    grand_missing = []
    for o in sorted(targets, key=lambda x: x["LastModified"]):
        try:
            jd = get_job(o["Key"])
        except Exception:
            continue
        syms = [p["symbol_number"] for p in jd.get("parts", [])]
        missing = [s for s in syms if not has_image(s)]
        grand_missing += missing
        tag = f"{len(missing)} MISSING" if missing else "all present"
        print(f"   {o['Key'].split('/')[-1]}: {len(syms)} symbols -> {tag}")
        if missing:
            print("       " + ", ".join(missing[:30]) + (" ..." if len(missing) > 30 else ""))
    if grand_missing:
        uniq = sorted(set(grand_missing))
        print(f"\n   TOTAL symbols still missing an image: {len(uniq)}")
        print("   (these are the ones that did NOT go through)")
