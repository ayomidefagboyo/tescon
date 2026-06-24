#!/usr/bin/env python3
"""
Simple Kaggle processor - just runs the batch service directly
"""
import os
import sys
import asyncio
import traceback

print("🚀 Kaggle Processor Starting...")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

try:
    # Add app to path
    app_path = os.path.join(os.path.dirname(__file__), 'app')
    print(f"Adding to path: {app_path}")
    sys.path.append(app_path)

    print("✅ Path configured")

    async def main():
        try:
            print("📦 Importing KaggleBatchService...")

            # Import and run the existing batch service
            from services.kaggle_batch_service import KaggleBatchService

            print("✅ Import successful")
            print("🔧 Creating service instance...")

            service = KaggleBatchService()

            print("✅ Service created")
            print("🚀 Starting batch service...")

            await service.run_batch_service()

        except Exception as e:
            print(f"❌ Error in main: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            raise

    if __name__ == "__main__":
        print("🎯 Running async main...")
        asyncio.run(main())

except Exception as e:
    print(f"❌ Fatal error: {e}")
    print(f"❌ Full traceback: {traceback.format_exc()}")
    sys.exit(1)