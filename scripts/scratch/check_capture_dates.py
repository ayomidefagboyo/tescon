import os
import sys
from collections import Counter
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.abspath("app"))

try:
    from services.cloudflare_r2 import get_r2_storage
    r2 = get_r2_storage()
    if not r2:
        print("Failed to connect to R2")
        sys.exit(1)
        
    paginator = r2.s3_client.get_paginator('list_objects_v2')
    
    print("Checking raw/ captures...")
    raw_dates = Counter()
    for page in paginator.paginate(Bucket=r2.bucket_name, Prefix='raw/'):
        for obj in page.get('Contents', []):
            date_str = obj['LastModified'].strftime('%Y-%m-%d')
            raw_dates[date_str] += 1
            
    print("Highest raw captures in a day:")
    for d, c in raw_dates.most_common(5):
        print(f"{d}: {c} images")

except Exception as e:
    print(f"Error: {e}")
