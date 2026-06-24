import pandas as pd
import boto3
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def find_remaining_gta_items():
    print("🔍 Searching for remaining GTA items...")
    
    # 1. Load GTA parts
    try:
        df = pd.read_excel('egtl_GTA_BOH_filtered.xlsx')
        gta_parts = df[['Symbol Number', 'Location', 'Desc1']].to_dict('records')
        print(f"📊 Total GTA parts to do: {len(gta_parts)}")
    except Exception as e:
        print(f"❌ Failed to load Excel: {e}")
        return

    # 2. Check R2 for processed/queued
    endpoint = os.getenv('CLOUDFLARE_ENDPOINT') or f"https://{os.getenv('CLOUDFLARE_ACCOUNT_ID')}.r2.cloudflarestorage.com"
    access_key = os.getenv('CLOUDFLARE_ACCESS_KEY_ID')
    secret_key = os.getenv('CLOUDFLARE_SECRET_ACCESS_KEY')
    bucket = os.getenv('CLOUDFLARE_BUCKET_NAME')
    
    s3 = boto3.client(
        's3', 
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='auto'
    )
    
    # List all folders in 'parts/' to see what's processed
    print("☁️  Checking processed parts in R2...")
    processed_symbols = set()
    paginator = s3.get_paginator('list_objects_v2')
    
    # We check common prefixes 'parts/' and 'raw/'
    for prefix in ['parts/', 'raw/']:
        print(f"   Checking {prefix}...")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    # Key format: parts/SYMBOL/filename.png
                    parts = obj['Key'].split('/')
                    if len(parts) > 1:
                        symbol = parts[1]
                        processed_symbols.add(symbol)
    
    print(f"✅ Found {len(processed_symbols)} symbols already in R2 (processed or raw)")
    
    # 3. Filter remaining
    remaining = []
    processed_count = 0
    
    print("\n📋 Status:")
    for part in gta_parts:
        symbol = str(part['Symbol Number']).strip()
        location = str(part['Location']).strip()
        desc = str(part['Desc1']).strip()
        
        if symbol in processed_symbols:
            processed_count += 1
        else:
            remaining.append({
                'Symbol': symbol,
                'Location': location,
                'Description': desc
            })
            
    print(f"   ✅ Done: {processed_count}")
    print(f"   ⏳ Remaining: {len(remaining)}")
    print("=" * 60)

    if processed_count > 0:
        print("\n✅ COMPLETED GTA ITEMS (In R2):")
        print(f"{'Symbol':<15} | {'Location':<15} | {'Description'}")
        print("-" * 60)
        # Find the completed items to print
        completed_list = []
        for part in gta_parts:
            symbol = str(part['Symbol Number']).strip()
            if symbol in processed_symbols:
                completed_list.append(part)
        
        for item in completed_list:
            print(f"{str(item['Symbol Number']).strip():<15} | {str(item['Location']).strip():<15} | {str(item['Desc1']).strip()}")
        print("=" * 60)
    
    if remaining:
        print("\n⏳ REMAINING ITEMS TO DO (GTA):")
        print(f"{'Symbol':<15} | {'Location':<15} | {'Description'}")
        print("-" * 60)
        for item in remaining:
            print(f"{item['Symbol']:<15} | {item['Location']:<15} | {item['Description']}")
    else:
        print("🎉 All GTA items are done!")

if __name__ == "__main__":
    find_remaining_gta_items()
