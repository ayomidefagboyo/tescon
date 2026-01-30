#!/usr/bin/env python3
"""
Automatic Kaggle notebook triggering system.
Monitors R2 for new jobs and automatically triggers Kaggle processing.
"""

import os
import sys
import json
import time
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from services.cloudflare_r2 import get_r2_storage
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class KaggleAutoTrigger:
    def __init__(self):
        self.r2_storage = get_r2_storage()
        self.kaggle_cli = "/Users/admin/Library/Python/3.9/bin/kaggle"
        self.notebook_username = "ayomidefagboyo"
        self.notebook_slug = "daily-enhanced-rembg-processor"

        # Track processed jobs to avoid duplicates
        self.processed_jobs = set()
        self.running = True

        # Validate setup
        self._validate_setup()

    def _validate_setup(self):
        """Validate that all required components are available."""

        # Check R2 connection
        if not self.r2_storage:
            raise Exception("❌ R2 storage not configured")

        # Check Kaggle CLI
        if not Path(self.kaggle_cli).exists():
            raise Exception(f"❌ Kaggle CLI not found at {self.kaggle_cli}")

        # Test Kaggle authentication
        try:
            result = subprocess.run([self.kaggle_cli, 'datasets', 'list', '--max-size', '1'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise Exception("❌ Kaggle authentication failed")
        except Exception as e:
            raise Exception(f"❌ Kaggle CLI test failed: {e}")

        print("✅ Auto-trigger setup validated")

    def log(self, message, prefix="🤖"):
        """Log with timestamp."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {prefix} {message}")

    def check_for_new_jobs(self):
        """Check R2 for new jobs to process."""
        try:
            # List jobs in queue
            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix='jobs/queued/'
            )

            new_jobs = []

            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.json'):
                    job_id = Path(key).stem

                    # Skip if already processed
                    if job_id in self.processed_jobs:
                        continue

                    # Check job age (only process jobs older than 2 minutes to ensure all files uploaded)
                    job_age = (datetime.now() - obj['LastModified'].replace(tzinfo=None)).total_seconds()

                    if job_age > 120:  # 2 minutes
                        # Download and parse job data
                        try:
                            job_response = self.r2_storage.s3_client.get_object(
                                Bucket=self.r2_storage.bucket_name,
                                Key=key
                            )
                            job_data = json.loads(job_response['Body'].read().decode('utf-8'))

                            new_jobs.append({
                                'job_id': job_id,
                                'key': key,
                                'data': job_data,
                                'age_minutes': job_age / 60
                            })

                        except Exception as e:
                            self.log(f"❌ Error reading job {job_id}: {e}")

            return new_jobs

        except Exception as e:
            self.log(f"❌ Error checking for new jobs: {e}")
            return []

    def create_kaggle_notebook_update(self, job_id):
        """Create updated notebook with new job ID."""

        notebook_template = f'''{{
  "id": "{self.notebook_username}/{self.notebook_slug}",
  "title": "Daily Enhanced REMBG Processor",
  "code_file": "enhanced_rembg_processor.py",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": "true",
  "enable_gpu": "false",
  "enable_internet": "true",
  "enable_external_data_sources": "false",
  "dataset_sources": [],
  "competition_sources": [],
  "kernel_sources": [],
  "model_sources": []
}}'''

        notebook_code = f'''# Enhanced REMBG Daily Batch Processor - Auto-triggered
# Job ID: {job_id}
# Triggered at: {datetime.now().isoformat()}

# Install dependencies
!pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
!pip install rembg opencv-python-headless pillow boto3

import os
import sys
import boto3
import zipfile
import json
from pathlib import Path
from datetime import datetime
import time
import requests

# R2 Configuration from Kaggle secrets
from kaggle_secrets import UserSecretsClient

user_secrets = UserSecretsClient()

# Get R2 credentials
try:
    R2_ENDPOINT = f"https://{{user_secrets.get_secret('R2_ENDPOINT')}}"
    R2_ACCESS_KEY = user_secrets.get_secret('R2_ACCESS_KEY')
    R2_SECRET_KEY = user_secrets.get_secret('R2_SECRET_KEY')
    R2_BUCKET = user_secrets.get_secret('R2_BUCKET')
    RENDER_WEBHOOK = user_secrets.get_secret('RENDER_WEBHOOK')

    print("✅ R2 credentials loaded from secrets")
except Exception as e:
    print(f"❌ Error loading secrets: {{e}}")
    sys.exit(1)

# Initialize R2 client
r2 = boto3.client('s3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

print(f"🚀 Auto-triggered Enhanced REMBG Processing")
print(f"💼 Job ID: {job_id}")
print(f"💰 Saving money vs PicWish API!")
print("=" * 60)

def download_job_images(job_id):
    """Download images for the specified job."""
    print(f"📥 Downloading images for job: {{job_id}}")

    try:
        # Download job metadata
        job_response = r2.get_object(
            Bucket=R2_BUCKET,
            Key=f"jobs/queued/{{job_id}}.json"
        )
        job_data = json.loads(job_response['Body'].read().decode('utf-8'))

        print(f"📋 Job metadata loaded:")
        print(f"  🔖 Symbol: {{job_data.get('symbol_number', 'unknown')}}")
        print(f"  📁 Files: {{len(job_data.get('raw_file_paths', []))}}")

        # Download all raw images
        raw_images = []

        for file_info in job_data.get('raw_file_paths', []):
            r2_key = file_info.get('r2_key')
            filename = file_info.get('filename', 'unknown')

            print(f"  📷 Downloading: {{filename}}")

            try:
                image_response = r2.get_object(Bucket=R2_BUCKET, Key=r2_key)
                image_bytes = image_response['Body'].read()

                raw_images.append({{
                    'filename': filename,
                    'bytes': image_bytes,
                    'symbol_number': job_data.get('symbol_number'),
                    'r2_key': r2_key
                }})

            except Exception as e:
                print(f"    ❌ Failed to download {{filename}}: {{e}}")

        print(f"✅ Downloaded {{len(raw_images)}} images")
        return raw_images, job_data

    except Exception as e:
        print(f"❌ Error downloading job images: {{e}}")
        return [], {{}}

def process_with_rembg(raw_images, job_data):
    """Process images with rembg."""

    print(f"🎨 Processing {{len(raw_images)}} images with Enhanced REMBG...")

    from rembg import remove, new_session
    from PIL import Image
    from io import BytesIO

    # Initialize rembg
    print("🔧 Initializing rembg...")
    session = new_session("isnet-general-use")  # CPU-optimized model

    processed_files = []
    successful = 0

    # Get job parameters
    params = job_data.get('parameters', {{}})
    symbol_number = job_data.get('symbol_number', 'unknown')

    start_time = time.time()

    for i, img_data in enumerate(raw_images):
        try:
            print(f"  🖼️ Processing {{i+1}}/{{len(raw_images)}}: {{img_data['filename']}}")

            # Remove background
            output_bytes = remove(img_data['bytes'], session=session)

            # Load and process
            processed_image = Image.open(BytesIO(output_bytes))

            # Add white background if requested
            if params.get('white_background', True):
                if processed_image.mode in ('RGBA', 'LA'):
                    # Create white background
                    white_bg = Image.new('RGB', processed_image.size, (255, 255, 255))
                    white_bg.paste(processed_image, mask=processed_image.split()[-1])
                    processed_image = white_bg

            # Save as PNG
            output_buffer = BytesIO()
            processed_image.save(output_buffer, format='PNG', optimize=True)
            processed_bytes = output_buffer.getvalue()

            # Generate output filename
            original_name = img_data['filename'].rsplit('.', 1)[0]
            processed_filename = f"{{original_name}}.png"

            processed_files.append({{
                'filename': processed_filename,
                'bytes': processed_bytes,
                'symbol_number': symbol_number,
                'view_number': i + 1
            }})

            successful += 1

        except Exception as e:
            print(f"    ❌ Failed to process {{img_data['filename']}}: {{e}}")

    total_time = time.time() - start_time
    print(f"✅ Processing complete!")
    print(f"  💪 Successful: {{successful}}/{{len(raw_images)}}")
    print(f"  ⏱️ Total time: {{total_time/60:.1f}} minutes")
    print(f"  ⚡ Avg per image: {{total_time/len(raw_images):.1f}}s")

    return processed_files

def upload_processed_images(job_id, processed_files):
    """Upload processed images to R2."""

    print(f"📤 Uploading {{len(processed_files)}} processed files...")

    uploaded_files = []

    for file_data in processed_files:
        try:
            # Upload to processed_images folder
            r2_key = f"processed_images/{{job_id}}/{{file_data['symbol_number']}}/{{file_data['filename']}}"

            r2.put_object(
                Bucket=R2_BUCKET,
                Key=r2_key,
                Body=file_data['bytes'],
                ContentType='image/png'
            )

            uploaded_files.append(r2_key)

        except Exception as e:
            print(f"❌ Upload failed for {{file_data['filename']}}: {{e}}")

    print(f"✅ Upload complete: {{len(uploaded_files)}} files")
    return uploaded_files

def create_zip_file(job_id, processed_files):
    """Create ZIP file with processed images."""

    print("📦 Creating ZIP file...")

    zip_filename = f"processed_{{job_id}}.zip"
    zip_path = f"/kaggle/working/{{zip_filename}}"

    # Create ZIP
    import zipfile
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_data in processed_files:
            # Preserve folder structure: symbol_number/filename
            zip_internal_path = f"{{file_data['symbol_number']}}/{{file_data['filename']}}"

            zipf.writestr(zip_internal_path, file_data['bytes'])

    # Upload ZIP to R2
    with open(zip_path, 'rb') as f:
        r2.put_object(
            Bucket=R2_BUCKET,
            Key=f"processed_images/{{job_id}}/{{zip_filename}}",
            Body=f.read(),
            ContentType='application/zip'
        )

    print(f"✅ ZIP created and uploaded: {{zip_filename}}")

def mark_job_complete(job_id, processed_count):
    """Mark job as completed."""

    print("📋 Marking job as completed...")

    try:
        # Get original job data
        job_response = r2.get_object(
            Bucket=R2_BUCKET,
            Key=f"jobs/queued/{{job_id}}.json"
        )
        job_data = json.loads(job_response['Body'].read().decode('utf-8'))

        # Update job data
        job_data['status'] = 'completed'
        job_data['completed_at'] = datetime.now().isoformat()
        job_data['processed_files_count'] = processed_count
        job_data['processing_method'] = 'auto_kaggle'

        # Upload to completed folder
        r2.put_object(
            Bucket=R2_BUCKET,
            Key=f"jobs/completed/{{job_id}}.json",
            Body=json.dumps(job_data, indent=2),
            ContentType='application/json'
        )

        # Delete from queued folder
        r2.delete_object(
            Bucket=R2_BUCKET,
            Key=f"jobs/queued/{{job_id}}.json"
        )

        print("✅ Job marked as completed")

    except Exception as e:
        print(f"❌ Error marking job complete: {{e}}")

def notify_render(job_id):
    """Notify Render that processing is complete."""

    try:
        if RENDER_WEBHOOK:
            response = requests.post(
                RENDER_WEBHOOK,
                json={{'job_id': job_id, 'status': 'completed', 'processor': 'auto_kaggle'}},
                timeout=30
            )

            if response.status_code == 200:
                print("✅ Render notified successfully")
            else:
                print(f"⚠️ Render notification failed: {{response.status_code}}")
        else:
            print("⚠️ No webhook URL configured")

    except Exception as e:
        print(f"⚠️ Failed to notify Render: {{e}}")

# MAIN PROCESSING
def main():
    try:
        # Step 1: Download images
        raw_images, job_data = download_job_images("{job_id}")

        if not raw_images:
            print("❌ No images to process")
            return

        # Step 2: Process with rembg
        processed_files = process_with_rembg(raw_images, job_data)

        if not processed_files:
            print("❌ No images processed successfully")
            return

        # Step 3: Upload processed images
        uploaded_files = upload_processed_images("{job_id}", processed_files)

        # Step 4: Create ZIP
        create_zip_file("{job_id}", processed_files)

        # Step 5: Mark complete
        mark_job_complete("{job_id}", len(processed_files))

        # Step 6: Notify Render
        notify_render("{job_id}")

        print("=" * 60)
        print("🎉 AUTO-PROCESSING COMPLETE!")
        print(f"📊 Processed: {{len(processed_files)}} images")
        print(f"💰 Cost: $0 (vs PicWish API)")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Processing failed: {{e}}")
        import traceback
        traceback.print_exc()

# Run main processing
main()'''

        return notebook_template, notebook_code

    def trigger_kaggle_processing(self, job_id):
        """Trigger Kaggle notebook processing for a specific job."""

        self.log(f"🚀 Triggering Kaggle processing for job: {job_id}")

        try:
            # Create temporary directory for notebook files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Generate notebook files
                metadata, code = self.create_kaggle_notebook_update(job_id)

                # Write metadata file
                metadata_file = temp_path / "kernel-metadata.json"
                with open(metadata_file, 'w') as f:
                    f.write(metadata)

                # Write code file
                code_file = temp_path / "enhanced_rembg_processor.py"
                with open(code_file, 'w') as f:
                    f.write(code)

                self.log("📝 Notebook files created")

                # Push to Kaggle
                self.log("📤 Pushing to Kaggle...")

                result = subprocess.run([
                    self.kaggle_cli, 'kernels', 'push',
                    '--path', str(temp_path),
                    '--timeout', '7200'  # 2 hours timeout
                ], capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    self.log("✅ Kaggle notebook triggered successfully!")
                    self.log(f"📊 Output: {result.stdout.strip()}")

                    # Mark as processed
                    self.processed_jobs.add(job_id)
                    return True

                else:
                    self.log(f"❌ Kaggle push failed: {result.stderr}")
                    return False

        except subprocess.TimeoutExpired:
            self.log("❌ Kaggle push timeout")
            return False
        except Exception as e:
            self.log(f"❌ Error triggering Kaggle: {e}")
            return False

    def run_auto_trigger(self, check_interval=300):  # 5 minutes
        """Main loop for automatic triggering."""

        self.log("🤖 Auto-trigger system started")
        self.log(f"⏰ Checking for new jobs every {check_interval/60:.0f} minutes")
        self.log("⏹️  Press Ctrl+C to stop")

        try:
            while self.running:
                # Check for new jobs
                new_jobs = self.check_for_new_jobs()

                if new_jobs:
                    self.log(f"🆕 Found {len(new_jobs)} jobs ready for processing")

                    for job in new_jobs:
                        job_id = job['job_id']
                        age_min = job['age_minutes']

                        self.log(f"📋 Job: {job_id} (age: {age_min:.1f}m)")

                        # Trigger processing
                        success = self.trigger_kaggle_processing(job_id)

                        if success:
                            self.log(f"✅ {job_id} triggered successfully")
                        else:
                            self.log(f"❌ {job_id} trigger failed")

                        # Wait between jobs to avoid rate limits
                        time.sleep(30)

                else:
                    self.log("💤 No new jobs found")

                # Wait for next check
                time.sleep(check_interval)

        except KeyboardInterrupt:
            self.log("⏹️ Auto-trigger stopped by user")
            self.running = False
        except Exception as e:
            self.log(f"❌ Auto-trigger error: {e}")

def main():
    """Main function."""

    print("🤖 KAGGLE AUTO-TRIGGER SYSTEM")
    print("=" * 50)

    try:
        trigger = KaggleAutoTrigger()

        # Check current status
        new_jobs = trigger.check_for_new_jobs()
        if new_jobs:
            print(f"🆕 Found {len(new_jobs)} jobs ready for processing")

            # Ask if user wants to process them now
            for job in new_jobs:
                job_id = job['job_id']
                age_min = job['age_minutes']

                process = input(f"Process job {job_id} now? (y/n): ").lower().startswith('y')
                if process:
                    trigger.trigger_kaggle_processing(job_id)

        # Ask about continuous monitoring
        auto_mode = input("\\nStart continuous auto-trigger mode? (y/n): ").lower().startswith('y')

        if auto_mode:
            # Get check interval
            interval_input = input("Check interval in minutes (5): ").strip()
            interval = int(interval_input) * 60 if interval_input else 300

            trigger.run_auto_trigger(interval)
        else:
            print("👋 Auto-trigger ready for manual use")

    except Exception as e:
        print(f"❌ Setup error: {e}")

if __name__ == "__main__":
    main()