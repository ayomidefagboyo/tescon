"""
GitHub Actions background worker for Render.
This runs as a separate Render Background Worker service.
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.github_trigger_service import start_github_trigger_service, stop_github_trigger_service
from app.logging import setup_logger

logger = setup_logger("github_worker")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    stop_github_trigger_service()
    sys.exit(0)


async def main():
    """Main entry point for GitHub Actions worker."""
    logger.info("=" * 60)
    logger.info("GitHub Actions Background Worker Starting")
    logger.info("=" * 60)
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start the GitHub trigger service
        await start_github_trigger_service()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in worker: {e}")
        import traceback
        traceback.print_exc()
    finally:
        stop_github_trigger_service()
        logger.info("GitHub Actions worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
