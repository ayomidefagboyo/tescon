#!/usr/bin/env python3
"""
Kaggle Background Worker for Render
This runs as a separate background service to process R2 job queues.
"""

import os
import sys
import time
import asyncio
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the Kaggle worker."""
    logger.info("🚀 Starting Kaggle Background Worker")

    try:
        # Import and start the Kaggle batch service
        from app.services.kaggle_batch_service import KaggleBatchService

        # Create service instance
        service = KaggleBatchService()

        # Run the service with proper error handling
        await service.run_batch_service()

    except KeyboardInterrupt:
        logger.info("⏹️ Kaggle worker stopped by user")
    except Exception as e:
        logger.error(f"❌ Kaggle worker crashed: {e}")
        import traceback
        logger.error(f"❌ Full traceback:\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Failed to start Kaggle worker: {e}")
        sys.exit(1)