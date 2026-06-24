#!/usr/bin/env python3
"""
check_captured_status.py
========================
Answer: "the symbols I captured with the app yesterday / two days ago —
did they actually get processed?"  Reads R2 LIVE.

For each symbol it reports:
  DONE     -> parts/{symbol}/ exists  (final processed images are there)
  STAGED   -> only raw/{symbol}/ or sitting in a jobs/queued/*.json (not processed yet)
  PENDING  -> nothing in R2 yet

Modes:
  # check the daily capture jobs for specific dates (default: yesterday + 2 days ago)
  python3 backend/check_captured_status.py
  python3 backend/check_captured_status.py --dates 20260621,20260622

  # check specific symbol numbers directly
  python3 backend/check_captured_status.py --symbols 58009212,58009254,58009296
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import boto3
from botocore.config import Config
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent
load_dotenv(BACKEND_ROOT / ".env")


def make_r2():
    acct = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    if not all([acct, os.getenv("CLOUDFLARE_ACCESS_KEY_ID"), os.getenv("CLOUDFLARE_SECRET_ACCESS_KEY")]):
        raise RuntimeError("Missing R2 credentials in backend/.env")
    c = boto3.client(
        "s3",
        endpoint_url=f"https://{acct}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("CLOUDFLARE_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("CLOUDFLARE_SECRET_ACCESS_KEY"),
        region_name="auto",
        config=Config(connect_timeout=10, read_timeout=30,
                      retries={"max_attempts": 3}, signature_version="s3v4"),
    )
    return c, os.getenv("CLOUDFLARE_BUCKET_NAME", "tescon-images")


def n(v) -> str:
    return str(v).strip()


def _has(r2, b, prefix) -> bool:
    return r2.list_objects_v2(Bucket=b, Prefix=prefix, MaxKeys=1).get("KeyCount", 0) > 0


def status(r2, b, sym) -> str:
    sym = n(sym)
    if _has(r2, b, f"parts/{sym}/"):
        return "DONE"
    if _has(r2, b, f"raw/{sym}/"):
        return "STAGED"
    return "PENDING"


def load_job_symbols(r2, b, key) -> list[str]:
    data = json.loads(r2.get_object(Bucket=b, Key=key)["Body"].read())
    return [n(p["symbol_number"]) for p in data.get("parts", []) if p.get("symbol_number")]


def find_day_jobs(r2, b, dates) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    pg = r2.get_paginator("list_objects_v2")
    for state in ["jobs/completed/", "jobs/queued/", "jobs/processing/", "jobs/failed/"]:
        for page in pg.paginate(Bucket=b, Prefix=state):
            for o in page.get("Contents", []):
                name = o["Key"].split("/")[-1]
                if not name.endswith(".json"):
                    continue
                for d in dates:
                    if f"job_daily_{d}" in name or f"job_proxy_{d}" in name:
                        found.setdefault(d, []).append(o["Key"])
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", help="comma-sep YYYYMMDD (default: yesterday + 2 days ago)")
    ap.add_argument("--symbols", help="comma-sep symbol numbers to check directly")
    args = ap.parse_args()

    r2, b = make_r2()
    r2.list_objects_v2(Bucket=b, Prefix="parts/", MaxKeys=1)  # connectivity probe
    print(f"Connected: {b}\n")

    # --- direct symbol mode --------------------------------------------------
    if args.symbols:
        syms = [s.strip() for s in args.symbols.split(",") if s.strip()]
        print(f"Checking {len(syms)} symbol(s):\n")
        tally = {"DONE": 0, "STAGED": 0, "PENDING": 0}
        for s in syms:
            st = status(r2, b, s)
            tally[st] += 1
            print(f"  {s:<14} {st}")
        print(f"\n  DONE={tally['DONE']}  STAGED={tally['STAGED']}  PENDING={tally['PENDING']}")
        return 0

    # --- by-date mode --------------------------------------------------------
    if args.dates:
        dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    else:
        today = datetime.now()
        dates = [(today - timedelta(days=1)).strftime("%Y%m%d"),
                 (today - timedelta(days=2)).strftime("%Y%m%d")]

    print(f"Looking for capture jobs on: {', '.join(dates)}\n")
    jobs = find_day_jobs(r2, b, dates)
    if not jobs:
        print("No job_daily_/job_proxy_ files found for those dates.")
        return 0

    for d in dates:
        keys = jobs.get(d, [])
        if not keys:
            print(f"=== {d}: no job files found ===\n")
            continue
        syms = sorted({s for k in keys for s in load_job_symbols(r2, b, k)})
        missing = [s for s in syms if status(r2, b, s) != "DONE"]
        print(f"=== {d}: {len(syms)} captured symbols across {len(keys)} job file(s) ===")
        for k in keys:
            print(f"     {k.split('/')[-1]}")
        print(f"     processed (DONE): {len(syms) - len(missing)}     NOT processed: {len(missing)}")
        if missing:
            print("     not done:", ", ".join(missing[:40]) + (" ..." if len(missing) > 40 else ""))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
