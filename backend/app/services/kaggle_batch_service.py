"""
Improved Kaggle batch processing service.
Processes multiple jobs together and manages notebook lifecycle properly.
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
from app.logging import setup_logger

logger = setup_logger("kaggle_batch")

class KaggleBatchService:
    """Smart Kaggle batch processing service with multiple strategies."""

    def __init__(self):
        self.r2_storage = get_r2_storage()
        self.kaggle_cli = os.getenv('KAGGLE_CLI_PATH', '/usr/local/bin/kaggle')
        self.notebook_username = os.getenv('KAGGLE_USERNAME', 'ayomidefagboyo')
        self.notebook_slug = os.getenv('KAGGLE_NOTEBOOK_SLUG', 'daily-enhanced-rembg-processor')

        # Processing strategy configuration
        self.strategy = os.getenv('KAGGLE_STRATEGY', 'batch_hourly')  # 'batch_hourly', 'batch_daily', 'immediate'
        self.max_jobs_per_batch = int(os.getenv('KAGGLE_MAX_JOBS_PER_BATCH', '10'))
        self.batch_timeout_hours = int(os.getenv('KAGGLE_BATCH_TIMEOUT', '1'))

        # Timing configuration based on strategy
        if self.strategy == 'batch_daily':
            self.check_interval = 3600 * 24  # Check once daily
            self.process_at_hour = int(os.getenv('KAGGLE_DAILY_HOUR', '18'))  # 6 PM default
            self.job_age_threshold = 300  # 5 minutes minimum age for daily batch
        elif self.strategy == 'batch_hourly':
            self.check_interval = 3600  # Check every hour
            self.job_age_threshold = 1800  # 30 minutes
        else:  # immediate
            self.check_interval = 300  # 5 minutes
            self.job_age_threshold = 120  # 2 minutes

        self.enabled = os.getenv('KAGGLE_AUTO_TRIGGER_ENABLED', 'false').lower() == 'true'
        self.processed_jobs = set()
        self.running = False

        logger.info(f"Kaggle batch service initialized (strategy: {self.strategy}, enabled: {self.enabled})")

    async def get_jobs_ready_for_processing(self) -> List[Dict[str, Any]]:
        """Get jobs that are ready for batch processing."""
        try:
            if not self.r2_storage:
                logger.warning("R2 storage not configured")
                return []

            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix='jobs/queued/'
            )

            total_objects = len(response.get('Contents', []))
            logger.debug(f"Found {total_objects} objects in jobs/queued/")

            ready_jobs = []
            now = datetime.now()

            for obj in response.get('Contents', []):
                key = obj['Key']
                if not key.endswith('.json'):
                    continue

                job_id = Path(key).stem
                if job_id in self.processed_jobs:
                    continue

                # Check job age based on strategy
                job_age_seconds = (now - obj['LastModified'].replace(tzinfo=None)).total_seconds()

                logger.debug(f"Job {job_id}: age {job_age_seconds:.0f}s, threshold {self.job_age_threshold}s")

                if self.strategy == 'batch_daily':
                    # For daily batch, collect all jobs from the day
                    if job_age_seconds > 300:  # At least 5 minutes old
                        ready_jobs.append(self._get_job_data(key, job_id, job_age_seconds))

                elif self.strategy == 'batch_hourly':
                    # For hourly batch, collect jobs older than threshold
                    if job_age_seconds > self.job_age_threshold:
                        ready_jobs.append(self._get_job_data(key, job_id, job_age_seconds))

                else:  # immediate
                    if job_age_seconds > self.job_age_threshold:
                        ready_jobs.append(self._get_job_data(key, job_id, job_age_seconds))
                        logger.debug(f"Added job {job_id} to ready queue")
                        break  # Only process one job at a time for immediate mode
                    else:
                        logger.debug(f"Job {job_id} not ready yet (age: {job_age_seconds:.0f}s < threshold: {self.job_age_threshold}s)")

            # Limit batch size
            if len(ready_jobs) > self.max_jobs_per_batch:
                logger.info(f"Limiting batch to {self.max_jobs_per_batch} jobs (found {len(ready_jobs)})")
                ready_jobs = ready_jobs[:self.max_jobs_per_batch]

            return [job for job in ready_jobs if job is not None]

        except Exception as e:
            logger.error(f"Error getting ready jobs: {e}")
            return []

    def _get_job_data(self, key: str, job_id: str, age_seconds: float) -> Dict[str, Any]:
        """Get job data from R2."""
        try:
            job_response = self.r2_storage.s3_client.get_object(
                Bucket=self.r2_storage.bucket_name,
                Key=key
            )
            job_data = json.loads(job_response['Body'].read().decode('utf-8'))

            return {
                'job_id': job_id,
                'key': key,
                'data': job_data,
                'age_minutes': age_seconds / 60
            }
        except Exception as e:
            logger.error(f"Error reading job {job_id}: {e}")
            return None

    def generate_batch_notebook(self, jobs: List[Dict[str, Any]]) -> tuple[str, str]:
        """Generate notebook that processes multiple jobs in one execution."""

        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        job_ids = [job['job_id'] for job in jobs]

        metadata = {
            "id": f"{self.notebook_username}/{self.notebook_slug}",
            "title": "Daily Enhanced REMBG Processor",
            "code_file": "enhanced_rembg_batch_processor.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": "true",
            "enable_gpu": "false",
            "enable_tpu": "false",
            "enable_internet": "true",
            "dataset_sources": [],
            "competition_sources": [],
            "kernel_sources": [],
            "model_sources": []
        }

        render_webhook = os.getenv('RENDER_WEBHOOK_URL', '')

        # Get R2 credentials from environment
        r2_endpoint = os.getenv('CLOUDFLARE_ACCOUNT_ID', '')
        r2_access_key = os.getenv('CLOUDFLARE_ACCESS_KEY_ID', '')
        r2_secret_key = os.getenv('CLOUDFLARE_SECRET_ACCESS_KEY', '')
        r2_bucket = os.getenv('CLOUDFLARE_BUCKET_NAME', '')

        code = f'''# Enhanced REMBG Batch Processor
# Batch ID: {batch_id}
# Jobs: {len(jobs)}
# Triggered: {datetime.now().isoformat()}

# Optimize dependency installation - avoid re-downloading if already available
try:
    import torch
    print("✅ torch already available")
except ImportError:
    print("📦 Installing torch...")
    !pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

try:
    import rembg
    print("✅ rembg already available")
except ImportError:
    print("📦 Installing rembg...")
    !pip install rembg opencv-python-headless

# Always ensure boto3 is available (lightweight)
try:
    import boto3
except ImportError:
    !pip install boto3 pillow

import os
import sys
import boto3
import json
import time
import requests
import zipfile
from pathlib import Path
from datetime import datetime
from PIL import Image
from io import BytesIO
from rembg import remove, new_session
# from kaggle_secrets import UserSecretsClient  # No longer needed - using embedded credentials

print("🚀 Enhanced REMBG Batch Processor")
print(f"📦 Batch ID: {batch_id}")
print(f"📋 Processing {len(jobs)} jobs")
print("💰 Saving massive costs vs PicWish API!")
print("=" * 60)

# R2 credentials (embedded for reliability)
R2_ENDPOINT = "https://{r2_endpoint}.r2.cloudflarestorage.com"
R2_ACCESS_KEY = "{r2_access_key}"
R2_SECRET_KEY = "{r2_secret_key}"
R2_BUCKET = "{r2_bucket}"

print("✅ R2 credentials configured")
print(f"📡 Endpoint: {{R2_ENDPOINT}}")
print(f"🪣 Bucket: {{R2_BUCKET}}")

# Initialize R2 and REMBG
r2 = boto3.client('s3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

# Jobs to process
JOBS_TO_PROCESS = {job_ids}
RENDER_WEBHOOK = "{render_webhook}"

def process_job_batch():
    """Process all jobs in this batch."""

    # Initialize REMBG once for all jobs
    print("🔧 Initializing REMBG...")
    session = new_session("isnet-general-use")
    print("✅ REMBG session ready")

    total_jobs = len(JOBS_TO_PROCESS)
    completed_jobs = []
    failed_jobs = []

    batch_start_time = time.time()

    for job_idx, job_id in enumerate(JOBS_TO_PROCESS, 1):
        job_start_time = time.time()

        print(f"\\n📋 Job {{job_idx}}/{{total_jobs}}: {{job_id}}")
        print("-" * 50)

        try:
            # Download job metadata
            job_response = r2.get_object(Bucket=R2_BUCKET, Key=f"jobs/queued/{{job_id}}.json")
            job_data = json.loads(job_response['Body'].read().decode('utf-8'))

            symbol_number = job_data.get('symbol_number', 'unknown')
            raw_files = job_data.get('raw_file_paths', [])
            params = job_data.get('parameters', {{}})
            part_info = job_data.get('part_info', {{}})

            # Get desc1 from Excel catalog data included in job
            description = part_info.get('desc1') or part_info.get('description') or f"Part_{{symbol_number}}"

            print(f"🔖 Symbol: {{symbol_number}}")
            print(f"📁 Files: {{len(raw_files)}}")
            print(f"📝 Description: {{description}}")

            processed_files = []

            # Process each image in the job
            for file_idx, file_info in enumerate(raw_files, 1):
                try:
                    r2_key = file_info.get('r2_key')
                    filename = file_info.get('filename', 'unknown')

                    print(f"  📷 {{file_idx}}/{{len(raw_files)}}: {{filename}}")

                    # Download image
                    img_response = r2.get_object(Bucket=R2_BUCKET, Key=r2_key)
                    img_bytes = img_response['Body'].read()

                    # Remove background
                    output_bytes = remove(img_bytes, session=session)

                    # Load and process
                    img = Image.open(BytesIO(output_bytes))

                    # Add white background if requested
                    if params.get('white_background', True) and img.mode in ('RGBA', 'LA'):
                        white_bg = Image.new('RGB', img.size, (255, 255, 255))
                        white_bg.paste(img, mask=img.split()[-1])
                        img = white_bg

                    # Save as PNG
                    output_buffer = BytesIO()
                    img.save(output_buffer, format='PNG', optimize=True)
                    processed_bytes = output_buffer.getvalue()

                    # Generate filename: SymbolNumber_ViewNumber_Description.png
                    # Extract view number from filename or use index
                    view_num = file_idx
                    if '_' in filename:
                        parts = filename.split('_')
                        if len(parts) >= 2 and parts[1].isdigit():
                            view_num = int(parts[1])

                    # Use description from job processing (already sanitized above)
                    safe_description = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in description)
                    safe_description = safe_description.replace(' ', '_')[:50]  # Limit length

                    # Generate filename: SymbolNumber_ViewNumber_Description.png
                    output_filename = f"{{symbol_number}}_{{view_num}}_{{safe_description}}.png"
                    output_key = f"parts/{{symbol_number}}/{{output_filename}}"

                    # Upload processed image
                    r2.put_object(
                        Bucket=R2_BUCKET,
                        Key=output_key,
                        Body=processed_bytes,
                        ContentType='image/png'
                    )

                    processed_files.append({{
                        'filename': output_filename,
                        'key': output_key,
                        'bytes': processed_bytes
                    }})

                    print(f"    ✅ {{output_filename}}")

                except Exception as e:
                    print(f"    ❌ Failed: {{e}}")

            if processed_files:
                # Images already uploaded individually to R2 - no ZIP creation needed
                print(f"  ✅ All {{len(processed_files)}} images uploaded directly to R2")

                # Mark job complete
                job_data['status'] = 'completed'
                job_data['completed_at'] = datetime.now().isoformat()
                job_data['processed_files_count'] = len(processed_files)
                job_data['processing_method'] = 'kaggle_batch'
                job_data['batch_id'] = "{batch_id}"

                # Move to completed
                r2.put_object(
                    Bucket=R2_BUCKET,
                    Key=f"jobs/completed/{{job_id}}.json",
                    Body=json.dumps(job_data, indent=2),
                    ContentType='application/json'
                )

                # Delete from queue
                r2.delete_object(Bucket=R2_BUCKET, Key=f"jobs/queued/{{job_id}}.json")

                completed_jobs.append({{
                    'job_id': job_id,
                    'processed_files': len(processed_files),
                    'processing_time': time.time() - job_start_time
                }})

                job_time = time.time() - job_start_time
                print(f"  ✅ Job completed: {{len(processed_files)}} files in {{job_time:.1f}}s")

            else:
                print(f"  ❌ No files processed for job {{job_id}}")
                failed_jobs.append(job_id)

        except Exception as e:
            print(f"❌ Job {{job_id}} failed: {{e}}")
            failed_jobs.append(job_id)

    # Batch completion summary
    batch_time = time.time() - batch_start_time
    total_files = sum(job['processed_files'] for job in completed_jobs)

    print("\\n" + "=" * 60)
    print("🎉 BATCH PROCESSING COMPLETE!")
    print(f"📊 Completed jobs: {{len(completed_jobs)}}/{{total_jobs}}")
    print(f"📁 Total files processed: {{total_files}}")
    print(f"⏱️ Total batch time: {{batch_time/60:.1f}} minutes")
    print(f"⚡ Average per job: {{batch_time/len(completed_jobs) if completed_jobs else 0:.1f}}s")
    print(f"💰 Cost savings vs PicWish: ${{total_files * 0.10:.2f}}")
    print("=" * 60)

    # Notify Render about completed jobs
    if RENDER_WEBHOOK:
        try:
            for job in completed_jobs:
                requests.post(RENDER_WEBHOOK,
                    json={{
                        'job_id': job['job_id'],
                        'status': 'completed',
                        'processor': 'kaggle_batch',
                        'batch_id': "{batch_id}",
                        'files_processed': job['processed_files']
                    }},
                    timeout=30)
            print(f"✅ Notified Render about {{len(completed_jobs)}} completed jobs")
        except Exception as e:
            print(f"⚠️ Failed to notify Render: {{e}}")

    return completed_jobs, failed_jobs

# Run batch processing
try:
    completed, failed = process_job_batch()

    if failed:
        print(f"\\n⚠️ Failed jobs: {{failed}}")

    print(f"\\n🎯 Batch {batch_id} finished successfully!")

except Exception as e:
    print(f"❌ Batch processing failed: {{e}}")
    import traceback
    traceback.print_exc()
'''

        return json.dumps(metadata, indent=2), code

    def create_notebook_from_code(self, python_code: str) -> str:
        """Convert Python code to Jupyter notebook format."""
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": python_code.split('\n')
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                },
                "language_info": {
                    "name": "python",
                    "version": "3.8.5"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4
        }
        return json.dumps(notebook, indent=2)

    async def trigger_batch_processing(self, jobs: List[Dict[str, Any]]) -> bool:
        """Trigger Kaggle processing for a batch of jobs."""
        if not jobs:
            return False

        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Triggering batch processing: {batch_id} ({len(jobs)} jobs)")

        try:
            # Generate batch notebook
            metadata, code = self.generate_batch_notebook(jobs)

            # Create temporary directory and push to Kaggle
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                (temp_path / "kernel-metadata.json").write_text(metadata)
                notebook = self.create_notebook_from_code(code)
                (temp_path / "enhanced_rembg_batch_processor.ipynb").write_text(notebook)

                result = subprocess.run([
                    self.kaggle_cli, 'kernels', 'push',
                    '--path', str(temp_path)
                ], capture_output=True, text=True, timeout=120)

                if result.returncode == 0:
                    # Mark all jobs as processed
                    for job in jobs:
                        self.processed_jobs.add(job['job_id'])

                    logger.info(f"Batch {batch_id} triggered successfully ({len(jobs)} jobs)")
                    return True
                else:
                    logger.error(f"Batch trigger failed:")
                    logger.error(f"Return code: {result.returncode}")
                    logger.error(f"STDOUT: {result.stdout}")
                    logger.error(f"STDERR: {result.stderr}")
                    return False

        except Exception as e:
            logger.error(f"Error triggering batch {batch_id}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    async def cleanup_old_notebooks(self):
        """Clean up old notebook versions (optional)."""
        # Note: Kaggle API doesn't provide direct notebook deletion
        # But newer pushes to the same notebook overwrite the previous version
        # So we only keep the latest version automatically
        logger.info("Notebook cleanup: Latest version automatically maintained")

    def should_process_now(self) -> bool:
        """Determine if it's time to process based on strategy."""
        now = datetime.now()

        if self.strategy == 'batch_daily':
            # Only process at specific hour
            return now.hour == self.process_at_hour and now.minute < 10
        elif self.strategy == 'batch_hourly':
            # Process at the top of every hour
            return now.minute < 10
        else:  # immediate
            return True

    async def run_batch_service(self):
        """Main batch service loop."""
        if not self.enabled:
            logger.info("Kaggle batch service disabled")
            return

        logger.info(f"Starting Kaggle batch service (strategy: {self.strategy})")
        self.running = True

        while self.running:
            try:
                # Check if it's time to process
                if self.should_process_now():
                    # Get jobs ready for processing
                    ready_jobs = await self.get_jobs_ready_for_processing()

                    if ready_jobs:
                        logger.info(f"Found {len(ready_jobs)} jobs ready for batch processing")

                        # Trigger batch processing
                        success = await self.trigger_batch_processing(ready_jobs)

                        if success:
                            logger.info(f"Batch processing triggered for {len(ready_jobs)} jobs")
                        else:
                            logger.error(f"Failed to trigger batch processing")
                    else:
                        logger.debug(f"No jobs ready for processing (strategy: {self.strategy}, threshold: {self.job_age_threshold}s)")

                    # Always cleanup old notebooks
                    await self.cleanup_old_notebooks()

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in batch service: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    def stop(self):
        """Stop the batch service."""
        logger.info("Stopping Kaggle batch service")
        self.running = False

# Global service instance
_batch_service = None

def get_kaggle_batch_service() -> KaggleBatchService:
    """Get the global Kaggle batch service instance."""
    global _batch_service
    if _batch_service is None:
        _batch_service = KaggleBatchService()
    return _batch_service

async def start_kaggle_batch_service():
    """Start the Kaggle batch service."""
    try:
        service = get_kaggle_batch_service()
        logger.info("🚀 Kaggle batch service starting...")
        await service.run_batch_service()
    except Exception as e:
        logger.error(f"❌ Kaggle batch service crashed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        # Don't re-raise to avoid crashing the main app

def stop_kaggle_batch_service():
    """Stop the Kaggle batch service."""
    global _batch_service
    if _batch_service:
        _batch_service.stop()