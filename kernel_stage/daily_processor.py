# Enhanced REMBG Daily Batch Processor for Kaggle
# This replaces PicWish API with $6,900 savings

# Install dependencies
import os
import shutil
import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Install required packages
install("numpy<2.0.0")
install("rembg==2.0.61")
install("onnxruntime")
install("boto3")
install("requests")
install("pandas")
install("openpyxl")
# torch/torchvision are usually pre-installed on Kaggle but we can ensure cpu version if needed
# subprocess.check_call([sys.executable, "-m", "pip", "install", "torch", "torchvision", "--index-url", "https://download.pytorch.org/whl/cpu"])

import boto3
import zipfile
from pathlib import Path
from datetime import datetime
import time
from kaggle_secrets import UserSecretsClient

# Add current directory to Python path
sys.path.append('/kaggle/working')
sys.path.append('.')

# Setup: Copy files from Read-Only Input to Read-Write Working Directory
print("⚙️ Setting up environment...")

INPUT_DIR = '/kaggle/input/enhanced-rembg-processor'
WORKING_DIR = '/kaggle/working'

if os.path.exists(INPUT_DIR):
    print(f"✅ Found input dataset at {INPUT_DIR}")
    
    # Copy egtl.xlsx
    if os.path.exists(os.path.join(INPUT_DIR, 'egtl.xlsx')):
        shutil.copy(os.path.join(INPUT_DIR, 'egtl.xlsx'), os.path.join(WORKING_DIR, 'egtl.xlsx'))
        print("✅ Copied egtl.xlsx to working directory")
        
    # Extract app.tar or copy app folder
    app_tar = os.path.join(INPUT_DIR, 'app.tar')
    if os.path.exists(app_tar):
        print(f"📦 Extracting {app_tar}...")
        import tarfile
        with tarfile.open(app_tar, 'r') as tar:
            tar.extractall(path=WORKING_DIR)
        print("✅ Extracted 'app' package")
    elif os.path.exists(os.path.join(INPUT_DIR, 'app')):
        if os.path.exists(os.path.join(WORKING_DIR, 'app')):
            shutil.rmtree(os.path.join(WORKING_DIR, 'app'))
        shutil.copytree(os.path.join(INPUT_DIR, 'app'), os.path.join(WORKING_DIR, 'app'))
        print("✅ Copied 'app' folder to working directory")

    # Add working dir to path
    sys.path.append(WORKING_DIR)
    print(f"✅ Added {WORKING_DIR} to sys.path")
else:
    print(f"❌ CRITICAL: Could not find dataset at {INPUT_DIR}")
    # Fallback to current directory for local testing
    sys.path.append(os.getcwd())
            
# Import modules after setup
try:
    from app.processing.rembg_processor import process_image, initialize_processor
    from app.storage.local_storage import LocalStorage
    from app.utils.filename_parser import parse_filename
    from app.services.excel_service import ExcelPartsService
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Files in working dir:", os.listdir('/kaggle/working'))
    if os.path.exists('/kaggle/working/app'):
         print("Files in app:", os.listdir('/kaggle/working/app'))
    raise e

print("🚀 Enhanced REMBG Daily Processor starting...")
print("💰 Saving $6,900 vs PicWish API")
print("✅ Internet verification run")

# Configuration - Using Kaggle Secrets
try:
    user_secrets = UserSecretsClient()
    endpoint_secret = user_secrets.get_secret('R2_ENDPOINT')
    R2_ENDPOINT = endpoint_secret if endpoint_secret.startswith("http") else f"https://{endpoint_secret}"
    R2_ACCESS_KEY = user_secrets.get_secret('R2_ACCESS_KEY')
    R2_SECRET_KEY = user_secrets.get_secret('R2_SECRET_KEY')
    R2_BUCKET = user_secrets.get_secret('R2_BUCKET')
    # Optional webhook
    try:
        RENDER_WEBHOOK = user_secrets.get_secret('RENDER_WEBHOOK')
    except:
        RENDER_WEBHOOK = None
        
    print("✅ Secrets loaded successfully")
except Exception as e:
    print(f"❌ Failed to load secrets: {e}")
    print("Make sure you have added R2_ENDPOINT (no https://), R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET to Kaggle Secrets")
    raise e

# Check internet connectivity
def check_connection():
    import socket
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        print("✅ Internet access confirmd")
    except OSError:
        print("❌ No internet access. Please enable 'Internet' in Kaggle Notebook settings.")
        print("   Settings -> Internet -> On")
        sys.exit(1)

check_connection()

