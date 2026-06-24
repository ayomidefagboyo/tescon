import sys
import os
from pathlib import Path
import json

sys.path.append('./app')
from dotenv import load_dotenv
load_dotenv('.env')

try:
    from services.cloudflare_r2 import get_r2_storage
except ImportError:
    print("Cannot import cloudflare_r2")
    sys.exit(1)

import pandas as pd

def normalize(value) -> str:
    if pd.isna(value): return ""
    return str(value).strip()

def main():
    r2 = get_r2_storage()
    captured = set()
    
    print("Fetching processed parts from R2...")
    paginator = r2.s3_client.get_paginator("list_objects_v2")
    
    # 1. Processed in parts/
    for page in paginator.paginate(Bucket=r2.bucket_name, Prefix="parts/"):
        for obj in page.get("Contents", []):
            parts = obj["Key"].split("/")
            if len(parts) >= 2 and parts[1]:
                captured.add(normalize(parts[1]))
                
    # 2. Queued in jobs/
    print("Fetching queued jobs from R2...")
    for page in paginator.paginate(Bucket=r2.bucket_name, Prefix="jobs/queued/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".json"):
                res = r2.s3_client.get_object(Bucket=r2.bucket_name, Key=key)
                try:
                    data = json.loads(res["Body"].read().decode("utf-8"))
                    if "parts" in data:
                        for p in data["parts"]:
                            sym = p.get("symbol_number")
                            if sym:
                                captured.add(normalize(sym))
                except Exception as e:
                    print(f"Error reading {key}: {e}")
                    
    # 3. Just in case, scan raw/
    print("Fetching raw items from R2...")
    for page in paginator.paginate(Bucket=r2.bucket_name, Prefix="raw/", Delimiter="/"):
        for prefix in page.get("CommonPrefixes", []):
            parts = prefix.get("Prefix", "").split("/")
            if len(parts) >= 2 and parts[1]:
                captured.add(normalize(parts[1]))
                
    print(f"Total symbols considered captured or queued: {len(captured)}")
    
    master_file = "Total EGTL Photo Project.xlsx"
    print(f"Reading master catalog {master_file}...")
    df = pd.read_excel(master_file, sheet_name="Photo Data")
    
    # Filter
    df['normalized_symbol'] = df['Symbol Number'].apply(normalize)
    pending_df = df[~df['normalized_symbol'].isin(captured)].copy()
    pending_df.drop(columns=['normalized_symbol'], inplace=True)
    
    out_file = "Pending_Symbols_Export.xlsx"
    print(f"Exporting {len(pending_df)} pending symbols to {out_file}...")
    pending_df.to_excel(out_file, index=False)
    print("Done!")

if __name__ == "__main__":
    main()
