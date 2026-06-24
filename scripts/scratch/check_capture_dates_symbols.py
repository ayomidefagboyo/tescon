import os
import sys
from collections import defaultdict
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
    
    print("Checking raw/ captures for unique symbol numbers...")
    raw_symbols_per_day = defaultdict(set)
    
    for page in paginator.paginate(Bucket=r2.bucket_name, Prefix='raw/'):
        for obj in page.get('Contents', []):
            key = obj['Key']
            # path is usually raw/SYMBOL_NUMBER/filename
            parts = key.split('/')
            if len(parts) >= 3:
                symbol_num = parts[1]
                date_str = obj['LastModified'].strftime('%Y-%m-%d')
                raw_symbols_per_day[date_str].add(symbol_num)
            
    print("Highest raw symbol numbers captured in a day:")
    # convert to (date, count) and sort
    counts = [(date, len(symbols)) for date, symbols in raw_symbols_per_day.items()]
    counts.sort(key=lambda x: x[1], reverse=True)
    
    for d, c in counts[:5]:
        print(f"{d}: {c} symbol numbers")

except Exception as e:
    print(f"Error: {e}")
