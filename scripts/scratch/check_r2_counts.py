import sys
from pathlib import Path
from dotenv import load_dotenv

backend_root = Path(__file__).resolve().parent
load_dotenv(backend_root / ".env")
sys.path.insert(0, str(backend_root))

from app.services.cloudflare_r2 import get_r2_storage

r2 = get_r2_storage()
if not r2:
    print("R2 is None")
    sys.exit(1)

paginator = r2.s3_client.get_paginator('list_objects_v2')
parts = set()
images = 0
for page in paginator.paginate(Bucket=r2.bucket_name, Prefix='parts/'):
    for obj in page.get('Contents', []):
        key = obj['Key']
        images += 1
        paths = key.split('/')
        if len(paths) >= 2:
            parts.add(paths[1])

print(f"R2 Unique Parts (parts/): {len(parts)}, Total Images: {images}")

raw_parts = set()
for page in paginator.paginate(Bucket=r2.bucket_name, Prefix='raw/'):
    for obj in page.get('Contents', []):
        key = obj['Key']
        paths = key.split('/')
        if len(paths) >= 2:
            raw_parts.add(paths[1])
            
print(f"R2 Unique Raw Parts (raw/): {len(raw_parts)}")
print(f"Total Unique across both: {len(parts.union(raw_parts))}")
