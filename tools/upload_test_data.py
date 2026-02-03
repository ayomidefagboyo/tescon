
import os
import sys
import subprocess
import time
from datetime import datetime

# Install boto3 and pillow if not present
try:
    import boto3
    from PIL import Image
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "boto3", "pillow"])
    import boto3
    from PIL import Image
    
import io

# Credentials
R2_ENDPOINT = "https://1c53aea24561b07a82241cbbdafdd753.r2.cloudflarestorage.com"
R2_ACCESS_KEY = "737bb1704aa4d0c57ed52f593ba0fc0e"
R2_SECRET_KEY = "f8aa8d180dea21296bfd9fb938a759a1ffd6d5c3282490c3bd03aeccefefa7b4"
R2_BUCKET = "tescon-images"

TEST_JOB_ID = "job_test_system_check"

def setup_test_data():
    print(f"🚀 Setting up test data for job: {TEST_JOB_ID}")
    
    # Initialize R2
    r2 = boto3.client('s3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name='auto'  # Required for R2
    )
    
    # Create test images
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)] # Red, Green, Blue
    
    for i, color in enumerate(colors):
        # Create image
        img = Image.new('RGB', (500, 500), color=color)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        # Define path: raw_images/JOB_ID/SYMBOL/filename
        symbol = f"TEST{i+1}"
        filename = f"image_{i+1}.png"
        key = f"raw_images/{TEST_JOB_ID}/{symbol}/{filename}"
        
        # Upload
        print(f"📤 Uploading {key}...")
        r2.put_object(Bucket=R2_BUCKET, Key=key, Body=buf.getvalue())
        
    print("✅ Test data uploaded successfully!")

if __name__ == "__main__":
    setup_test_data()
