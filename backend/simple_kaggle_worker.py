#!/usr/bin/env python3
"""
Simple Kaggle worker - step by step debugging
"""
import os
import sys
import asyncio
import traceback

print("🚀 Kaggle Worker Starting...")

# Test 1: Basic imports
try:
    sys.path.append('app')
    print("✅ Path configured")

    # Test 2: Import services
    from services.cloudflare_r2 import get_r2_storage
    print("✅ R2 service imported")

    # Test 3: Test R2 connection
    r2 = get_r2_storage()
    print(f"✅ R2 storage: {'configured' if r2 else 'not configured'}")

    # Test 4: Import batch service
    from services.kaggle_batch_service import KaggleBatchService
    print("✅ KaggleBatchService imported")

    # Test 5: Create service
    service = KaggleBatchService()
    print("✅ Service created successfully")
    print(f"Service enabled: {service.enabled}")
    print(f"Service strategy: {service.strategy}")

    # Test 6: Check for jobs
    async def test_jobs():
        print("🔍 Testing job detection...")
        try:
            jobs = await service.get_jobs_ready_for_processing()
            print(f"✅ Found {len(jobs)} ready jobs")
            if jobs:
                for job in jobs:
                    print(f"  📋 Job: {job.get('job_id', 'unknown')}")
            return len(jobs) > 0
        except Exception as e:
            print(f"❌ Error getting jobs: {e}")
            return False

    # Run test
    has_jobs = asyncio.run(test_jobs())

    if has_jobs:
        print("🎯 Jobs found! Starting actual processing...")
        # Run the real service
        asyncio.run(service.run_batch_service())
    else:
        print("💤 No jobs found, but service is working. Waiting...")
        # Keep alive and check periodically
        while True:
            import time
            time.sleep(300)  # Check every 5 minutes
            has_jobs = asyncio.run(test_jobs())
            if has_jobs:
                print("🎯 New jobs detected! Starting processing...")
                asyncio.run(service.run_batch_service())
                break

except Exception as e:
    print(f"❌ Error: {e}")
    print(f"❌ Traceback: {traceback.format_exc()}")
    # Keep the worker alive to see the error
    import time
    time.sleep(3600)