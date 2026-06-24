import sys
import json
from pathlib import Path
from dotenv import load_dotenv

backend_root = Path(__file__).resolve().parent
project_root = backend_root.parent
load_dotenv(backend_root / ".env")
sys.path.insert(0, str(backend_root))

from app.services.cloudflare_r2 import get_r2_storage

r2 = get_r2_storage()
paginator = r2.s3_client.get_paginator('list_objects_v2')
r2_parts = set()
for page in paginator.paginate(Bucket=r2.bucket_name, Prefix='parts/'):
    for obj in page.get('Contents', []):
        paths = obj['Key'].split('/')
        if len(paths) >= 2:
            r2_parts.add(paths[1])

print(f"Total parts processed on R2: {len(r2_parts)}")

download_state_file = project_root / 'downloads' / 'download_state.json'
downloaded_parts = set()
if download_state_file.exists():
    with open(download_state_file, 'r') as f:
        data = json.load(f)
        downloaded_parts = set(data.get('downloaded_parts', []))

print(f"Total parts marked as downloaded in state file: {len(downloaded_parts)}")

# Also check physical folders in downloads/
physical_downloads = set()
for batch_dir in (project_root / 'downloads').glob('Batch_*'):
    if batch_dir.is_dir():
        for part_dir in batch_dir.iterdir():
            if part_dir.is_dir():
                physical_downloads.add(part_dir.name)

print(f"Total parts physically present in downloads folders: {len(physical_downloads)}")

# Use physical downloads as source of truth if it's larger or use state file
local_parts = downloaded_parts.union(physical_downloads)
print(f"Total unique parts downloaded locally: {len(local_parts)}")

missing_locally = r2_parts - local_parts
missing_on_r2 = local_parts - r2_parts

print("-" * 40)
print(f"Stats:")
print(f"  - Parts on R2 but NOT downloaded yet: {len(missing_locally)}")
print(f"  - Parts downloaded but NOT on R2 (should be 0): {len(missing_on_r2)}")
print(f"  - Parts perfectly synced: {len(r2_parts.intersection(local_parts))}")
