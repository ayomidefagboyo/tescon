#!/usr/bin/env python3
"""
Test end-to-end workflow with Render deployment.
Monitor mobile uploads → Render processing → Kaggle → Results
"""

import requests
import json
import time
import os
from datetime import datetime, timedelta
from pathlib import Path

class RenderDeploymentTester:
    def __init__(self, render_url=None):
        # Get Render URL from environment or user input
        self.render_url = render_url or os.getenv('RENDER_URL') or input("Enter your Render app URL (e.g., https://your-app.onrender.com): ").strip()

        if not self.render_url.startswith('http'):
            self.render_url = f"https://{self.render_url}"

        self.render_url = self.render_url.rstrip('/')

        print(f"🌐 Testing Render deployment: {self.render_url}")

        # For R2 monitoring, we'll need to set up local R2 client
        self.r2_storage = None
        self.setup_r2_connection()

    def setup_r2_connection(self):
        """Set up R2 connection for monitoring (requires local .env)."""
        try:
            import sys
            sys.path.append('app')
            from services.cloudflare_r2 import get_r2_storage

            self.r2_storage = get_r2_storage()
            if self.r2_storage:
                print("✅ R2 connection established for monitoring")
            else:
                print("⚠️ R2 connection not available - limited monitoring")
        except Exception as e:
            print(f"⚠️ R2 setup error: {e}")
            self.r2_storage = None

    def log(self, message, prefix="🌐"):
        """Log with timestamp."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {prefix} {message}")

    def test_render_health(self):
        """Test if Render deployment is healthy."""
        self.log("🔍 Checking Render deployment health")

        try:
            response = requests.get(f"{self.render_url}/health", timeout=15)

            if response.status_code == 200:
                health_data = response.json()
                self.log("✅ Render deployment is healthy")
                self.log(f"  📊 Status: {health_data.get('status', 'unknown')}")
                self.log(f"  ⏰ Server time: {health_data.get('timestamp', 'unknown')}")
                return True
            else:
                self.log(f"❌ Health check failed: {response.status_code}")
                return False

        except requests.RequestException as e:
            self.log(f"❌ Cannot connect to Render: {e}")
            self.log("  💡 Check if your Render app is deployed and running")
            return False

    def test_render_endpoints(self):
        """Test key Render endpoints."""
        self.log("🧪 Testing Render endpoints")

        endpoints = [
            ("/api/process/single", "POST", "Single image upload"),
            ("/api/jobs/submit", "POST", "Job submission"),
            ("/api/jobs/status", "GET", "Job status"),
            ("/api/parts/search?q=test", "GET", "Parts search")
        ]

        all_good = True

        for endpoint, method, description in endpoints:
            try:
                url = f"{self.render_url}{endpoint}"

                if method == "GET":
                    response = requests.get(url, timeout=10)
                else:
                    # Use OPTIONS to check if endpoint exists
                    response = requests.options(url, timeout=10)

                if response.status_code in [200, 405, 422]:  # Expected codes
                    self.log(f"  ✅ {description}")
                else:
                    self.log(f"  ❌ {description}: {response.status_code}")
                    all_good = False

            except Exception as e:
                self.log(f"  ❌ {description}: {str(e)}")
                all_good = False

        return all_good

    def test_mobile_upload_simulation(self):
        """Simulate a mobile upload to test the full pipeline."""
        self.log("📱 Simulating mobile upload to Render")

        try:
            # Create test image
            from PIL import Image
            from io import BytesIO

            # Create a test image with some content
            img = Image.new('RGB', (800, 600), color=(70, 130, 180))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            draw.rectangle([100, 100, 700, 500], outline=(255, 255, 255), width=3)
            draw.text((300, 280), "RENDER TEST", fill=(255, 255, 255))
            draw.text((280, 320), str(datetime.now().strftime("%H:%M:%S")), fill=(255, 255, 255))

            # Convert to bytes
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)

            # Test single upload endpoint
            files = {
                'file': ('render_test_58020640_1.jpg', buffer, 'image/jpeg')
            }
            data = {
                'format': 'PNG',
                'white_background': 'true',
                'compression_quality': '85'
            }

            self.log("  📤 Uploading test image...")
            start_time = time.time()

            response = requests.post(
                f"{self.render_url}/api/process/single",
                files=files,
                data=data,
                timeout=60  # Render can be slower
            )

            upload_time = time.time() - start_time

            if response.status_code == 200:
                self.log(f"  ✅ Upload successful ({upload_time:.1f}s)")

                # Check if we get a valid response
                if response.headers.get('content-type', '').startswith('image/'):
                    result_size = len(response.content)
                    self.log(f"  📊 Result: {result_size} bytes image")
                    return True
                else:
                    self.log(f"  ⚠️ Unexpected response type: {response.headers.get('content-type')}")

            else:
                self.log(f"  ❌ Upload failed: {response.status_code}")
                try:
                    error_data = response.json()
                    self.log(f"    Error: {error_data.get('detail', 'Unknown')}")
                except:
                    self.log(f"    Raw error: {response.text[:200]}")

            return False

        except Exception as e:
            self.log(f"❌ Upload simulation error: {e}")
            return False

    def monitor_r2_activity(self, duration_minutes=5):
        """Monitor R2 for activity from mobile uploads."""
        if not self.r2_storage:
            self.log("⚠️ R2 monitoring not available - check local .env file")
            return

        self.log(f"👀 Monitoring R2 activity for {duration_minutes} minutes")
        self.log("📱 Now upload images from your mobile app...")

        seen_files = set()
        start_time = time.time()

        while time.time() - start_time < (duration_minutes * 60):
            try:
                # Check for new uploads in last 2 minutes
                cutoff_time = datetime.now() - timedelta(minutes=2)

                # Check raw images
                response = self.r2_storage.s3_client.list_objects_v2(
                    Bucket=self.r2_storage.bucket_name,
                    Prefix='raw_images/'
                )

                new_files = []
                for obj in response.get('Contents', []):
                    key = obj['Key']
                    last_modified = obj['LastModified'].replace(tzinfo=None)

                    if (last_modified > cutoff_time and
                        key not in seen_files and
                        not key.endswith('/')):  # Skip folder markers

                        seen_files.add(key)
                        new_files.append({
                            'key': key,
                            'size': obj['Size'],
                            'age': (datetime.now() - last_modified).total_seconds()
                        })

                if new_files:
                    self.log(f"📤 New uploads detected:")
                    for file_info in new_files:
                        age = file_info['age']
                        size_mb = file_info['size'] / (1024 * 1024)
                        key_parts = Path(file_info['key']).parts

                        if len(key_parts) >= 3:
                            job_id = key_parts[1]
                            symbol = key_parts[2]
                            filename = key_parts[3] if len(key_parts) > 3 else 'unknown'

                            self.log(f"  📷 {filename}")
                            self.log(f"    📋 Job: {job_id}")
                            self.log(f"    🔖 Symbol: {symbol}")
                            self.log(f"    📊 Size: {size_mb:.1f}MB ({age:.0f}s ago)")

                # Check for processing jobs
                response = self.r2_storage.s3_client.list_objects_v2(
                    Bucket=self.r2_storage.bucket_name,
                    Prefix='jobs/queued/'
                )

                for obj in response.get('Contents', []):
                    if obj['Key'].endswith('.json'):
                        last_modified = obj['LastModified'].replace(tzinfo=None)
                        if last_modified > cutoff_time:
                            job_id = Path(obj['Key']).stem
                            age = (datetime.now() - last_modified).total_seconds()

                            if f"job_{job_id}" not in seen_files:
                                seen_files.add(f"job_{job_id}")
                                self.log(f"📋 New job queued: {job_id} ({age:.0f}s ago)")

                # Check processed results
                response = self.r2_storage.s3_client.list_objects_v2(
                    Bucket=self.r2_storage.bucket_name,
                    Prefix='processed_images/'
                )

                for obj in response.get('Contents', []):
                    last_modified = obj['LastModified'].replace(tzinfo=None)
                    if last_modified > cutoff_time:
                        key = obj['Key']
                        if key not in seen_files:
                            seen_files.add(key)
                            age = (datetime.now() - last_modified).total_seconds()
                            size_mb = obj['Size'] / (1024 * 1024)

                            if key.endswith('.zip'):
                                self.log(f"📦 Processed ZIP: {Path(key).name} ({size_mb:.1f}MB, {age:.0f}s ago)")
                            elif key.endswith(('.png', '.jpg', '.jpeg')):
                                self.log(f"🖼️ Processed image: {Path(key).name} ({size_mb:.1f}MB)")

                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                self.log(f"❌ Monitoring error: {e}")
                time.sleep(5)

    def show_recent_activity(self):
        """Show recent activity in R2."""
        if not self.r2_storage:
            self.log("⚠️ R2 access not available")
            return

        self.log("📊 Recent R2 Activity (last 30 minutes)")

        try:
            cutoff_time = datetime.now() - timedelta(minutes=30)

            # Count recent files by type
            counters = {
                'raw_uploads': 0,
                'queued_jobs': 0,
                'processed_images': 0,
                'zip_files': 0
            }

            # Check each prefix
            prefixes = {
                'raw_images/': 'raw_uploads',
                'jobs/queued/': 'queued_jobs',
                'processed_images/': 'processed_images'
            }

            for prefix, counter_key in prefixes.items():
                response = self.r2_storage.s3_client.list_objects_v2(
                    Bucket=self.r2_storage.bucket_name,
                    Prefix=prefix
                )

                for obj in response.get('Contents', []):
                    last_modified = obj['LastModified'].replace(tzinfo=None)
                    if last_modified > cutoff_time:
                        counters[counter_key] += 1

                        if obj['Key'].endswith('.zip'):
                            counters['zip_files'] += 1

            self.log(f"  📤 Raw uploads: {counters['raw_uploads']}")
            self.log(f"  📋 Queued jobs: {counters['queued_jobs']}")
            self.log(f"  🖼️ Processed images: {counters['processed_images']}")
            self.log(f"  📦 ZIP files: {counters['zip_files']}")

        except Exception as e:
            self.log(f"❌ Error checking activity: {e}")

def main():
    """Main testing function."""
    print("🚀 RENDER DEPLOYMENT END-TO-END TEST")
    print("=" * 60)

    tester = RenderDeploymentTester()

    # Test deployment health
    if not tester.test_render_health():
        print("❌ Render deployment not healthy - fix deployment first")
        return

    # Test endpoints
    if not tester.test_render_endpoints():
        print("⚠️ Some endpoints have issues")

    # Test upload simulation
    upload_works = tester.test_mobile_upload_simulation()

    if upload_works:
        print("\n✅ RENDER DEPLOYMENT IS WORKING!")

        # Show recent activity
        tester.show_recent_activity()

        # Ask about monitoring
        print("\n📱 Ready for mobile app testing!")
        print("Options:")
        print("1. Monitor R2 activity while you upload from mobile")
        print("2. Check current R2 status and exit")
        print("3. Exit now")

        choice = input("\nChoose option (1-3): ").strip()

        if choice == "1":
            duration = int(input("Monitor duration in minutes (5): ") or "5")
            tester.monitor_r2_activity(duration)
        elif choice == "2":
            tester.show_recent_activity()
    else:
        print("❌ Upload test failed - check Render logs")

if __name__ == "__main__":
    main()