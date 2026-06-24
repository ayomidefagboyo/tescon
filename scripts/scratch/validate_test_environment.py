#!/usr/bin/env python3
"""
Quick environment validation before full end-to-end test.
"""

import os
import sys
from pathlib import Path

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def validate_environment():
    """Check if all prerequisites are met for testing."""

    print("🔍 VALIDATING TEST ENVIRONMENT")
    print("=" * 50)

    issues = []

    # 1. Check .env file exists
    env_path = Path(".env")
    if env_path.exists():
        print("✅ .env file found")
    else:
        print("❌ .env file missing")
        issues.append(".env file not found")

    # 2. Check Excel file exists
    excel_path = Path("egtl_cleaned_OPTIMIZED_20260124_131513.xlsx")
    if excel_path.exists():
        print(f"✅ Excel file found ({excel_path.stat().st_size / (1024*1024):.1f}MB)")
    else:
        print("❌ Excel file missing")
        issues.append("Excel catalog file not found")

    # 3. Check R2 configuration
    try:
        from services.cloudflare_r2 import get_r2_storage
        r2_storage = get_r2_storage()

        if r2_storage:
            # Test connection
            try:
                r2_storage.s3_client.list_objects_v2(
                    Bucket=r2_storage.bucket_name,
                    MaxKeys=1
                )
                print("✅ R2 connection successful")
            except Exception as e:
                print(f"❌ R2 connection failed: {e}")
                issues.append(f"R2 connection error: {e}")
        else:
            print("❌ R2 not configured")
            issues.append("R2 storage not configured")

    except Exception as e:
        print(f"❌ R2 setup error: {e}")
        issues.append(f"R2 setup error: {e}")

    # 4. Check Kaggle CLI
    kaggle_path = Path("/Users/admin/Library/Python/3.9/bin/kaggle")
    if kaggle_path.exists():
        print("✅ Kaggle CLI found")

        # Test Kaggle authentication
        try:
            import subprocess
            result = subprocess.run([str(kaggle_path), 'datasets', 'list', '--max-size', '1'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ Kaggle authentication working")
            else:
                print("⚠️ Kaggle authentication may need setup")
                issues.append("Kaggle authentication needs verification")
        except Exception as e:
            print(f"⚠️ Kaggle test failed: {e}")
            issues.append("Kaggle CLI test failed")
    else:
        print("❌ Kaggle CLI not found")
        issues.append("Kaggle CLI not installed")

    # 5. Check processor availability
    try:
        from processing.processor_selector import get_processor_selector
        selector = get_processor_selector()
        available = selector._check_processor_availability()

        if available:
            print(f"✅ Processors available: {[p.value for p in available]}")
        else:
            print("❌ No processors available")
            issues.append("No image processors available")

    except Exception as e:
        print(f"❌ Processor check failed: {e}")
        issues.append(f"Processor check failed: {e}")

    # 6. Check required directories
    required_dirs = ['app', 'logs', 'uploads', 'processed']
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"✅ Directory exists: {dir_name}")
        else:
            print(f"⚠️ Directory missing: {dir_name} (will create)")
            try:
                dir_path.mkdir(exist_ok=True)
                print(f"  ✅ Created: {dir_name}")
            except Exception as e:
                print(f"  ❌ Cannot create: {dir_name} - {e}")
                issues.append(f"Cannot create directory: {dir_name}")

    print("\n" + "=" * 50)

    if issues:
        print(f"❌ VALIDATION FAILED - {len(issues)} issues found:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print("\nPlease fix these issues before running the full test.")
        return False
    else:
        print("✅ ALL CHECKS PASSED - Ready for end-to-end testing!")
        return True

if __name__ == "__main__":
    validate_environment()