# Initialize R2 client
r2 = boto3.client('s3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

def download_daily_images(job_id):
    """Download today's raw images from R2."""
    print(f"📥 Downloading images for job: {job_id}")

    raw_images = []

    try:
        # Determine prefix based on job type
        if job_id.isdigit():
            # It's a symbol number in the raw folder
            prefix = f'raw/{job_id}/'
            print(f"   Targeting specific symbol folder: {prefix}")
        elif job_id.startswith("job_"):
            # Standard job folder
            prefix = f'raw_images/{job_id}/'
        else:
            # Fallback
            prefix = f'raw_images/{job_id}/'

        # List all images for today's job
        response = r2.list_objects_v2(
            Bucket=R2_BUCKET,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            print(f"⚠️ No files found in {prefix}")
            return []

        for obj in response.get('Contents', []):
            key = obj['Key']
            # print(f"  📄 Found: {key}") 

            # Download image
            image_data = r2.get_object(Bucket=R2_BUCKET, Key=key)['Body'].read()

            # Extract filename and symbol number from path robustly
            path_parts = list(Path(key).parts)
            filename = path_parts[-1]
            
            # Default symbol number to job_id if not found in path
            symbol_number = job_id
            
            # If we have enough parts, try to extract symbol number from path
            # Structure: raw/symbol_number/filename OR raw_images/job_id/symbol_number/filename
            if len(path_parts) >= 3:
                # If it's raw/job_id/filename, path_parts[1] is job_id
                # If it's raw_images/job_id/symbol_id/filename, path_parts[2] is symbol_id
                if path_parts[0] == 'raw':
                    symbol_number = path_parts[1]
                else:
                    symbol_number = path_parts[2]

            raw_images.append({
                'bytes': image_data,
                'filename': filename,
                'symbol_number': symbol_number,
                'original_key': key
            })

        print(f"✅ Downloaded {len(raw_images)} images")
        return raw_images

    except Exception as e:
        print(f"❌ Error downloading images: {e}")
        return []

def process_daily_batch(job_id, image_data_list):
    """Process images with Enhanced REMBG."""
    print(f"🎨 Processing {len(image_data_list)} images...")

    # Initialize Enhanced REMBG
    print("🔧 Initializing Enhanced REMBG...")
    initialize_processor()

    # Create local storage instance
    local_storage = LocalStorage(
        upload_dir="/kaggle/working/uploads",
        processed_dir="/kaggle/working/processed"
    )

    processed_files = []
    successful = 0
    failed = 0

    # Load Excel metadata
    excel_service = ExcelPartsService()
    excel_path = "egtl.xlsx"
    if os.path.exists(excel_path):
        print(f"📂 Loading Excel metadata from {excel_path}...")
        excel_service.load_excel_file(excel_path, sheet_name="DATA")
        print(f"✅ Loaded {excel_service.total_parts} parts from catalog")
    else:
        print(f"⚠️ Metadata file egtl.xlsx not found at {os.path.abspath(excel_path)}")

    start_time = time.time()

    for i, image_data in enumerate(image_data_list):
        try:
            # print(f"  🖼️  Processing {i+1}/{len(image_data_list)}: {image_data['filename']}")

            # Get metadata from Excel catalog
            parsed = parse_filename(image_data['filename'])
            symbol_number = parsed.symbol_number if parsed.is_valid else image_data.get('symbol_number')
            
            part_info = excel_service.get_part_info(symbol_number) if symbol_number else None
            
            # Extract fields for labeling
            desc1 = ""
            desc2 = ""
            part_no = ""
            mfg = ""
            long_desc = ""
            
            if part_info:
                desc1 = part_info.get('description_1', '')
                desc2 = part_info.get('description_2', '')
                part_no = part_info.get('part_number', '')
                mfg = part_info.get('manufacturer', '')
                long_desc = part_info.get('long_text_jde', '')

            # Process with Enhanced REMBG CPU + Metadata Layout
            processed_buffer = process_image(
                image_data['bytes'],
                output_format="JPEG",
                white_background=True,
                optimization_level="cost",  # CPU optimized
                compression_quality=85,
                symbol_number=symbol_number,
                desc1=desc1,
                desc2=desc2,
                part_number=part_no,
                manufacturer=mfg,
                long_description=long_desc,
                use_ecommerce_layout=True
            )

            # Parse filename for symbol number
            parsed = parse_filename(image_data['filename'])
            symbol_number = parsed.symbol_number if parsed.is_valid else image_data.get('symbol_number')

            # Save with EXACT same folder structure
            original_name = image_data['filename'].rsplit('.', 1)[0]
            processed_filename = f"{original_name}.jpg"

            # This maintains job_id/symbol_number/filename structure
            file_path = local_storage.save_processed(
                processed_buffer.read(),
                processed_filename,
                job_id,
                symbol_number=symbol_number
            )

            processed_files.append(file_path)
            successful += 1

            # Show progress
            if i % 10 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / (i + 1)
                remaining = avg_time * (len(image_data_list) - i - 1)
                print(f"    📊 Progress: {i+1}/{len(image_data_list)} ({remaining/60:.1f}m remaining)")

        except Exception as e:
            print(f"    ❌ Failed: {image_data['filename']} - {str(e)}")
            failed += 1

    total_time = time.time() - start_time
    print(f"✅ Processing complete!")
    print(f"   💪 Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   ⏱️  Total time: {total_time/60:.1f} minutes")
    if len(image_data_list) > 0:
        print(f"   ⚡ Avg per image: {total_time/len(image_data_list):.1f}s")

    return processed_files

def upload_processed_to_r2(job_id, processed_files):
    """Upload processed images to R2 using the main branch path structure."""
    print(f"📤 Uploading {len(processed_files)} processed images...")

    base_path = Path("/kaggle/working/processed")
    uploaded = 0

    for file_path in processed_files:
        try:
            local_file_path = base_path / file_path

            if local_file_path.exists():
                # Extract symbol_number and filename for main branch structure
                # file_path is: job_id/symbol_number/filename.jpg
                parts = Path(file_path).parts
                if len(parts) >= 2:
                    symbol_number = parts[-2]
                    filename = parts[-1]
                    # Main branch structure: parts/{symbol_number}/{filename}
                    r2_key = f"parts/{symbol_number}/{filename}"
                else:
                    filename = parts[-1]
                    r2_key = f"parts/{job_id}/{filename}"

                # print(f"    📤 Uploading to: {r2_key}")
                with open(local_file_path, 'rb') as f:
                    r2.put_object(
                        Bucket=R2_BUCKET,
                        Key=r2_key,
                        Body=f.read(),
                        ContentType='image/jpeg'
                    )
                uploaded += 1

                if uploaded % 50 == 0:
                    print(f"    📤 Uploaded: {uploaded}/{len(processed_files)}")
        except Exception as e:
            print(f"    ❌ Upload failed: {file_path} - {e}")

    print(f"✅ Upload complete: {uploaded}/{len(processed_files)} files to main branch paths")

def create_zip_in_r2(job_id):
    """Create ZIP file with same structure."""
    print("📦 Creating ZIP file...")

    local_storage = LocalStorage(processed_dir="/kaggle/working/processed")

    # Get all processed files for this job
    processed_files = []
    job_dir = Path(f"/kaggle/working/processed/{job_id}")

    if job_dir.exists():
        for file_path in job_dir.rglob("*.png"):
            relative_path = file_path.relative_to(job_dir.parent)
            processed_files.append(str(relative_path))

    if processed_files:
        # Create ZIP with preserved folder structure
        zip_path = local_storage.create_zip(
            processed_files,
            f"processed_{job_id}.zip",
            job_id,
            preserve_structure=True  # Keeps symbol_number folders
        )

        # Upload ZIP to R2
        with open(zip_path, 'rb') as f:
            r2.put_object(
                Bucket=R2_BUCKET,
                Key=f"processed_images/{job_id}/processed_{job_id}.zip",
                Body=f.read()
            )

        print(f"✅ ZIP created and uploaded: processed_{job_id}.zip")
    else:
        print("❌ No files to ZIP")

def notify_render_completion(job_id):
    """Notify Render that processing is complete."""
    if not RENDER_WEBHOOK:
        print("ℹ️ No RENDER_WEBHOOK secret set, skipping notification")
        return

    import requests

    try:
        response = requests.post(
            RENDER_WEBHOOK,
            json={'job_id': job_id, 'status': 'completed'},
            timeout=30
        )

        if response.status_code == 200:
            print(f"✅ Notified Render: Job {job_id} complete")
        else:
            print(f"⚠️ Render notification failed: {response.status_code}")

    except Exception as e:
        print(f"⚠️ Failed to notify Render: {e}")

# MAIN PROCESSING FUNCTION
def process_daily_job(job_id):
    """Complete daily processing pipeline."""

    print("="*60)
    print(f"🚀 ENHANCED REMBG DAILY PROCESSING")
    print(f"💼 Job ID: {job_id}")
    print(f"💰 Saving $6,900 vs PicWish API")
    print("="*60)

    try:
        # Step 1: Download raw images
        image_data_list = download_daily_images(job_id)

        if not image_data_list:
            print("❌ No images found for processing")
            return

        # Step 2: Process with Enhanced REMBG
        processed_files = process_daily_batch(job_id, image_data_list)

        if not processed_files:
            print("❌ No images processed successfully")
            return

        # Step 3: Upload processed images
        upload_processed_to_r2(job_id, processed_files)

        # Step 4: Notify Render (Skip ZIP per user request)
        notify_render_completion(job_id)

        print("="*60)
        print("🎉 DAILY PROCESSING COMPLETE!")
        print(f"📊 Processed: {len(processed_files)} images")
        print("="*60)

    except Exception as e:
        print(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()

# USAGE EXAMPLE
if __name__ == "__main__":
    # You can pass the job_id as an environment variable or argument if needed
    # Default to today's date based ID
    today_job = "84130406" # Real Test Data
    
    # Check for environment variable override
    if "JOB_ID" in os.environ:
        today_job = os.environ["JOB_ID"]
        print(f"Using JOB_ID from environment: {today_job}")

    process_daily_job(today_job)
