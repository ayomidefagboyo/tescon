# Enhanced REMBG Daily Batch Processor for Kaggle
# This replaces PicWish API with $6,900 savings

# Install dependencies
!pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
!pip install rembg opencv-python-headless pillow boto3

import os
import sys
import boto3
import zipfile
from pathlib import Path
from datetime import datetime
import time

# Add current directory to Python path
sys.path.append('/kaggle/working')

# Import your Enhanced REMBG modules (uploaded to Kaggle)
from app.processing.rembg_processor import process_image, initialize_processor
from app.storage.local_storage import LocalStorage
from app.utils.filename_parser import parse_filename

print("🚀 Enhanced REMBG Daily Processor")
print("💰 Saving $6,900 vs PicWish API")

# Configuration - SET THESE VALUES
R2_ENDPOINT = "YOUR_R2_ENDPOINT"
R2_ACCESS_KEY = "YOUR_R2_ACCESS_KEY"
R2_SECRET_KEY = "YOUR_R2_SECRET_KEY"
R2_BUCKET = "YOUR_R2_BUCKET_NAME"

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
        # List all images for today's job
        response = r2.list_objects_v2(
            Bucket=R2_BUCKET,
            Prefix=f'raw_images/{job_id}/'
        )

        for obj in response.get('Contents', []):
            key = obj['Key']
            print(f"  📄 Found: {key}")

            # Download image
            image_data = r2.get_object(Bucket=R2_BUCKET, Key=key)['Body'].read()

            # Extract filename and symbol number from path
            path_parts = Path(key).parts
            if len(path_parts) >= 3:  # raw_images/job_id/symbol_number/filename
                symbol_number = path_parts[2]
                filename = path_parts[3]

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

    start_time = time.time()

    for i, image_data in enumerate(image_data_list):
        try:
            print(f"  🖼️  Processing {i+1}/{len(image_data_list)}: {image_data['filename']}")

            # Process with Enhanced REMBG CPU
            processed_buffer = process_image(
                image_data['bytes'],
                output_format="PNG",
                white_background=True,
                optimization_level="cost"  # CPU optimized
            )

            # Parse filename for symbol number
            parsed = parse_filename(image_data['filename'])
            symbol_number = parsed.symbol_number if parsed.is_valid else image_data.get('symbol_number')

            # Save with EXACT same folder structure
            original_name = image_data['filename'].rsplit('.', 1)[0]
            processed_filename = f"{original_name}.png"

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
            if i % 50 == 0:
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
    print(f"   ⚡ Avg per image: {total_time/len(image_data_list):.1f}s")

    return processed_files

def upload_processed_to_r2(job_id, processed_files):
    """Upload processed images to R2."""
    print(f"📤 Uploading {len(processed_files)} processed images...")

    base_path = Path("/kaggle/working/processed")
    uploaded = 0

    for file_path in processed_files:
        try:
            local_file_path = base_path / file_path

            if local_file_path.exists():
                # Upload to R2 with same structure
                r2_key = f"processed_images/{file_path}"

                with open(local_file_path, 'rb') as f:
                    r2.put_object(
                        Bucket=R2_BUCKET,
                        Key=r2_key,
                        Body=f.read()
                    )
                uploaded += 1

                if uploaded % 100 == 0:
                    print(f"    📤 Uploaded: {uploaded}/{len(processed_files)}")
        except Exception as e:
            print(f"    ❌ Upload failed: {file_path} - {e}")

    print(f"✅ Upload complete: {uploaded}/{len(processed_files)} files")

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
    import requests

    try:
        # Replace with your Render app URL
        response = requests.post(
            'https://your-render-app.onrender.com/api/jobs/complete',
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

        # Step 4: Create ZIP file
        create_zip_in_r2(job_id)

        # Step 5: Notify Render
        notify_render_completion(job_id)

        print("="*60)
        print("🎉 DAILY PROCESSING COMPLETE!")
        print(f"📊 Processed: {len(processed_files)} images")
        print(f"💰 Cost: $0 (vs ~${len(image_data_list) * 0.10:.0f} with PicWish)")
        print("="*60)

    except Exception as e:
        print(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()

# USAGE EXAMPLE
if __name__ == "__main__":
    # Set today's job ID (format: job_YYYYMMDD_HHMMSS)
    today_job = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Or manually set specific job ID:
    # today_job = "job_20250125_143022"

    process_daily_job(today_job)
