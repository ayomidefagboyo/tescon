#!/usr/bin/env python3
import os
import sys
import json
import pandas as pd
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
MASTER_CATALOG = BACKEND_ROOT / "data" / "Total EGTL Photo Project.xlsx"
PROXY_REPORT = PROJECT_ROOT / "reports" / "proxy_capture_report.xlsx"
OUTPUT_EXCEL = PROJECT_ROOT / "reports" / "Remaining_To_Shoot_By_Location.xlsx"

import sys
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")
import boto3
from botocore.config import Config

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
        config=Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 3}, signature_version="s3v4"),
    )
    return client, bucket

def get_captured_symbols(r2, bucket):
    print("Scanning R2 for captured symbols...")
    paginator = r2.get_paginator("list_objects_v2")
    captured = set()
    for page in paginator.paginate(Bucket=bucket, Prefix="parts/", Delimiter="/"):
        for prefix in page.get("CommonPrefixes", []):
            sym = prefix["Prefix"].split("/")[1]
            if sym:
                captured.add(sym)
    return captured

def get_queued_symbols_from_local_report():
    print("Reading local proxy capture report to find queued symbols...")
    queued = set()
    if PROXY_REPORT.exists():
        df = pd.read_excel(PROXY_REPORT)
        for _, row in df.iterrows():
            if str(row.get("status", "")).upper() == "QUEUED":
                queued.add(str(row.get("pending_symbol")).strip())
    print(f"Found {len(queued)} symbols queued from local report.")
    return queued

def main():
    # Use the fast, accurate local tracker instead of scanning R2 manually
    from app.services.parts_tracker import get_parts_tracker
    tracker = get_parts_tracker()
    tracker.refresh_from_db()
    
    captured_syms = tracker.processed_parts
    queued_syms = tracker.queued_parts
    
    handled_syms = captured_syms.union(queued_syms)
    
    print("Loading Master Catalog...")
    df = pd.read_excel(MASTER_CATALOG, sheet_name="Photo Data")
    df["sym_norm"] = df["Symbol Number"].astype(str).str.strip().str.lstrip('0')
    
    # Filter pending
    pending_df = df[~df["sym_norm"].isin(handled_syms)].copy()
    print(f"Total handled (captured + queued): {len(handled_syms)}")
    print(f"Total remaining to physically shoot: {len(pending_df)}")
    
    # Sort by Location
    pending_df.sort_values(by=["Location", "Symbol Number"], inplace=True)
    
    # Drop temp column and select desired columns
    columns_to_keep = ['Symbol Number', 'Location', 'Desc1', 'Desc2', 'BOH']
    pending_df = pending_df[columns_to_keep]
    
    # Add S/N column as the first column
    pending_df.insert(0, 'S/N', range(1, 1 + len(pending_df)))
    
    # Save
    OUTPUT_EXCEL.parent.mkdir(exist_ok=True)
    pending_df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"Report saved to: {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()
