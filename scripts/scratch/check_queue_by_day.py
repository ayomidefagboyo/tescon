#!/usr/bin/env python3
"""
check_queue_by_day.py — What is ACTUALLY queued, split by the day it was queued.

Reads every recent job manifest in R2 (jobs/queued, jobs/processing, jobs/failed,
jobs/completed), then checks each symbol against a single fast parts/ scan to see
how many have REALLY been processed (a parts/{symbol}/ folder exists) versus how
many are still waiting. Buckets the result by the day the job was queued.

Run:
    python3 backend/check_queue_by_day.py
"""
import os
import re
import json
from collections import defaultdict
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

STATES = ["jobs/queued/", "jobs/processing/", "jobs/failed/", "jobs/completed/"]
READ_CUTOFF = datetime.now(timezone.utc) - timedelta(days=3)  # only read recent manifests


def done_symbols() -> set[str]:
    """Fast prefix scan of parts/ -> set of symbols actually processed in R2."""
    p = s3.get_paginator("list_objects_v2")
    out = set()
    for pg in p.paginate(Bucket=B, Prefix="parts/", Delimiter="/"):
        for pre in pg.get("CommonPrefixes", []):
            sym = pre["Prefix"].split("/")[1]
            if sym:
                out.add(sym.strip())
    return out


def list_job_files(prefix):
    p = s3.get_paginator("list_objects_v2")
    out = []
    for pg in p.paginate(Bucket=B, Prefix=prefix):
        for o in pg.get("Contents", []):
            if o["Key"].endswith(".json"):
                out.append(o)
    return out


def job_day(key, last_modified) -> str:
    """Day the job was queued: prefer the YYYYMMDD baked into the job id."""
    m = re.search(r"(20\d{6})", key.split("/")[-1])
    return m.group(1) if m else last_modified.strftime("%Y%m%d")


def main():
    s3.list_objects_v2(Bucket=B, Prefix="parts/", MaxKeys=1)
    print(f"Connected: {B}\n")

    print("Scanning parts/ for what's actually processed…")
    done = done_symbols()
    print(f"  → {len(done):,} symbols done in R2\n")

    today = datetime.now().strftime("%Y%m%d")
    yest = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    tag_of = {today: "TODAY", yest: "YESTERDAY"}

    by_day = defaultdict(lambda: {"symbols": set(), "states": defaultdict(int)})

    print("RECENT JOB FILES  (waiting = symbol has no parts/ folder yet)")
    print("=" * 74)
    for st in STATES:
        label = st.split("/")[1]
        jobs = list_job_files(st)
        recent = [o for o in jobs if o["LastModified"] >= READ_CUTOFF]
        older = len(jobs) - len(recent)
        suffix = f"   (+{older} older, not read)" if older else ""
        print(f"\n[{label}]  {len(jobs)} file(s){suffix}")
        if not recent:
            print("   (nothing in the last 3 days)")
        for o in sorted(recent, key=lambda x: x["LastModified"]):
            try:
                jd = json.loads(s3.get_object(Bucket=B, Key=o["Key"])["Body"].read())
                syms = [str(p.get("symbol_number", "")).strip()
                        for p in jd.get("parts", []) if p.get("symbol_number")]
            except Exception as e:
                print(f"   {o['Key'].split('/')[-1]}: read-err {e}")
                continue
            d = job_day(o["Key"], o["LastModified"])
            n_done = sum(1 for s in syms if s in done)
            n_wait = len(syms) - n_done
            tag = tag_of.get(d, d)
            print(f"   {o['LastModified']:%m-%d %H:%M}  {o['Key'].split('/')[-1]:<26} "
                  f"parts={len(syms):<5} done={n_done:<5} waiting={n_wait:<5} [{tag}]")
            bd = by_day[d]
            bd["symbols"].update(syms)
            bd["states"][label] += len(syms)

    print("\n" + "=" * 74)
    print("ROLLUP — unique symbols queued, by day")
    print("=" * 74)
    for d, tag in [(yest, "YESTERDAY"), (today, "TODAY")]:
        bd = by_day.get(d)
        if not bd:
            print(f"\n{tag} ({d}): no job files")
            continue
        syms = bd["symbols"]
        n_done = sum(1 for s in syms if s in done)
        n_wait = len(syms) - n_done
        print(f"\n{tag} ({d}): {len(syms):,} unique symbols queued")
        print(f"   ✅ already processed into parts/: {n_done:,}")
        print(f"   ⏳ still waiting (not in parts/):  {n_wait:,}")
        print("   states: " + ", ".join(f"{k}={v}" for k, v in bd["states"].items()))


if __name__ == "__main__":
    main()
