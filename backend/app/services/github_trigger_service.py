"""
GitHub Actions trigger service - simplified version without Kaggle fallback.
Runs as background task in Render to monitor R2 and trigger GitHub Actions workflows.
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from app.services.cloudflare_r2 import get_r2_storage
from app.services.github_actions_service import get_github_actions_service
from app.logging import setup_logger

logger = setup_logger("github_trigger")


class GitHubTriggerService:
    """Service to automatically trigger GitHub Actions for image processing."""

    def __init__(self):
        self.r2_storage = get_r2_storage()
        self.github_actions = get_github_actions_service()
        
        # Track processed jobs
        self.processed_jobs = set()
        self.running = False

        # Auto-trigger settings
        self.check_interval = int(os.getenv('GITHUB_CHECK_INTERVAL', '300'))  # 5 minutes
        self.job_age_threshold = int(os.getenv('GITHUB_JOB_AGE_THRESHOLD', '120'))  # 2 minutes
        self.enabled = os.getenv('GITHUB_AUTO_TRIGGER_ENABLED', 'true').lower() == 'true'

        logger.info(f"GitHub trigger service initialized (enabled: {self.enabled})")

    async def check_for_new_jobs(self) -> List[Dict[str, Any]]:
        """Check R2 for jobs ready for processing."""
        try:
            if not self.r2_storage:
                return []

            response = self.r2_storage.s3_client.list_objects_v2(
                Bucket=self.r2_storage.bucket_name,
                Prefix='jobs/queued/'
            )

            new_jobs = []

            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.json'):
                    job_id = Path(key).stem

                    # Skip if already processed
                    if job_id in self.processed_jobs:
                        continue

                    # Check job age
                    job_age = (datetime.now() - obj['LastModified'].replace(tzinfo=None)).total_seconds()

                    if job_age > self.job_age_threshold:
                        try:
                            # Get job data
                            job_response = self.r2_storage.s3_client.get_object(
                                Bucket=self.r2_storage.bucket_name,
                                Key=key
                            )
                            job_data = json.loads(job_response['Body'].read().decode('utf-8'))

                            new_jobs.append({
                                'job_id': job_id,
                                'key': key,
                                'data': job_data,
                                'age_minutes': job_age / 60
                            })

                        except Exception as e:
                            logger.error(f"Error reading job {job_id}: {e}")

            return new_jobs

        except Exception as e:
            logger.error(f"Error checking for new jobs: {e}")
            return []

    async def trigger_job(self, job_id: str) -> bool:
        """
        Trigger GitHub Actions workflow for a job.
        
        Args:
            job_id: Job ID to process
            
        Returns:
            True if triggered successfully
        """
        if not self.github_actions.enabled:
            logger.error("GitHub Actions not configured - missing GITHUB_TOKEN")
            return False

        try:
            logger.info(f"Triggering GitHub Actions for job: {job_id}")
            
            run_id = await self.github_actions.trigger_workflow(job_id)
            
            if run_id:
                logger.info(f"✅ GitHub Actions triggered for job {job_id} (run: {run_id})")
                self.processed_jobs.add(job_id)
                return True
            else:
                logger.error(f"❌ Failed to trigger GitHub Actions for job {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error triggering job {job_id}: {e}")
            return False

    async def run_background_service(self):
        """Main background service loop."""
        if not self.enabled:
            logger.info("GitHub trigger service disabled")
            return

        logger.info("Starting GitHub Actions trigger service")
        self.running = True

        while self.running:
            try:
                # Check for new jobs
                new_jobs = await self.check_for_new_jobs()

                if new_jobs:
                    logger.info(f"Found {len(new_jobs)} jobs ready for processing")

                    for job in new_jobs:
                        if not self.running:
                            break

                        job_id = job['job_id']
                        success = await self.trigger_job(job_id)

                        if success:
                            logger.info(f"Job {job_id} triggered successfully")
                        else:
                            logger.error(f"Failed to trigger job {job_id}")

                        # Wait between jobs to avoid rate limits
                        await asyncio.sleep(10)

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in background service: {e}")
                await asyncio.sleep(60)  # Wait before retry

    def stop(self):
        """Stop the background service."""
        logger.info("Stopping GitHub trigger service")
        self.running = False


# Global service instance
_github_trigger_service = None


def get_github_trigger_service() -> GitHubTriggerService:
    """Get the global GitHub trigger service instance."""
    global _github_trigger_service
    if _github_trigger_service is None:
        _github_trigger_service = GitHubTriggerService()
    return _github_trigger_service


async def start_github_trigger_service():
    """Start the GitHub trigger background service."""
    service = get_github_trigger_service()
    await service.run_background_service()


def stop_github_trigger_service():
    """Stop the GitHub trigger service."""
    global _github_trigger_service
    if _github_trigger_service:
        _github_trigger_service.stop()
