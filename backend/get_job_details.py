import os
import sys
import json
import boto3
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# R2 configuration
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

def get_job_symbols(job_id):
    print(f"🔍 Looking for details for job: {job_id}")
    
    # Check completed first
    keys_to_check = [
        f"jobs/completed/{job_id}.json",
        f"jobs/queued/{job_id}.json"
    ]
    
    job_data = None
    found_key = None
    
    for key in keys_to_check:
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            job_data = json.loads(response['Body'].read().decode('utf-8'))
            found_key = key
            break
        except s3.exceptions.NoSuchKey:
            continue
        except Exception as e:
            print(f"Error checking {key}: {e}")
            
    if not job_data:
        print("❌ Job file not found in queued or completed folders.")
        return

    status = job_data.get('status', 'unknown')
    print(f"✅ Found job in: {found_key}")
    print(f"📊 Status: {status}")
    
    parts = job_data.get('parts', [])
    if not parts and 'symbol_number' in job_data:
        # Handle single-part legacy format
        parts = [{'symbol_number': job_data['symbol_number']}]
        
    print(f"📦 Total Parts: {len(parts)}")
    print("=" * 40)
    
    symbols = sorted([p.get('symbol_number') for p in parts])
    
    for i, symbol in enumerate(symbols, 1):
        print(f"{i}. {symbol}")
        
    print("=" * 40)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
    else:
        # Default to today's daily job
        today_str = datetime.now().strftime('%Y%m%d')
        job_id = f"job_daily_{today_str}"
        
    get_job_symbols(job_id)
