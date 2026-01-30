#!/usr/bin/env python3
"""
Check if the backend server is running and ready for mobile uploads.
"""

import requests
import json
import time
from datetime import datetime

def check_server_status(base_url="http://localhost:8000"):
    """Check if the backend server is responding."""

    print("🔍 CHECKING BACKEND SERVER STATUS")
    print("=" * 50)

    # 1. Check health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health endpoint responding")
            health_data = response.json()
            print(f"  📊 Status: {health_data.get('status', 'unknown')}")
            print(f"  ⏰ Timestamp: {health_data.get('timestamp', 'unknown')}")
        else:
            print(f"❌ Health endpoint error: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        print("  💡 Make sure you're running: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return False

    # 2. Check upload endpoints
    endpoints_to_check = [
        ("/api/process/single", "POST", "Single image processing"),
        ("/api/process/bulk", "POST", "Bulk image processing"),
        ("/api/jobs/submit", "POST", "Job submission"),
        ("/api/parts/search", "GET", "Parts search")
    ]

    for endpoint, method, description in endpoints_to_check:
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}?q=test", timeout=5)
            else:
                # Just check if endpoint exists (will return method not allowed or validation error)
                response = requests.options(f"{base_url}{endpoint}", timeout=5)

            if response.status_code in [200, 405, 422]:  # 405 = method not allowed, 422 = validation error
                print(f"✅ {description} endpoint available")
            else:
                print(f"⚠️ {description} endpoint issue: {response.status_code}")

        except requests.RequestException as e:
            print(f"❌ {description} endpoint failed: {e}")

    # 3. Check R2 connection through API
    try:
        response = requests.get(f"{base_url}/api/jobs/status", timeout=10)
        if response.status_code == 200:
            print("✅ R2 storage connection working")
        else:
            print(f"⚠️ R2 connection may have issues: {response.status_code}")
    except:
        print("⚠️ Cannot verify R2 connection through API")

    # 4. Show current time for mobile app testing
    print(f"\n🕐 Current server time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Server URL: {base_url}")
    print("\n✅ Server appears ready for mobile app testing!")

    return True

def test_upload_endpoint(base_url="http://localhost:8000"):
    """Test the upload endpoint with a simple request."""
    print("\n🧪 Testing upload endpoint...")

    # Create a simple test image
    from PIL import Image
    from io import BytesIO

    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)

    try:
        files = {'file': ('test.jpg', buffer, 'image/jpeg')}
        data = {'format': 'PNG', 'white_background': 'true'}

        response = requests.post(
            f"{base_url}/api/process/single",
            files=files,
            data=data,
            timeout=30
        )

        if response.status_code == 200:
            print("✅ Upload endpoint working correctly")
            return True
        else:
            print(f"❌ Upload test failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"  Raw response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Upload test error: {e}")
        return False

if __name__ == "__main__":
    import sys

    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    server_ok = check_server_status(base_url)

    if server_ok:
        upload_ok = test_upload_endpoint(base_url)

        if upload_ok:
            print("\n🎉 BACKEND READY FOR MOBILE APP TESTING!")
            print("\n📱 Next steps:")
            print("1. Start monitoring: python monitor_mobile_upload.py")
            print("2. Upload images from your mobile app")
            print("3. Watch the monitoring output for real-time feedback")
        else:
            print("\n⚠️ Backend needs attention before mobile testing")
    else:
        print("\n❌ Backend server not ready")