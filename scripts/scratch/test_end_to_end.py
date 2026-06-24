#!/usr/bin/env python3
"""
Complete end-to-end test of Enhanced REMBG pipeline.
Tests: Upload → Kaggle Processing → Download
"""

import os
import sys
import time
import requests
import zipfile
from pathlib import Path
from PIL import Image
from datetime import datetime
import json

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.cloudflare_r2 import get_r2_storage
from services.excel_service import get_excel_parts_service

class EndToEndTester:
    def __init__(self):
        self.test_id = f"e2e_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.r2_storage = None
        self.excel_service = None
        self.test_results = {
            'test_id': self.test_id,
            'started_at': datetime.now().isoformat(),
            'stages': {}
        }

    def log(self, message, stage=None):
        """Log test progress."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")

        if stage:
            if stage not in self.test_results['stages']:
                self.test_results['stages'][stage] = []
            self.test_results['stages'][stage].append({
                'timestamp': timestamp,
                'message': message
            })

    def setup(self):
        """Initialize all required services."""
        self.log("🚀 Starting End-to-End Test Setup", "setup")

        # Test R2 connection
        self.log("Connecting to Cloudflare R2...", "setup")
        self.r2_storage = get_r2_storage()

        if not self.r2_storage:
            raise Exception("❌ R2 storage not configured")

        # Test R2 credentials
        try:
            self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                MaxKeys=1
            )
            self.log("✅ R2 connection successful", "setup")
        except Exception as e:
            raise Exception(f"❌ R2 connection failed: {e}")

        # Test Excel service
        self.log("Loading Excel catalog...", "setup")
        self.excel_service = get_excel_parts_service()

        # Load Excel file
        excel_file_path = Path("egtl_cleaned_OPTIMIZED_20260124_131513.xlsx")
        if excel_file_path.exists():
            success = self.excel_service.load_excel_file(str(excel_file_path), sheet_name="Sheet1")
            if success:
                stats = self.excel_service.get_stats()
                self.log(f"✅ Excel loaded: {stats['total_parts']} parts", "setup")
            else:
                raise Exception("❌ Failed to load Excel file")
        else:
            raise Exception("❌ Excel file not found")

    def create_test_images(self, count=3):
        """Create test images for processing."""
        self.log(f"🎨 Creating {count} test images", "test_data")

        test_images = []
        test_symbol = "58020640"  # Use known symbol from Excel

        for i in range(count):
            # Create a simple test image
            img = Image.new('RGB', (800, 600), color=(50 + i*50, 100 + i*30, 150 + i*20))

            # Add some content to make it interesting
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)

            # Draw some shapes
            draw.rectangle([100, 100, 300, 200], fill=(255, 255, 255))
            draw.ellipse([400, 200, 600, 400], fill=(200, 100, 50))
            draw.text((150, 140), f"Test Item {i+1}", fill=(0, 0, 0))
            draw.text((450, 450), f"Symbol: {test_symbol}", fill=(255, 255, 255))

            # Save to bytes
            from io import BytesIO
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            image_bytes = buffer.getvalue()

            filename = f"{test_symbol}_{i+1}_test_item.jpg"
            test_images.append({
                'symbol_number': test_symbol,
                'filename': filename,
                'bytes': image_bytes,
                'view_number': i + 1
            })

        self.log(f"✅ Created {len(test_images)} test images", "test_data")
        return test_images

    def upload_test_images(self, test_images):
        """Upload test images to R2 storage."""
        self.log(f"📤 Uploading {len(test_images)} test images to R2", "upload")

        uploaded_keys = []

        for img_data in test_images:
            try:
                # Upload to raw_images folder
                key = f"raw_images/{self.test_id}/{img_data['symbol_number']}/{img_data['filename']}"

                self.r2_storage.s3_client.put_object(
                    Bucket=self.r2_storage.bucket_name,
                    Key=key,
                    Body=img_data['bytes'],
                    ContentType='image/jpeg'
                )

                uploaded_keys.append(key)
                self.log(f"  ✅ Uploaded: {img_data['filename']}", "upload")

            except Exception as e:
                self.log(f"  ❌ Failed to upload {img_data['filename']}: {e}", "upload")

        self.log(f"✅ Upload complete: {len(uploaded_keys)}/{len(test_images)} files", "upload")
        return uploaded_keys

    def create_processing_job(self, test_images):
        """Create a job metadata file for processing."""
        self.log("📋 Creating processing job metadata", "job_creation")

        # Get part info for test symbol
        symbol_number = test_images[0]['symbol_number']
        part_info = self.excel_service.get_part_info(symbol_number)

        if not part_info:
            self.log(f"⚠️ Symbol {symbol_number} not found in Excel, using defaults", "job_creation")
            part_info = {
                'description': 'Test Item',
                'symbol_number': symbol_number
            }

        # Create job metadata
        job_data = {
            'job_id': self.test_id,
            'symbol_number': symbol_number,
            'created_at': datetime.now().isoformat(),
            'status': 'queued',
            'raw_file_paths': [],
            'parameters': {
                'format': 'PNG',
                'white_background': True,
                'add_label': True,
                'label_position': 'bottom-left',
                'compression_quality': 85,
                'max_dimension': 2048,
                'view_numbers': ','.join(str(img['view_number']) for img in test_images)
            }
        }

        # Add file paths
        for img_data in test_images:
            job_data['raw_file_paths'].append({
                'filename': img_data['filename'],
                'r2_key': f"raw_images/{self.test_id}/{img_data['symbol_number']}/{img_data['filename']}"
            })

        # Upload job metadata to R2
        job_key = f"jobs/queued/{self.test_id}.json"

        try:
            self.r2_storage.s3_client.put_object(
                Bucket=self.r2_storage.bucket_name,
                Key=job_key,
                Body=json.dumps(job_data, indent=2),
                ContentType='application/json'
            )
            self.log(f"✅ Job created: {job_key}", "job_creation")
            return job_data

        except Exception as e:
            self.log(f"❌ Failed to create job: {e}", "job_creation")
            raise

    def test_local_processing(self, test_images):
        """Test enhanced REMBG processing locally (fallback test)."""
        self.log("🔧 Testing local Enhanced REMBG processing", "local_test")

        try:
            from app.processing.processor_selector import process_with_optimal_selection

            for i, img_data in enumerate(test_images):
                self.log(f"  Processing image {i+1}/{len(test_images)}: {img_data['filename']}", "local_test")

                start_time = time.time()

                # Process with optimal selection
                result = process_with_optimal_selection(
                    img_data['bytes'],
                    output_format="PNG",
                    white_background=True,
                    compression_quality=85,
                    description=f"Test item for {img_data['symbol_number']}",
                    symbol_number=img_data['symbol_number']
                )

                processing_time = (time.time() - start_time) * 1000
                result_size = len(result.getvalue())

                self.log(f"  ✅ Processed in {processing_time:.0f}ms, output: {result_size} bytes", "local_test")

            self.log("✅ Local processing test successful", "local_test")

        except Exception as e:
            self.log(f"❌ Local processing failed: {e}", "local_test")
            return False

        return True

    def check_kaggle_status(self):
        """Check if Kaggle is set up and ready."""
        self.log("🔍 Checking Kaggle setup", "kaggle_check")

        # Check if Kaggle CLI is available
        try:
            import subprocess
            result = subprocess.run(['/Users/admin/Library/Python/3.9/bin/kaggle', '--version'],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                self.log(f"✅ Kaggle CLI available: {result.stdout.strip()}", "kaggle_check")

                # Try to check kernel status
                try:
                    result = subprocess.run([
                        '/Users/admin/Library/Python/3.9/bin/kaggle',
                        'kernels', 'status',
                        'ayomidefagboyo/daily-enhanced-rembg-processor'
                    ], capture_output=True, text=True, timeout=10)

                    if "complete" in result.stdout.lower() or "idle" in result.stdout.lower():
                        self.log("✅ Kaggle kernel is available", "kaggle_check")
                        return True
                    else:
                        self.log(f"⚠️ Kaggle kernel status: {result.stdout}", "kaggle_check")
                        return False

                except subprocess.TimeoutExpired:
                    self.log("⚠️ Kaggle API timeout - may need authentication", "kaggle_check")
                    return False
                except Exception as e:
                    self.log(f"⚠️ Kaggle kernel check failed: {e}", "kaggle_check")
                    return False
            else:
                self.log("❌ Kaggle CLI not available", "kaggle_check")
                return False

        except Exception as e:
            self.log(f"❌ Kaggle check failed: {e}", "kaggle_check")
            return False

    def wait_for_processing(self, timeout_minutes=30):
        """Wait for job to be processed."""
        self.log(f"⏳ Waiting for processing (timeout: {timeout_minutes}m)", "waiting")

        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        while time.time() - start_time < timeout_seconds:
            try:
                # Check if job moved to completed
                try:
                    completed_key = f"jobs/completed/{self.test_id}.json"
                    self.r2_storage.s3_client.head_object(
                        Bucket=self.r2_storage.bucket_name,
                        Key=completed_key
                    )
                    self.log("✅ Job marked as completed", "waiting")
                    return True
                except:
                    pass

                # Check if processed images exist
                try:
                    response = self.r2_storage.s3_client.list_objects_v2(
                        Bucket=self.r2_storage.bucket_name,
                        Prefix=f'processed_images/{self.test_id}/',
                        MaxKeys=1
                    )

                    if 'Contents' in response:
                        self.log("✅ Processed images found", "waiting")
                        return True

                except:
                    pass

                # Wait and try again
                time.sleep(30)
                elapsed = (time.time() - start_time) / 60
                self.log(f"  ⏱️ Still waiting... ({elapsed:.1f}m elapsed)", "waiting")

            except Exception as e:
                self.log(f"  ❌ Error checking status: {e}", "waiting")

        self.log(f"❌ Timeout after {timeout_minutes} minutes", "waiting")
        return False

    def verify_processed_images(self):
        """Check if processed images are available."""
        self.log("🔍 Verifying processed images", "verification")

        try:
            # List processed images
            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix=f'processed_images/{self.test_id}/'
            )

            if 'Contents' not in response:
                self.log("❌ No processed images found", "verification")
                return False

            processed_files = [obj['Key'] for obj in response['Contents']]
            self.log(f"✅ Found {len(processed_files)} processed files:", "verification")

            for file_key in processed_files:
                size = next(obj['Size'] for obj in response['Contents'] if obj['Key'] == file_key)
                self.log(f"  📁 {file_key} ({size} bytes)", "verification")

            # Check for ZIP file
            zip_files = [f for f in processed_files if f.endswith('.zip')]
            if zip_files:
                self.log(f"✅ ZIP file found: {zip_files[0]}", "verification")
            else:
                self.log("⚠️ No ZIP file found", "verification")

            return True

        except Exception as e:
            self.log(f"❌ Error verifying processed images: {e}", "verification")
            return False

    def download_and_inspect(self):
        """Download and inspect processed images."""
        self.log("📥 Downloading processed images for inspection", "download")

        try:
            # Create download directory
            download_dir = Path(f"test_downloads/{self.test_id}")
            download_dir.mkdir(parents=True, exist_ok=True)

            # List processed images
            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix=f'processed_images/{self.test_id}/'
            )

            downloaded_count = 0

            for obj in response.get('Contents', []):
                key = obj['Key']
                filename = Path(key).name

                # Download file
                local_path = download_dir / filename

                self.r2_storage.s3_client.download_file(
                    self.r2_storage.bucket_name,
                    key,
                    str(local_path)
                )

                downloaded_count += 1
                self.log(f"  ✅ Downloaded: {filename} ({obj['Size']} bytes)", "download")

                # Inspect if it's an image
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    try:
                        img = Image.open(local_path)
                        self.log(f"    📊 Image: {img.size[0]}x{img.size[1]}, mode: {img.mode}", "download")
                    except Exception as e:
                        self.log(f"    ❌ Cannot open image: {e}", "download")

            self.log(f"✅ Download complete: {downloaded_count} files in {download_dir}", "download")
            return True

        except Exception as e:
            self.log(f"❌ Download failed: {e}", "download")
            return False

    def cleanup(self):
        """Clean up test data."""
        self.log("🧹 Cleaning up test data", "cleanup")

        try:
            # List and delete all test files
            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix=f'{self.test_id}'
            )

            deleted_count = 0

            for obj in response.get('Contents', []):
                self.r2_storage.s3_client.delete_object(
                    Bucket=self.r2_storage.bucket_name,
                    Key=obj['Key']
                )
                deleted_count += 1

            # Also check other prefixes
            for prefix in ['raw_images/', 'processed_images/', 'jobs/queued/', 'jobs/completed/']:
                response = self.r2_storage.s3_client.list_objects_v2(
                    Bucket=self.r2_storage.bucket_name,
                    Prefix=f'{prefix}{self.test_id}'
                )

                for obj in response.get('Contents', []):
                    self.r2_storage.s3_client.delete_object(
                        Bucket=self.r2_storage.bucket_name,
                        Key=obj['Key']
                    )
                    deleted_count += 1

            self.log(f"✅ Cleanup complete: {deleted_count} files deleted", "cleanup")

        except Exception as e:
            self.log(f"❌ Cleanup failed: {e}", "cleanup")

    def save_test_report(self):
        """Save complete test report."""
        self.test_results['completed_at'] = datetime.now().isoformat()

        report_path = Path(f"test_reports/e2e_test_report_{self.test_id}.json")
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        self.log(f"📊 Test report saved: {report_path}", "report")

def run_full_test():
    """Run complete end-to-end test."""
    tester = EndToEndTester()

    try:
        print("🚀 ENHANCED REMBG END-TO-END TEST")
        print("=" * 60)

        # Step 1: Setup
        tester.setup()

        # Step 2: Create test data
        test_images = tester.create_test_images(3)

        # Step 3: Upload to R2
        uploaded_keys = tester.upload_test_images(test_images)

        # Step 4: Create processing job
        job_data = tester.create_processing_job(test_images)

        # Step 5: Test local processing (fallback)
        local_success = tester.test_local_processing(test_images)

        # Step 6: Check Kaggle status
        kaggle_ready = tester.check_kaggle_status()

        if kaggle_ready:
            tester.log("🎯 Kaggle is ready - you can now manually trigger processing", "status")
            tester.log(f"📋 Job ID to process: {tester.test_id}", "status")

            # Step 7: Wait for processing (or skip if manual)
            user_input = input("\nDo you want to wait for automatic processing? (y/n): ")

            if user_input.lower().startswith('y'):
                processing_success = tester.wait_for_processing(30)

                if processing_success:
                    # Step 8: Verify results
                    verification_success = tester.verify_processed_images()

                    if verification_success:
                        # Step 9: Download and inspect
                        download_success = tester.download_and_inspect()
            else:
                tester.log("⏭️ Skipping automatic wait - check manually", "status")
        else:
            tester.log("⚠️ Kaggle not ready - only local processing tested", "status")

        print("\n" + "=" * 60)
        print("🎉 END-TO-END TEST COMPLETE")
        print(f"📋 Test ID: {tester.test_id}")
        print(f"📁 Raw images uploaded to: raw_images/{tester.test_id}/")
        print(f"🔍 Check R2 bucket for processed results")
        print("=" * 60)

    except Exception as e:
        tester.log(f"❌ TEST FAILED: {e}", "error")
        print(f"\n💥 Test failed: {e}")

    finally:
        # Save test report
        tester.save_test_report()

        # Ask about cleanup
        cleanup_input = input("\nClean up test data? (y/n): ")
        if cleanup_input.lower().startswith('y'):
            tester.cleanup()

if __name__ == "__main__":
    run_full_test()