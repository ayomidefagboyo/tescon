#!/usr/bin/env python3
"""
Diagnose deployment issues remotely.
Test your Render deployment to see why jobs are failing.
"""

import requests
import json
import time
from datetime import datetime

def test_deployment(render_url=None):
    """Test the deployment and diagnose issues."""

    # Get Render URL
    if not render_url:
        render_url = input("Enter your Render app URL: ").strip()

    if not render_url.startswith('http'):
        render_url = f"https://{render_url}"

    render_url = render_url.rstrip('/')

    print(f"🔍 Diagnosing deployment: {render_url}")
    print("=" * 60)

    # Test 1: Health check
    print("\n1️⃣ Testing health endpoint...")
    try:
        response = requests.get(f"{render_url}/health", timeout=10)
        if response.status_code == 200:
            health = response.json()
            print(f"   ✅ Health: {health.get('status', 'unknown')}")
            print(f"   📊 Model loaded: {health.get('model_loaded', 'unknown')}")
            print(f"   🖥️  GPU available: {health.get('gpu_available', 'unknown')}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return

    # Test 2: Environment debug
    print("\n2️⃣ Checking environment variables...")
    try:
        response = requests.get(f"{render_url}/api/debug/env", timeout=10)
        if response.status_code == 200:
            env_data = response.json()
            print(f"   📦 R2 Status: {env_data.get('r2_service_status', 'unknown')}")
            if env_data.get('r2_error'):
                print(f"   ❌ R2 Error: {env_data.get('r2_error')}")

            kaggle_configured = bool(env_data.get('environment_variables', {}).get('KAGGLE_USERNAME'))
            print(f"   🤖 Kaggle configured: {kaggle_configured}")
        else:
            print(f"   ❌ Environment check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Environment check error: {e}")

    # Test 3: Excel catalog status
    print("\n3️⃣ Checking Excel catalog...")
    try:
        response = requests.get(f"{render_url}/api/tracker/progress", timeout=10)
        if response.status_code == 200:
            progress = response.json()
            stats = progress.get('progress', {})
            total_parts = stats.get('total_parts', 0)
            if total_parts > 0:
                print(f"   ✅ Excel loaded: {total_parts} parts")
                print(f"   📊 Processed: {stats.get('processed_parts', 0)}")
                print(f"   ❌ Failed: {stats.get('failed_parts', 0)}")
            else:
                print(f"   ❌ No Excel catalog loaded")
        else:
            print(f"   ❌ Progress check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Progress check error: {e}")

    # Test 4: Check for recent failed jobs
    print("\n4️⃣ Checking recent job failures...")
    try:
        # We can't directly access R2 from here, but we can check job status
        # If user provides a job ID, we can check it
        print("   💡 To check specific job failure, provide job ID from your recent upload")
        job_id = input("   Enter job ID (or press Enter to skip): ").strip()

        if job_id:
            response = requests.get(f"{render_url}/api/jobs/{job_id}", timeout=10)
            if response.status_code == 200:
                job_data = response.json()
                print(f"   📋 Job Status: {job_data.get('status', 'unknown')}")
                print(f"   📊 Total: {job_data.get('total_images', 0)}")
                print(f"   ✅ Processed: {job_data.get('processed_count', 0)}")
                print(f"   ❌ Failed: {job_data.get('failed_count', 0)}")

                if job_data.get('failed_count', 0) > 0:
                    errors = job_data.get('error_messages', [])
                    if errors:
                        print(f"   💥 Errors:")
                        for error in errors[-3:]:  # Last 3 errors
                            print(f"      - {error}")
            else:
                print(f"   ❌ Job check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Job check error: {e}")

    # Test 5: Test simple upload
    print("\n5️⃣ Testing simple image processing...")
    test_simple = input("   Test with a simple image? (y/n): ").lower().strip()

    if test_simple == 'y':
        try:
            # Create a small test image
            from PIL import Image
            from io import BytesIO

            # Create test image
            img = Image.new('RGB', (100, 100), color=(255, 0, 0))
            buffer = BytesIO()
            img.save(buffer, format='JPEG')
            buffer.seek(0)

            files = {'file': ('test_diagnostic.jpg', buffer, 'image/jpeg')}
            data = {
                'format': 'PNG',
                'white_background': 'true',
                'compression_quality': '85'
            }

            print("   📤 Uploading test image...")
            response = requests.post(
                f"{render_url}/api/process/single",
                files=files,
                data=data,
                timeout=30
            )

            if response.status_code == 200:
                print(f"   ✅ Simple processing works! ({len(response.content)} bytes)")
            else:
                print(f"   ❌ Simple processing failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"      Error: {error_data.get('detail', 'Unknown')}")
                except:
                    print(f"      Raw error: {response.text[:200]}")

        except ImportError:
            print("   ⚠️  PIL not available, skipping image test")
        except Exception as e:
            print(f"   ❌ Test upload error: {e}")

    # Recommendations
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSIS SUMMARY & RECOMMENDATIONS:")
    print("=" * 60)

    print("\n📋 Likely causes of job failures:")
    print("1. Enhanced REMBG dependencies not installed on Render")
    print("   - torch, rembg, opencv-python-headless missing")
    print("   - Check requirements.txt includes these packages")

    print("\n2. Background worker not running")
    print("   - worker.py needs to run continuously on Render")
    print("   - Check if worker.py is in your start command")

    print("\n3. Kaggle integration not configured")
    print("   - Set KAGGLE_AUTO_TRIGGER_ENABLED=true")
    print("   - Add Kaggle credentials to Render environment")

    print("\n4. Excel catalog not loaded")
    print("   - Upload Excel file via /api/excel/upload")
    print("   - Or ensure Excel file exists in deployment")

    print("\n💡 IMMEDIATE FIXES:")
    print(f"1. Check Render logs: {render_url}/logs")
    print("2. Ensure requirements.txt has: torch, rembg, opencv-python-headless")
    print("3. Start background worker in deployment")
    print("4. Set Kaggle environment variables")

if __name__ == "__main__":
    test_deployment()