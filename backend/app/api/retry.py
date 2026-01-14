"""Retry failed images from a job."""
import asyncio
import os
from typing import List
from fastapi import APIRouter, HTTPException, Query
from app.models import JobResponse, JobStatus
from app.processing.batch_manager import BatchProcessor
from app.api.jobs import job_manager
from app.storage.local_storage import LocalStorage

router = APIRouter()


@router.post("/jobs/{job_id}/retry", response_model=JobResponse)
async def retry_failed_images(
    job_id: str,
    output_format: str = "PNG",
    white_background: bool = True
):
    """
    Retry processing failed images from a completed job.
    
    Creates a new job with only the failed images from the original job.
    """
    original_job = job_manager.get_job(job_id)
    if not original_job:
        raise HTTPException(status_code=404, detail="Original job not found")
    
    if not original_job.get("failed_images"):
        raise HTTPException(status_code=400, detail="No failed images to retry")
    
    # Create new job for retry
    failed_count = len(original_job["failed_images"])
    new_job_id = job_manager.create_job(failed_count)
    
    # Get failed image filenames
    failed_filenames = original_job["failed_images"]
    
    # Load failed images from storage (if they still exist)
    storage = LocalStorage()
    image_data_list = []
    
    for filename in failed_filenames:
        # Try to find the original uploaded file
        # Note: This assumes files are still in uploads directory
        upload_path = storage.get_upload_path(filename)
        if upload_path.exists():
            with open(upload_path, "rb") as f:
                image_data_list.append({
                    'bytes': f.read(),
                    'filename': filename
                })
    
    if not image_data_list:
        raise HTTPException(
            status_code=404,
            detail="Failed images not found in storage. They may have been cleaned up."
        )
    
    # Process retry job in background
    batch_size = int(os.getenv("BATCH_SIZE", "500"))
    max_concurrent = int(os.getenv("MAX_CONCURRENT", "10"))
    batch_processor = BatchProcessor(batch_size=batch_size, max_concurrent=max_concurrent)
    
    asyncio.create_task(
        batch_processor.process_in_batches(
            new_job_id,
            image_data_list,
            output_format,
            white_background
        )
    )
    
    return JobResponse(
        job_id=new_job_id,
        status=JobStatus.PROCESSING,
        message=f"Retrying {len(image_data_list)} failed images"
    )

