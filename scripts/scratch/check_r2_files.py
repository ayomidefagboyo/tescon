#!/usr/bin/env python3
"""Check R2 storage for duplicate uploads"""
import os
import sys
import boto3
from collections import defaultdict

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize R2 client
s3 = boto3.client(
    's3',
    endpoint_url=os.getenv('R2_ENDPOINT'),
    aws_access_key_id=os.getenv('R2_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    region_name='auto'
)

bucket = os.getenv('R2_BUCKET_NAME', 'tescon-images')

# Get symbol number from command line
if len(sys.argv) < 2:
    print("Usage: python check_r2_files.py <symbol_number>")
    sys.exit(1)

symbol_number = sys.argv[1]
prefix = f"raw/{symbol_number}/"

print(f"🔍 Checking files for symbol: {symbol_number}")
print(f"📁 Prefix: {prefix}\n")

# List all files
response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)

if 'Contents' not in response:
    print("❌ No files found")
    sys.exit(0)

files = response['Contents']
print(f"📊 Total files found: {len(files)}\n")

# Group by timestamp
by_timestamp = defaultdict(list)
for obj in files:
    key = obj['Key']
    filename = key.split('/')[-1]
    # Extract timestamp from filename: job_daily_YYYYMMDD_HHMMSS_01_filename.jpg
    parts = filename.split('_')
    if len(parts) >= 5:
        timestamp = parts[3]  # HHMMSS
        by_timestamp[timestamp].append({
            'key': key,
            'size': obj['Size'],
            'modified': obj['LastModified']
        })

# Display results
for timestamp, file_list in sorted(by_timestamp.items()):
    print(f"⏰ Timestamp: {timestamp}")
    for f in file_list:
        print(f"   📄 {f['key']}")
        print(f"      Size: {f['size']} bytes")
        print(f"      Modified: {f['modified']}")
    print()

if len(by_timestamp) > 1:
    print(f"⚠️  WARNING: Found {len(by_timestamp)} different upload timestamps!")
    print("   This suggests multiple uploads for the same part.")
else:
    print("✅ All files from single upload session")
