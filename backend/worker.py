#!/usr/bin/env python3
"""
Render Background Worker for processing images from R2 storage.
This worker polls R2 for new jobs and processes them independently.
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.cloudflare_r2 import get_r2_storage
from services.excel_service import get_excel_parts_service
from services.parts_tracker import get_parts_tracker
from processing.picwish_processor import process_image
from processing.image_utils import validate_image


class R2BackgroundWorker:
    """Background worker that processes images using R2 as job queue."""

    def __init__(self):
        self.r2_storage = None
        self.excel_service = None
        self.parts_tracker = None
        self.running = False
        self.poll_interval = 5  # seconds

    async def initialize(self):
        """Initialize all services."""
        print("🚀 Initializing R2 Background Worker...")

        # Initialize R2 storage
        self.r2_storage = get_r2_storage()
        if not self.r2_storage:
            raise Exception("❌ Cloudflare R2 not configured")
        print("✅ R2 storage connected")

        # Initialize Excel service and load catalog
        self.excel_service = get_excel_parts_service()
        
        # Try to load Excel file if not already loaded
        if self.excel_service.unique_parts is None:
            excel_file_path = Path(__file__).parent / "egtl_cleaned_OPTIMIZED_20260124_131513.xlsx"
            if excel_file_path.exists():
                try:
                    print("📂 Loading Excel catalog with JDE data from file...")
                    success = self.excel_service.load_excel_file(str(excel_file_path), sheet_name="DATA")
                    if success:
                        stats = self.excel_service.get_stats()
                        print(f"✅ Excel catalog loaded: {stats['total_parts']} parts")

                        # Update parts tracker with total count
                        from services.parts_tracker import get_parts_tracker
                        tracker = get_parts_tracker()
                        tracker.set_total_parts(stats['total_parts'])
                    else:
                        raise Exception("❌ Failed to load Excel catalog file")
                except Exception as e:
                    raise Exception(f"❌ Error loading Excel catalog: {e}")
            else:
                raise Exception("❌ Excel catalog file not found. Ensure 'egtl_cleaned_OPTIMIZED_20260124_131513.xlsx' is in the backend directory.")
        else:
            print("✅ Excel catalog already loaded")

        # Initialize parts tracker
        self.parts_tracker = get_parts_tracker()
        print("✅ Parts tracker ready")

        print("🎯 Worker initialized successfully!")

    def list_job_files(self, prefix: str) -> List[str]:
        """List job files in R2 with given prefix."""
        try:
            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix=prefix
            )

            if 'Contents' not in response:
                return []

            return [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.json')]
        except Exception as e:
            print(f"⚠️  Error listing jobs: {e}")
            return []

    def get_job_metadata(self, job_key: str) -> Dict[str, Any]:
        """Download job metadata from R2."""
        try:
            response = self.r2_storage.s3_client.get_object(
                Bucket=self.r2_storage.bucket_name,
                Key=job_key
            )
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except Exception as e:
            print(f"⚠️  Error reading job {job_key}: {e}")
            return {}

    def move_job_file(self, from_key: str, to_key: str, metadata: Dict[str, Any]):
        """Move job file from one location to another in R2."""
        try:
            # Update metadata with completion info
            if 'completed_at' not in metadata:
                metadata['completed_at'] = datetime.now().isoformat()

            # Upload to new location
            self.r2_storage.s3_client.put_object(
                Bucket=self.r2_storage.bucket_name,
                Key=to_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json'
            )

            # Delete from old location
            self.r2_storage.s3_client.delete_object(
                Bucket=self.r2_storage.bucket_name,
                Key=from_key
            )
            return True
        except Exception as e:
            print(f"⚠️  Error moving job file: {e}")
            return False

    async def process_job(self, job_key: str, job_data: Dict[str, Any]) -> bool:
        """Process a single job."""
        job_id = job_data.get('job_id', 'unknown')
        symbol_number = job_data.get('symbol_number', 'unknown')

        print(f"🔄 Processing job {job_id} for part {symbol_number}")

        try:
            # Get part info from Excel
            part_info = self.excel_service.get_part_info(symbol_number)
            if not part_info:
                raise Exception(f"Part {symbol_number} not found in catalog")

            description = part_info.get("description", "")
            raw_file_paths = job_data.get('raw_file_paths', [])
            parameters = job_data.get('parameters', {})

            # Parse view numbers
            view_numbers = parameters.get("view_numbers")
            if view_numbers:
                view_nums = [int(v.strip()) for v in view_numbers.split(",")]
            else:
                view_nums = list(range(1, len(raw_file_paths) + 1))

            # Process each image
            processed_files = []

            for idx, file_info in enumerate(raw_file_paths):
                try:
                    print(f"  📷 Processing image {idx+1}/{len(raw_file_paths)}")

                    # Download file from R2
                    r2_key = file_info["r2_key"]
                    response = self.r2_storage.s3_client.get_object(
                        Bucket=self.r2_storage.bucket_name,
                        Key=r2_key
                    )
                    file_bytes = response['Body'].read()

                    # Validate image
                    is_valid, error_msg = validate_image(file_bytes)
                    if not is_valid:
                        print(f"    ❌ Invalid image: {error_msg}")
                        continue

                    # Process image with PicWish
                    view_num = view_nums[idx] if idx < len(view_nums) else idx + 1
                    output_format = "PNG" if parameters.get("format", "PNG").upper() == "PNG" else "JPEG"

                    processed_buffer = process_image(
                        file_bytes,
                        output_format=output_format,
                        white_background=parameters.get("white_background", True),
                        compression_quality=parameters.get("compression_quality", 85),
                        max_dimension=parameters.get("max_dimension", 2048),
                        description=description if parameters.get("add_label", True) else None,
                        add_label=parameters.get("add_label", True),
                        label_position=parameters.get("label_position", "bottom-left"),
                        item_note=part_info.get("item_note") or part_info.get("combined_description"),
                        symbol_number=symbol_number,
                        desc1=part_info.get("description_1") or part_info.get("description") or "",
                        desc2=part_info.get("description_2") or "",
                        long_description=part_info.get("long_text_jde"),  # Only Long Text JDE, no fallback
                        part_number=part_info.get("part_number") or parameters.get("part_number") or symbol_number,
                        manufacturer=part_info.get("manufacturer") or parameters.get("manufacturer"),
                        use_ecommerce_layout=True
                    )

                    # Generate filename
                    safe_description = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in description)
                    safe_description = safe_description.replace(' ', '_')[:50]
                    ext = ".jpg" if output_format.upper() in ["JPEG", "JPG"] else ".png"
                    filename = f"{symbol_number}_{view_num}_{safe_description}{ext}"

                    processed_bytes = processed_buffer.read()
                    processed_files.append((filename, processed_bytes))
                    print(f"    ✅ Processed: {filename}")

                except Exception as e:
                    print(f"    ❌ Failed to process image {idx+1}: {e}")
                    continue

            if not processed_files:
                raise Exception("No images processed successfully")

            # Upload processed images to R2
            saved_files = self.r2_storage.save_part_images(
                symbol_number=symbol_number,
                image_files=processed_files,
                description=description
            )

            # Mark part as processed in tracker
            self.parts_tracker.mark_part_processed(symbol_number, len(saved_files))

            # Cleanup raw images
            try:
                for file_info in raw_file_paths:
                    self.r2_storage.s3_client.delete_object(
                        Bucket=self.r2_storage.bucket_name,
                        Key=file_info["r2_key"]
                    )
                print(f"  🧹 Cleaned up {len(raw_file_paths)} raw files")
            except Exception as e:
                print(f"  ⚠️  Warning: Cleanup failed: {e}")

            # Move job to completed
            completed_key = job_key.replace('jobs/queued/', 'jobs/completed/')
            job_data['status'] = 'completed'
            job_data['processed_files_count'] = len(saved_files)

            if self.move_job_file(job_key, completed_key, job_data):
                print(f"✅ Job {job_id} completed: {len(saved_files)} images processed")
                return True
            else:
                print(f"⚠️  Job {job_id} processed but failed to move job file")
                return False

        except Exception as e:
            # Move job to failed
            failed_key = job_key.replace('jobs/queued/', 'jobs/failed/')
            job_data['status'] = 'failed'
            job_data['error'] = str(e)

            self.move_job_file(job_key, failed_key, job_data)
            print(f"❌ Job {job_id} failed: {e}")
            return False

    async def poll_jobs(self):
        """Main polling loop."""
        while self.running:
            try:
                # List queued jobs
                job_keys = self.list_job_files('jobs/queued/')

                if job_keys:
                    print(f"📋 Found {len(job_keys)} queued jobs")

                    for job_key in job_keys:
                        if not self.running:
                            break

                        job_data = self.get_job_metadata(job_key)
                        if job_data:
                            await self.process_job(job_key, job_data)

                        # Small delay between jobs
                        await asyncio.sleep(1)
                else:
                    # No jobs, shorter log message
                    print("💤 No jobs found, waiting...")

            except Exception as e:
                print(f"❌ Error in polling loop: {e}")

            # Wait before next poll
            await asyncio.sleep(self.poll_interval)

    async def start(self):
        """Start the worker."""
        await self.initialize()
        self.running = True
        print(f"🔄 Starting job polling (every {self.poll_interval}s)...")
        await self.poll_jobs()

    def stop(self):
        """Stop the worker."""
        print("⏹️  Stopping worker...")
        self.running = False


async def main():
    """Main entry point."""
    worker = R2BackgroundWorker()

    try:
        await worker.start()
    except KeyboardInterrupt:
        print("\n⏹️  Received interrupt signal")
        worker.stop()
    except Exception as e:
        print(f"❌ Worker crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())