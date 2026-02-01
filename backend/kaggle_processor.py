#!/usr/bin/env python3
"""
Simple Kaggle processor - just runs the batch service directly
"""
import os
import sys
import asyncio

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def main():
    print("🚀 Starting Kaggle Processor...")

    # Import and run the existing batch service
    from services.kaggle_batch_service import KaggleBatchService

    service = KaggleBatchService()
    await service.run_batch_service()

if __name__ == "__main__":
    asyncio.run(main())