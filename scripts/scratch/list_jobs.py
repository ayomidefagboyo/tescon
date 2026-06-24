#!/usr/bin/env python3
"""List all jobs in R2 storage"""
import os
import json
import boto3
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

print("🔍 Checking for jobs in R2...\n")

# Check queued jobs
print("📋 QUEUED JOBS:")
print("-" * 50)
try:
    response = s3.list_objects_v2(Bucket=bucket, Prefix='jobs/queued/')
    if 'Contents' in response:
        for obj in response['Contents']:
            if obj['Key'].endswith('.json'):
                print(f"  ✅ {obj['Key']}")
                print(f"     Size: {obj['Size']} bytes")
                print(f"     Modified: {obj['LastModified']}")
                
                # Get job details
                job_response = s3.get_object(Bucket=bucket, Key=obj['Key'])
                job_data = json.loads(job_response['Body'].read().decode('utf-8'))
                parts_count = len(job_data.get('parts', []))
                print(f"     Parts: {parts_count}")
                print()
    else:
        print("  ❌ No queued jobs found")
except Exception as e:
    print(f"  ❌ Error: {e}")

print()

# Check processing jobs
print("⚙️  PROCESSING JOBS:")
print("-" * 50)
try:
    response = s3.list_objects_v2(Bucket=bucket, Prefix='jobs/processing/')
    if 'Contents' in response:
        for obj in response['Contents']:
            if obj['Key'].endswith('.json'):
                print(f"  ⏳ {obj['Key']}")
                print(f"     Modified: {obj['LastModified']}")
    else:
        print("  ❌ No processing jobs found")
except Exception as e:
    print(f"  ❌ Error: {e}")

print()

# Check completed jobs
print("✅ COMPLETED JOBS:")
print("-" * 50)
try:
    response = s3.list_objects_v2(Bucket=bucket, Prefix='jobs/completed/')
    if 'Contents' in response:
        for obj in response['Contents']:
            if obj['Key'].endswith('.json'):
                print(f"  ✅ {obj['Key']}")
                print(f"     Modified: {obj['LastModified']}")
    else:
        print("  ❌ No completed jobs found")
except Exception as e:
    print(f"  ❌ Error: {e}")
