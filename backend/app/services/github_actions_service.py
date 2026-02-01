"""
GitHub Actions integration service for triggering image processing workflows.
"""

import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime

from app.logging import setup_logger

logger = setup_logger("github_actions")


class GitHubActionsService:
    """Service to trigger and monitor GitHub Actions workflows."""

    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.repo_owner = os.getenv('GITHUB_REPO_OWNER', 'ayomidefagboyo')
        self.repo_name = os.getenv('GITHUB_REPO_NAME', 'tescon')
        self.workflow_file = os.getenv('GITHUB_WORKFLOW_FILE', 'process-images.yml')
        
        self.base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        self.enabled = bool(self.github_token)
        
        if not self.enabled:
            logger.warning("GitHub Actions service disabled - no GITHUB_TOKEN found")
        else:
            logger.info(f"GitHub Actions service initialized for {self.repo_owner}/{self.repo_name}")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests."""
        return {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    async def trigger_workflow(self, job_id: str) -> Optional[str]:
        """
        Trigger GitHub Actions workflow for a job.
        
        Args:
            job_id: Job ID to process
            
        Returns:
            Workflow run ID if successful, None otherwise
        """
        if not self.enabled:
            logger.error("Cannot trigger workflow - GitHub token not configured")
            return None

        try:
            url = f"{self.base_url}/actions/workflows/{self.workflow_file}/dispatches"
            
            payload = {
                "ref": "master",  # Branch to run workflow on
                "inputs": {
                    "job_id": job_id
                }
            }
            
            logger.info(f"Triggering GitHub Actions workflow for job: {job_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 204:
                        logger.info(f"✅ Successfully triggered workflow for job: {job_id}")
                        
                        # Wait a bit for the run to be created
                        await asyncio.sleep(2)
                        
                        # Get the run ID
                        run_id = await self._get_latest_run_id(job_id)
                        return run_id
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to trigger workflow: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error triggering GitHub Actions workflow: {e}")
            return None

    async def _get_latest_run_id(self, job_id: str) -> Optional[str]:
        """Get the latest workflow run ID for a job."""
        try:
            url = f"{self.base_url}/actions/workflows/{self.workflow_file}/runs"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self._get_headers(),
                    params={"per_page": 5},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        runs = data.get('workflow_runs', [])
                        
                        # Find the most recent run (they're sorted by created_at desc)
                        for run in runs:
                            if run.get('status') in ['queued', 'in_progress']:
                                return str(run['id'])
                        
                        # If no queued/in_progress, return the latest
                        if runs:
                            return str(runs[0]['id'])
                    
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting workflow run ID: {e}")
            return None

    async def get_workflow_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a workflow run.
        
        Args:
            run_id: Workflow run ID
            
        Returns:
            Dict with status info or None
        """
        try:
            url = f"{self.base_url}/actions/runs/{run_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'id': data['id'],
                            'status': data['status'],  # queued, in_progress, completed
                            'conclusion': data.get('conclusion'),  # success, failure, cancelled
                            'created_at': data['created_at'],
                            'updated_at': data['updated_at'],
                            'html_url': data['html_url']
                        }
                    else:
                        logger.error(f"Failed to get workflow status: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting workflow status: {e}")
            return None

    async def wait_for_completion(
        self,
        run_id: str,
        timeout_seconds: int = 3600,
        poll_interval: int = 30
    ) -> Optional[str]:
        """
        Wait for workflow to complete.
        
        Args:
            run_id: Workflow run ID
            timeout_seconds: Maximum time to wait
            poll_interval: Seconds between status checks
            
        Returns:
            Conclusion (success/failure) or None if timeout
        """
        start_time = datetime.now()
        
        while True:
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if elapsed > timeout_seconds:
                logger.error(f"Workflow {run_id} timed out after {timeout_seconds}s")
                return None
            
            status = await self.get_workflow_status(run_id)
            
            if not status:
                logger.error(f"Failed to get status for run {run_id}")
                return None
            
            if status['status'] == 'completed':
                conclusion = status['conclusion']
                logger.info(f"Workflow {run_id} completed with conclusion: {conclusion}")
                return conclusion
            
            logger.debug(f"Workflow {run_id} status: {status['status']} (elapsed: {elapsed:.0f}s)")
            await asyncio.sleep(poll_interval)

    async def get_workflow_logs(self, run_id: str) -> Optional[str]:
        """
        Get logs for a workflow run.
        
        Args:
            run_id: Workflow run ID
            
        Returns:
            Logs as string or None
        """
        try:
            url = f"{self.base_url}/actions/runs/{run_id}/logs"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        # Logs are returned as a zip file
                        # For now, just return the URL
                        return f"Logs available at: {url}"
                    else:
                        logger.error(f"Failed to get workflow logs: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting workflow logs: {e}")
            return None

    async def cancel_workflow(self, run_id: str) -> bool:
        """
        Cancel a running workflow.
        
        Args:
            run_id: Workflow run ID
            
        Returns:
            True if cancelled successfully
        """
        try:
            url = f"{self.base_url}/actions/runs/{run_id}/cancel"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 202:
                        logger.info(f"Successfully cancelled workflow {run_id}")
                        return True
                    else:
                        logger.error(f"Failed to cancel workflow: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error cancelling workflow: {e}")
            return False


# Global service instance
_github_actions_service = None


def get_github_actions_service() -> GitHubActionsService:
    """Get the global GitHub Actions service instance."""
    global _github_actions_service
    if _github_actions_service is None:
        _github_actions_service = GitHubActionsService()
    return _github_actions_service
