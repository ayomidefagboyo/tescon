"""
Kaggle auto-trigger service that runs as background task in Render.
"""

import os
import json
import asyncio
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from app.services.cloudflare_r2 import get_r2_storage
from app.services.github_actions_service import get_github_actions_service
from app.logging import setup_logger

logger = setup_logger("kaggle_trigger")

class KaggleTriggerService:
    """Service to automatically trigger Kaggle processing."""

    def __init__(self):
        self.r2_storage = get_r2_storage()
        self.kaggle_cli = os.getenv('KAGGLE_CLI_PATH', '/usr/local/bin/kaggle')
        self.notebook_username = os.getenv('KAGGLE_USERNAME', 'ayomidefagboyo')
        self.notebook_slug = os.getenv('KAGGLE_NOTEBOOK_SLUG', 'daily-enhanced-rembg-processor')

        # GitHub Actions service
        self.github_actions = get_github_actions_service()
        
        # Processing strategy: 'github_actions', 'kaggle', or 'both'
        self.processing_strategy = os.getenv('PROCESSING_STRATEGY', 'github_actions')

        # Track processed jobs
        self.processed_jobs = set()
        self.running = False

        # Auto-trigger settings
        self.check_interval = int(os.getenv('KAGGLE_CHECK_INTERVAL', '300'))  # 5 minutes
        self.job_age_threshold = int(os.getenv('KAGGLE_JOB_AGE_THRESHOLD', '120'))  # 2 minutes
        self.enabled = os.getenv('KAGGLE_AUTO_TRIGGER_ENABLED', 'false').lower() == 'true'

        logger.info(f"Trigger service initialized (enabled: {self.enabled}, strategy: {self.processing_strategy})")

    def is_kaggle_available(self) -> bool:
        """Check if Kaggle CLI is available and authenticated."""
        try:
            if not Path(self.kaggle_cli).exists():
                logger.error(f"Kaggle CLI not found at {self.kaggle_cli}")
                return False

            # Test authentication
            result = subprocess.run([self.kaggle_cli, 'datasets', 'list', '--max-size', '1'],
                                  capture_output=True, text=True, timeout=10)

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Kaggle availability check failed: {e}")
            return False

    async def check_for_new_jobs(self) -> List[Dict[str, Any]]:
        """Check R2 for jobs ready for processing."""
        try:
            if not self.r2_storage:
                return []

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

                    # Check job age
                    job_age = (datetime.now() - obj['LastModified'].replace(tzinfo=None)).total_seconds()

                    if job_age > self.job_age_threshold:
                        try:
                            # Get job data
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
                            logger.error(f"Error reading job {job_id}: {e}")

            return new_jobs

        except Exception as e:
            logger.error(f"Error checking for new jobs: {e}")
            return []

    def generate_notebook_code(self, job_id: str) -> tuple[str, str]:
        """Generate Kaggle notebook metadata and code for job."""

        metadata = {
            "id": f"{self.notebook_username}/{self.notebook_slug}",
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
        }

        # Render webhook for completion notification
        render_webhook = os.getenv('RENDER_WEBHOOK_URL', '')

        code = f'''# Enhanced REMBG Auto Processing - Job {job_id}
# Triggered: {datetime.now().isoformat()}

!pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
!pip install rembg opencv-python-headless pillow boto3

import os
import sys
import boto3
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from PIL import Image
from io import BytesIO
from rembg import remove, new_session
from kaggle_secrets import UserSecretsClient

# Get R2 credentials from Kaggle secrets
user_secrets = UserSecretsClient()

try:
    R2_ENDPOINT = f"https://{{user_secrets.get_secret('R2_ENDPOINT')}}"
    R2_ACCESS_KEY = user_secrets.get_secret('R2_ACCESS_KEY')
    R2_SECRET_KEY = user_secrets.get_secret('R2_SECRET_KEY')
    R2_BUCKET = user_secrets.get_secret('R2_BUCKET')
    print("✅ R2 credentials loaded")
except Exception as e:
    print(f"❌ Error loading secrets: {{e}}")
    sys.exit(1)

# Initialize R2
r2 = boto3.client('s3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

JOB_ID = "{job_id}"
RENDER_WEBHOOK = "{render_webhook}"

print(f"🚀 Auto-Processing Job: {{JOB_ID}}")

def download_and_process():
    try:
        # Download job metadata
        job_response = r2.get_object(Bucket=R2_BUCKET, Key=f"jobs/queued/{{JOB_ID}}.json")
        job_data = json.loads(job_response['Body'].read().decode('utf-8'))

        print(f"📋 Job loaded: {{job_data.get('symbol_number')}} ({{len(job_data.get('raw_file_paths', []))}}) files)")

        # Initialize rembg
        session = new_session("isnet-general-use")
        print("🔧 REMBG initialized")

        processed_files = []
        symbol_number = job_data.get('symbol_number')
        params = job_data.get('parameters', {{}})

        # Process each image
        for i, file_info in enumerate(job_data.get('raw_file_paths', [])):
            try:
                r2_key = file_info.get('r2_key')
                filename = file_info.get('filename')

                print(f"  📷 Processing {{i+1}}: {{filename}}")

                # Download image
                img_response = r2.get_object(Bucket=R2_BUCKET, Key=r2_key)
                img_bytes = img_response['Body'].read()

                # Remove background
                output_bytes = remove(img_bytes, session=session)

                # Load and add white background
                img = Image.open(BytesIO(output_bytes))
                if params.get('white_background', True) and img.mode in ('RGBA', 'LA'):
                    white_bg = Image.new('RGB', img.size, (255, 255, 255))
                    white_bg.paste(img, mask=img.split()[-1])
                    img = white_bg

                # Save as PNG
                output_buffer = BytesIO()
                img.save(output_buffer, format='PNG', optimize=True)
                processed_bytes = output_buffer.getvalue()

                # Upload processed image
                output_filename = filename.rsplit('.', 1)[0] + '.png'
                output_key = f"processed_images/{{JOB_ID}}/{{symbol_number}}/{{output_filename}}"

                r2.put_object(
                    Bucket=R2_BUCKET,
                    Key=output_key,
                    Body=processed_bytes,
                    ContentType='image/png'
                )

                processed_files.append({{
                    'filename': output_filename,
                    'key': output_key
                }})

                print(f"    ✅ {{output_filename}}")

            except Exception as e:
                print(f"    ❌ Failed: {{e}}")

        # Create ZIP
        print("📦 Creating ZIP...")
        import zipfile
        zip_path = f"/kaggle/working/processed_{{JOB_ID}}.zip"

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for pf in processed_files:
                # Download processed file and add to ZIP
                response = r2.get_object(Bucket=R2_BUCKET, Key=pf['key'])
                file_data = response['Body'].read()
                zipf.writestr(f"{{symbol_number}}/{{pf['filename']}}", file_data)

        # Upload ZIP
        with open(zip_path, 'rb') as f:
            r2.put_object(
                Bucket=R2_BUCKET,
                Key=f"processed_images/{{JOB_ID}}/processed_{{JOB_ID}}.zip",
                Body=f.read(),
                ContentType='application/zip'
            )

        # Mark job complete
        job_data['status'] = 'completed'
        job_data['completed_at'] = datetime.now().isoformat()
        job_data['processed_files_count'] = len(processed_files)
        job_data['processing_method'] = 'auto_kaggle'

        # Move to completed
        r2.put_object(
            Bucket=R2_BUCKET,
            Key=f"jobs/completed/{{JOB_ID}}.json",
            Body=json.dumps(job_data, indent=2),
            ContentType='application/json'
        )

        # Delete from queue
        r2.delete_object(Bucket=R2_BUCKET, Key=f"jobs/queued/{{JOB_ID}}.json")

        # Notify Render
        if RENDER_WEBHOOK:
            try:
                requests.post(RENDER_WEBHOOK,
                    json={{'job_id': JOB_ID, 'status': 'completed', 'processor': 'auto_kaggle'}},
                    timeout=30)
                print("✅ Render notified")
            except:
                print("⚠️ Failed to notify Render")

        print(f"🎉 PROCESSING COMPLETE: {{len(processed_files)}} images")

    except Exception as e:
        print(f"❌ Processing failed: {{e}}")
        import traceback
        traceback.print_exc()

# Run processing
download_and_process()'''

        return json.dumps(metadata, indent=2), code

    async def trigger_job(self, job_id: str) -> bool:
        """
        Trigger processing for a job using configured strategy.
        
        Strategy options:
        - 'github_actions': Try GitHub Actions only
        - 'kaggle': Try Kaggle only  
        - 'both': Try GitHub Actions first, fallback to Kaggle
        
        Args:
            job_id: Job ID to process
            
        Returns:
            True if triggered successfully
        """
        logger.info(f"Triggering job {job_id} with strategy: {self.processing_strategy}")
        
        # Try GitHub Actions
        if self.processing_strategy in ['github_actions', 'both']:
            if self.github_actions.enabled:
                try:
                    run_id = await self.github_actions.trigger_workflow(job_id)
                    if run_id:
                        logger.info(f"✅ GitHub Actions triggered for job {job_id} (run: {run_id})")
                        self.processed_jobs.add(job_id)
                        return True
                    else:
                        logger.warning(f"GitHub Actions trigger failed for job {job_id}")
                except Exception as e:
                    logger.error(f"GitHub Actions error for job {job_id}: {e}")
            else:
                logger.warning("GitHub Actions not configured")
        
        # Fallback to Kaggle or if Kaggle-only strategy
        if self.processing_strategy in ['kaggle', 'both']:
            logger.info(f"Attempting Kaggle fallback for job {job_id}")
            return await self.trigger_kaggle_job(job_id)
        
        logger.error(f"All processing methods failed for job {job_id}")
        return False

    async def trigger_kaggle_job(self, job_id: str) -> bool:
        """Trigger Kaggle processing for a specific job."""
        try:
            logger.info(f"Triggering Kaggle processing for job: {job_id}")

            # Check if Kaggle is available
            if not self.is_kaggle_available():
                logger.error("Kaggle CLI not available")
                return False

            # Generate notebook files
            metadata, code = self.generate_notebook_code(job_id)

            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Write files
                (temp_path / "kernel-metadata.json").write_text(metadata)
                (temp_path / "enhanced_rembg_processor.py").write_text(code)

                # Push to Kaggle
                result = subprocess.run([
                    self.kaggle_cli, 'kernels', 'push',
                    '--path', str(temp_path)
                ], capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    logger.info(f"Successfully triggered Kaggle for job: {job_id}")
                    self.processed_jobs.add(job_id)
                    return True
                else:
                    logger.error(f"Kaggle push failed: {result.stderr}")
                    return False

        except Exception as e:
            logger.error(f"Error triggering Kaggle job {job_id}: {e}")
            return False

    async def run_background_service(self):
        """Main background service loop."""
        if not self.enabled:
            logger.info("Kaggle auto-trigger service disabled")
            return

        logger.info("Starting Kaggle auto-trigger service")
        self.running = True

        while self.running:
            try:
                # Check for new jobs
                new_jobs = await self.check_for_new_jobs()

                if new_jobs:
                    logger.info(f"Found {len(new_jobs)} jobs ready for processing")

                    for job in new_jobs:
                        if not self.running:
                            break

                        job_id = job['job_id']
                        success = await self.trigger_job(job_id)

                        if success:
                            logger.info(f"Job {job_id} triggered successfully")
                        else:
                            logger.error(f"Failed to trigger job {job_id}")

                        # Wait between jobs
                        await asyncio.sleep(30)

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in background service: {e}")
                await asyncio.sleep(60)  # Wait before retry

    def stop(self):
        """Stop the background service."""
        logger.info("Stopping Kaggle auto-trigger service")
        self.running = False

# Global service instance
_kaggle_service = None

def get_kaggle_service() -> KaggleTriggerService:
    """Get the global Kaggle trigger service instance."""
    global _kaggle_service
    if _kaggle_service is None:
        _kaggle_service = KaggleTriggerService()
    return _kaggle_service

async def start_kaggle_service():
    """Start the Kaggle trigger background service."""
    service = get_kaggle_service()
    await service.run_background_service()

def stop_kaggle_service():
    """Stop the Kaggle trigger service."""
    global _kaggle_service
    if _kaggle_service:
        _kaggle_service.stop()