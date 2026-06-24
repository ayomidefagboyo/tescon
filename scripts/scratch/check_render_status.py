#!/usr/bin/env python3
"""
Quick Render deployment status checker.
"""

import requests
import json
import os
from datetime import datetime

def check_render_deployment(render_url=None):
    """Check Render deployment status."""

    # Get URL
    if not render_url:
        render_url = os.getenv('RENDER_URL')
        if not render_url:
            render_url = input("Enter your Render app URL: ").strip()

    if not render_url.startswith('http'):
        render_url = f"https://{render_url}"

    render_url = render_url.rstrip('/')

    print(f"🌐 Checking: {render_url}")
    print("=" * 50)

    # 1. Health check
    try:
        print("⏳ Checking health...")
        response = requests.get(f"{render_url}/health", timeout=20)

        if response.status_code == 200:
            health_data = response.json()
            print("✅ Deployment is healthy")
            print(f"  📊 Status: {health_data.get('status')}")
            print(f"  ⏰ Server time: {health_data.get('timestamp')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("❌ Health check timed out (Render may be sleeping)")
        print("💡 Try accessing the URL in browser to wake it up")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

    # 2. API endpoints
    print("\n🧪 Testing API endpoints...")

    endpoints = [
        "/api/jobs/status",
        "/api/parts/search?q=test",
        "/docs"  # FastAPI docs
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(f"{render_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"  ✅ {endpoint}")
            else:
                print(f"  ❌ {endpoint}: {response.status_code}")
        except:
            print(f"  ❌ {endpoint}: timeout/error")

    # 3. Upload endpoint test
    print("\n📤 Testing upload endpoint...")
    try:
        # Simple OPTIONS request to check if endpoint exists
        response = requests.options(f"{render_url}/api/process/single", timeout=10)
        if response.status_code in [200, 405]:
            print("  ✅ Upload endpoint available")
        else:
            print(f"  ❌ Upload endpoint issue: {response.status_code}")
    except:
        print("  ❌ Upload endpoint timeout")

    # 4. Show URLs for mobile testing
    print(f"\n📱 Mobile App URLs:")
    print(f"  🌐 Base URL: {render_url}")
    print(f"  📤 Upload: {render_url}/api/process/single")
    print(f"  📋 Jobs: {render_url}/api/jobs/submit")
    print(f"  📖 Docs: {render_url}/docs")

    # 5. Performance info
    print(f"\n⚡ Performance Notes:")
    print(f"  🕐 First request may take 30-60s (cold start)")
    print(f"  📱 Mobile uploads should work normally after warmup")
    print(f"  🔄 Render auto-sleeps after 15min inactivity")

    return True

if __name__ == "__main__":
    check_render_deployment()