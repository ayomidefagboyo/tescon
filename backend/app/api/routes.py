"""API routes for image processing."""
import os
import time
import zipfile
import asyncio
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from app.models import JobResponse, JobStatusResponse, JobStatus
from app.processing.picwish_processor import process_image, check_api_available
from app.processing.image_utils import validate_image
from app.processing.batch_manager import BatchProcessor
from app.storage.local_storage import LocalStorage
from app.api.jobs import job_manager
from app.logging import log_image_processing, log_gpu_metrics

router = APIRouter()

# Initialize storage
storage = LocalStorage(
    upload_dir=os.getenv("UPLOAD_DIR", "uploads"),
    processed_dir=os.getenv("PROCESSED_DIR", "processed"),
    cleanup_ttl_hours=int(os.getenv("CLEANUP_TTL_HOURS", "24"))
)


@router.post("/process/single")
async def process_single_image(
    file: UploadFile = File(...),
    format: str = Query("PNG", regex="^(PNG|JPEG|JPG)$"),
    white_background: bool = Query(True)
):
    """
    Process a single image synchronously.
    
    Returns processed image immediately.
    """
    # Read file
    file_bytes = await file.read()
    
    # Validate image
    is_valid, error_msg = validate_image(file_bytes)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Process image
    start_time = time.time()
    api_available = check_api_available()
    
    try:
        output_format = "PNG" if format.upper() == "PNG" else "JPEG"
        processed_buffer = process_image(file_bytes, output_format, white_background)
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Log successful processing
        log_image_processing(
            image_filename=file.filename or "unknown",
            gpu_used=False,  # API-based, no GPU
            processing_time_ms=processing_time_ms,
            image_size_bytes=len(file_bytes),
            success=True
        )
        
        # Return processed image
        media_type = "image/png" if format.upper() == "PNG" else "image/jpeg"
        return StreamingResponse(
            processed_buffer,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="processed_{file.filename}"'
            }
        )
    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Log failed processing
        log_image_processing(
            image_filename=file.filename or "unknown",
            gpu_used=False,  # API-based, no GPU
            processing_time_ms=processing_time_ms,
            image_size_bytes=len(file_bytes),
            success=False,
            error=str(e)
        )
        
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/process/bulk", response_model=JobResponse)
async def process_bulk_images(
    files: List[UploadFile] = File(...),
    format: str = Query("PNG", regex="^(PNG|JPEG|JPG)$"),
    white_background: bool = Query(True)
):
    """
    Process multiple images asynchronously.
    
    Accepts multiple image files or a ZIP file containing images.
    Returns job ID for status tracking.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Check if first file is a ZIP
    first_file = files[0]
    if first_file.filename and first_file.filename.lower().endswith(".zip"):
        # Extract ZIP file
        zip_bytes = await first_file.read()
        image_files = await extract_images_from_zip(zip_bytes)
    else:
        # Filter valid image files
        image_files = []
        for file in files:
            if file.filename:
                ext = Path(file.filename).suffix.lower()
                if ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    image_files.append(file)
    
    if not image_files:
        raise HTTPException(status_code=400, detail="No valid image files found")
    
    # Create job
    job_id = job_manager.create_job(len(image_files))
    
    # Start async processing
    asyncio.create_task(
        process_bulk_job(job_id, image_files, format, white_background)
    )
    
    return JobResponse(
        job_id=job_id,
        status=JobStatus.PROCESSING,
        message=f"Processing {len(image_files)} images"
    )


async def extract_images_from_zip(zip_bytes: bytes) -> List[UploadFile]:
    """Extract image files from ZIP archive."""
    import tempfile
    from io import BytesIO
    
    image_files = []
    
    try:
        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zip_ref:
            for file_info in zip_ref.namelist():
                # Check if file is an image
                ext = Path(file_info).suffix.lower()
                if ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    # Read file from ZIP
                    file_data = zip_ref.read(file_info)
                    
                    # Create UploadFile-like object
                    # We'll use a simple wrapper
                    class ZipFileWrapper:
                        def __init__(self, data: bytes, filename: str):
                            self.data = data
                            self.filename = filename
                        
                        async def read(self):
                            return self.data
                    
                    image_files.append(ZipFileWrapper(file_data, file_info))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    
    return image_files


async def process_bulk_job(
    job_id: str,
    files: List,
    output_format: str,
    white_background: bool
):
    """Process bulk images in background with batching support."""
    api_available = check_api_available()
    
    # Log API availability at start
    log_gpu_metrics(gpu_available=False)  # API-based, no GPU
    
    # Get batch size from environment (default: 500 for large volumes)
    batch_size = int(os.getenv("BATCH_SIZE", "500"))
    max_concurrent = int(os.getenv("MAX_CONCURRENT", "10"))
    
    # Initialize batch processor
    batch_processor = BatchProcessor(batch_size=batch_size, max_concurrent=max_concurrent)
    
    try:
        # Prepare image data list
        image_data_list = []
        
        for file in files:
            try:
                # Read file (handles both UploadFile and ZipFileWrapper)
                if hasattr(file, 'read'):
                    if asyncio.iscoroutinefunction(file.read):
                        file_bytes = await file.read()
                    else:
                        file_bytes = file.read()
                else:
                    file_bytes = file
                
                # Get filename
                filename = getattr(file, 'filename', 'image')
                
                image_data_list.append({
                    'bytes': file_bytes,
                    'filename': filename
                })
                
            except Exception as e:
                filename = getattr(file, 'filename', 'unknown')
                job_manager.add_failed_image(job_id, filename, f"Failed to read file: {str(e)}")
        
        # Process all images in batches
        await batch_processor.process_in_batches(
            job_id,
            image_data_list,
            output_format,
            white_background
        )
        
    except Exception as e:
        job_manager.complete_job(job_id, success=False)
        job_manager.add_failed_image(job_id, "job", f"Job failed: {str(e)}")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get job status."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        total_images=job["total_images"],
        processed_count=job["processed_count"],
        failed_count=job["failed_count"],
        failed_images=job["failed_images"] if job["failed_images"] else None,
        error_messages=job["error_messages"] if job["error_messages"] else None
    )


@router.get("/jobs/{job_id}/download")
async def download_job_results(job_id: str):
    """Download processed images as ZIP."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    # Find ZIP file
    zip_filename = f"processed_{job_id}.zip"
    zip_path = storage.processed_dir / job_id / zip_filename
    
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="ZIP file not found")
    
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=zip_filename
    )

