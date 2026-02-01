#!/usr/bin/env python3
"""
Updated Kaggle worker with better error handling and continuous running
"""
import os
import sys
import asyncio
import traceback
import time

print("🚀 Kaggle Worker Starting...")

def keep_alive_on_error(func):
    """Decorator to keep worker alive on errors so we can see logs"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ Error in {func.__name__}: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            print("⏸️ Keeping worker alive for debugging...")
            time.sleep(3600)  # Stay alive for 1 hour to see error
            sys.exit(1)
    return wrapper

@keep_alive_on_error
def main():
    # Add app to path
    sys.path.append('app')
    print("✅ Path configured")

    # Import services step by step
    from services.cloudflare_r2 import get_r2_storage
    print("✅ R2 service imported")

    # Test R2 connection
    r2 = get_r2_storage()
    print(f"✅ R2 storage: {'configured' if r2 else 'not configured'}")

    if not r2:
        print("❌ R2 not configured - check environment variables")
        time.sleep(3600)
        return

    # Import and create batch service
    from services.kaggle_batch_service import KaggleBatchService
    print("✅ KaggleBatchService imported")

    service = KaggleBatchService()
    print("✅ Service created successfully")
    print(f"Service enabled: {service.enabled}")
    print(f"Service strategy: {service.strategy}")
    print(f"Service check interval: {service.check_interval}s")

    if not service.enabled:
        print("❌ Service disabled - check KAGGLE_AUTO_TRIGGER_ENABLED")
        time.sleep(3600)
        return

    # Run the service continuously
    print("🔄 Starting continuous batch service...")
    asyncio.run(service.run_batch_service())

if __name__ == "__main__":
    main()