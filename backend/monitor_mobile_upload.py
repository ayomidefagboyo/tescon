#!/usr/bin/env python3
"""
Monitor mobile app uploads and track processing pipeline.
Run this while testing from mobile app.
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from services.cloudflare_r2 import get_r2_storage
    from services.excel_service import get_excel_parts_service
    from services.parts_tracker import get_parts_tracker
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class MobileUploadMonitor:
    def __init__(self):
        self.r2_storage = get_r2_storage()
        self.excel_service = get_excel_parts_service()
        self.parts_tracker = get_parts_tracker()
        self.monitoring = True

        # Track what we've seen
        self.seen_jobs = set()
        self.seen_raw_images = set()
        self.seen_processed_images = set()

        # Load Excel if needed
        self._load_excel()

    def _load_excel(self):
        """Load Excel catalog if not already loaded."""
        if self.excel_service.unique_parts is None:
            excel_file_path = Path("EGTL_FINAL_23033_CLEANED.xlsx")
            if excel_file_path.exists():
                print("📂 Loading Excel catalog...")
                success = self.excel_service.load_excel_file(str(excel_file_path), sheet_name="Sheet1")
                if success:
                    stats = self.excel_service.get_stats()
                    print(f"✅ Excel loaded: {stats['total_parts']} parts")
                else:
                    print("❌ Failed to load Excel file")
            else:
                print("❌ Excel file not found")

    def log(self, message, prefix="📱"):
        """Log with timestamp."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {prefix} {message}")

    def check_new_uploads(self):
        """Check for new mobile uploads in raw_images."""
        try:
            # Look for recent uploads (last 10 minutes)
            cutoff_time = datetime.now() - timedelta(minutes=10)

            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix='raw_images/'
            )

            new_uploads = []

            for obj in response.get('Contents', []):
                key = obj['Key']
                last_modified = obj['LastModified'].replace(tzinfo=None)

                if last_modified > cutoff_time and key not in self.seen_raw_images:
                    self.seen_raw_images.add(key)
                    new_uploads.append({
                        'key': key,
                        'size': obj['Size'],
                        'modified': last_modified,
                        'age_seconds': (datetime.now() - last_modified).total_seconds()
                    })

            if new_uploads:
                self.log(f"🆕 Found {len(new_uploads)} new uploads:", "📤")
                for upload in new_uploads:
                    age = upload['age_seconds']
                    size_mb = upload['size'] / (1024 * 1024)
                    self.log(f"  📷 {upload['key']} ({size_mb:.1f}MB, {age:.0f}s ago)")

                    # Extract info from path
                    path_parts = Path(upload['key']).parts
                    if len(path_parts) >= 3:
                        job_id = path_parts[1] if len(path_parts) > 1 else 'unknown'
                        symbol_number = path_parts[2] if len(path_parts) > 2 else 'unknown'
                        filename = path_parts[3] if len(path_parts) > 3 else 'unknown'

                        # Check if part exists in Excel
                        part_info = self.excel_service.get_part_info(symbol_number)
                        if part_info:
                            self.log(f"    ✅ Part found: {part_info.get('description', 'No description')}")
                        else:
                            self.log(f"    ⚠️ Part {symbol_number} not in Excel catalog")

            return new_uploads

        except Exception as e:
            self.log(f"❌ Error checking uploads: {e}")
            return []

    def check_new_jobs(self):
        """Check for new jobs in the queue."""
        try:
            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix='jobs/queued/'
            )

            new_jobs = []

            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.json') and key not in self.seen_jobs:
                    self.seen_jobs.add(key)

                    # Download and parse job
                    try:
                        job_response = self.r2_storage.s3_client.get_object(
                            Bucket=self.r2_storage.bucket_name,
                            Key=key
                        )
                        job_data = json.loads(job_response['Body'].read().decode('utf-8'))

                        new_jobs.append({
                            'key': key,
                            'data': job_data,
                            'created': obj['LastModified']
                        })

                    except Exception as e:
                        self.log(f"❌ Error reading job {key}: {e}")

            if new_jobs:
                self.log(f"🆕 Found {len(new_jobs)} new jobs:", "📋")
                for job in new_jobs:
                    data = job['data']
                    job_id = data.get('job_id', 'unknown')
                    symbol = data.get('symbol_number', 'unknown')
                    file_count = len(data.get('raw_file_paths', []))

                    self.log(f"  📋 {job_id}: {symbol} ({file_count} files)")

                    # Show job parameters
                    params = data.get('parameters', {})
                    format_type = params.get('format', 'PNG')
                    bg = "white" if params.get('white_background', True) else "transparent"
                    self.log(f"    ⚙️ Format: {format_type}, Background: {bg}")

            return new_jobs

        except Exception as e:
            self.log(f"❌ Error checking jobs: {e}")
            return []

    def check_processing_status(self):
        """Check for completed/failed jobs."""
        try:
            # Check completed jobs
            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix='jobs/completed/'
            )

            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.json'):
                    job_id = Path(key).stem
                    age = (datetime.now() - obj['LastModified'].replace(tzinfo=None)).total_seconds()

                    if age < 600:  # Last 10 minutes
                        self.log(f"✅ Job completed: {job_id} ({age:.0f}s ago)", "🎉")

            # Check failed jobs
            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix='jobs/failed/'
            )

            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.json'):
                    job_id = Path(key).stem
                    age = (datetime.now() - obj['LastModified'].replace(tzinfo=None)).total_seconds()

                    if age < 600:  # Last 10 minutes
                        self.log(f"❌ Job failed: {job_id} ({age:.0f}s ago)", "💥")

                        # Try to get error details
                        try:
                            job_response = self.r2_storage.s3_client.get_object(
                                Bucket=self.r2_storage.bucket_name,
                                Key=key
                            )
                            job_data = json.loads(job_response['Body'].read().decode('utf-8'))
                            error = job_data.get('error', 'Unknown error')
                            self.log(f"    💥 Error: {error}")
                        except:
                            pass

        except Exception as e:
            self.log(f"❌ Error checking processing status: {e}")

    def check_processed_images(self):
        """Check for new processed images."""
        try:
            # Look for recent processed images (last 10 minutes)
            cutoff_time = datetime.now() - timedelta(minutes=10)

            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix='processed_images/'
            )

            new_processed = []

            for obj in response.get('Contents', []):
                key = obj['Key']
                last_modified = obj['LastModified'].replace(tzinfo=None)

                if last_modified > cutoff_time and key not in self.seen_processed_images:
                    self.seen_processed_images.add(key)
                    new_processed.append({
                        'key': key,
                        'size': obj['Size'],
                        'modified': last_modified
                    })

            if new_processed:
                self.log(f"🆕 Found {len(new_processed)} new processed files:", "📥")

                zip_files = []
                image_files = []

                for item in new_processed:
                    key = item['key']
                    size_mb = item['size'] / (1024 * 1024)

                    if key.endswith('.zip'):
                        zip_files.append(f"{Path(key).name} ({size_mb:.1f}MB)")
                    elif key.endswith(('.png', '.jpg', '.jpeg')):
                        image_files.append(f"{Path(key).name} ({size_mb:.1f}MB)")

                if zip_files:
                    self.log(f"  📦 ZIP files: {', '.join(zip_files)}")
                if image_files:
                    self.log(f"  🖼️ Images: {len(image_files)} files")

            return new_processed

        except Exception as e:
            self.log(f"❌ Error checking processed images: {e}")
            return []

    def show_status_summary(self):
        """Show current system status."""
        try:
            # Count current items
            queued_count = 0
            try:
                response = self.r2_storage.s3_client.list_objects_v2(
                    Bucket=self.r2_storage.bucket_name,
                    Prefix='jobs/queued/'
                )
                queued_count = len([obj for obj in response.get('Contents', []) if obj['Key'].endswith('.json')])
            except:
                pass

            # Parts tracker status
            try:
                tracker_stats = self.parts_tracker.get_stats()
                processed_parts = tracker_stats.get('processed_parts', 0)
                total_parts = tracker_stats.get('total_parts', 0)
            except:
                processed_parts = 0
                total_parts = 0

            self.log(f"📊 Status: {queued_count} queued jobs | {processed_parts}/{total_parts} parts processed", "📈")

        except Exception as e:
            self.log(f"❌ Error getting status: {e}")

    def monitor_continuously(self):
        """Main monitoring loop."""
        self.log("🚀 Mobile Upload Monitor Started")
        self.log("📱 Upload images from your mobile app now...")
        self.log("⏹️  Press Ctrl+C to stop monitoring")
        print()

        try:
            while self.monitoring:
                # Check for new activity
                new_uploads = self.check_new_uploads()
                new_jobs = self.check_new_jobs()
                new_processed = self.check_processed_images()

                # Check processing status
                self.check_processing_status()

                # Show periodic status
                if int(time.time()) % 60 == 0:  # Every minute
                    self.show_status_summary()

                # Wait before next check
                time.sleep(5)

        except KeyboardInterrupt:
            self.log("⏹️  Monitoring stopped by user")
        except Exception as e:
            self.log(f"❌ Monitor error: {e}")

    def show_recent_activity(self, minutes=30):
        """Show activity from last N minutes."""
        self.log(f"📊 Recent Activity (last {minutes} minutes)")
        print("=" * 60)

        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        try:
            # Raw uploads
            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix='raw_images/'
            )

            recent_uploads = []
            for obj in response.get('Contents', []):
                if obj['LastModified'].replace(tzinfo=None) > cutoff_time:
                    recent_uploads.append(obj)

            if recent_uploads:
                self.log(f"📤 Raw uploads: {len(recent_uploads)} files")
                for obj in recent_uploads[-5:]:  # Show last 5
                    age = (datetime.now() - obj['LastModified'].replace(tzinfo=None)).total_seconds()
                    size_mb = obj['Size'] / (1024 * 1024)
                    self.log(f"  📷 {Path(obj['Key']).name} ({size_mb:.1f}MB, {age:.0f}s ago)")

            # Processed images
            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix='processed_images/'
            )

            recent_processed = []
            for obj in response.get('Contents', []):
                if obj['LastModified'].replace(tzinfo=None) > cutoff_time:
                    recent_processed.append(obj)

            if recent_processed:
                self.log(f"📥 Processed files: {len(recent_processed)} files")
                zip_count = len([obj for obj in recent_processed if obj['Key'].endswith('.zip')])
                img_count = len([obj for obj in recent_processed if obj['Key'].endswith(('.png', '.jpg'))])
                self.log(f"  📦 {zip_count} ZIP files, 🖼️ {img_count} images")

            if not recent_uploads and not recent_processed:
                self.log("💤 No recent activity found")

        except Exception as e:
            self.log(f"❌ Error checking recent activity: {e}")

def main():
    """Main function."""
    monitor = MobileUploadMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        # Just show recent activity
        monitor.show_recent_activity(30)
    else:
        # Start continuous monitoring
        monitor.monitor_continuously()

if __name__ == "__main__":
    main()