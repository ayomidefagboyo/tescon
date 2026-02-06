import os
import boto3
from dotenv import load_dotenv

load_dotenv()

# R2 configuration
endpoint = os.getenv('CLOUDFLARE_ENDPOINT') or f"https://{os.getenv('CLOUDFLARE_ACCOUNT_ID')}.r2.cloudflarestorage.com"
access_key = os.getenv('CLOUDFLARE_ACCESS_KEY_ID')
secret_key = os.getenv('CLOUDFLARE_SECRET_ACCESS_KEY')
bucket = os.getenv('CLOUDFLARE_BUCKET_NAME')

print(f"Checking bucket: {bucket}")
print(f"Endpoint: {endpoint}")

s3 = boto3.client(
    's3',
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name='auto'
)

prefix = 'jobs/queued/'
print(f"Listing objects with prefix: {prefix}")

try:
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if 'Contents' in response:
        for obj in response['Contents']:
            print(f" - {obj['Key']} ({obj['Size']} bytes)")
    else:
        print("No jobs found in queue.")
except Exception as e:
    print(f"Error: {e}")
