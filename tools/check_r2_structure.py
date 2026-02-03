
import boto3
import os

# Credentials
R2_ENDPOINT = "https://1c53aea24561b07a82241cbbdafdd753.r2.cloudflarestorage.com"
R2_ACCESS_KEY = "737bb1704aa4d0c57ed52f593ba0fc0e"
R2_SECRET_KEY = "f8aa8d180dea21296bfd9fb938a759a1ffd6d5c3282490c3bd03aeccefefa7b4"
R2_BUCKET = "tescon-images"

def check_structure():
    print(f"🔍 Checking structure of raw/84130406/...")
    
    # Initialize R2
    r2 = boto3.client('s3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name='auto'
    )
    
    # List objects
    response = r2.list_objects_v2(
        Bucket=R2_BUCKET,
        Prefix='raw/84130406/'
    )
    
    if 'Contents' in response:
        print(f"✅ Found {len(response['Contents'])} files:")
        for obj in response['Contents'][:5]:
            print(f" - {obj['Key']}")
    else:
        print("❌ No files found in raw/84130406/")

if __name__ == "__main__":
    check_structure()
