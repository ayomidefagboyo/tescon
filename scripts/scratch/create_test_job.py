#!/usr/bin/env python3
"""Create a test daily job for testing the workflow"""
import os
import json
import boto3
from datetime import datetime
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

# Create test job
job_id = f"job_daily_{datetime.now().strftime('%Y%m%d')}"

# Sample job with test data
job_metadata = {
    "job_id": job_id,
    "status": "queued",
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
    "parts": [
        {
            "symbol_number": "TEST123",
            "raw_file_paths": [
                {
                    "filename": "test1.jpg",
                    "r2_key": "raw/TEST123/test1.jpg",
                    "content_type": "image/jpeg"
                },
                {
                    "filename": "test2.jpg",
                    "r2_key": "raw/TEST123/test2.jpg",
                    "content_type": "image/jpeg"
                },
                {
                    "filename": "test3.jpg",
                    "r2_key": "raw/TEST123/test3.jpg",
                    "content_type": "image/jpeg"
                }
            ],
            "uploaded_at": datetime.now().isoformat()
        }
    ]
}

# Upload to R2
job_key = f"jobs/queued/{job_id}.json"

try:
    s3.put_object(
        Bucket=bucket,
        Key=job_key,
        Body=json.dumps(job_metadata, indent=2),
        ContentType="application/json"
    )
    print(f"✅ Created test job: {job_id}")
    print(f"📁 Location: {job_key}")
    print(f"\n📋 Job contents:")
    print(json.dumps(job_metadata, indent=2))
    print(f"\n🚀 You can now trigger the workflow with job_id: {job_id}")
except Exception as e:
    print(f"❌ Failed to create job: {e}")
