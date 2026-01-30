"""API routes for image processing."""
import os
import io
import time
import zipfile
import asyncio
import sqlite3
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from app.models import PartInfo, ProcessPartResponse, JobResponse, JobStatus, JobStatusResponse
from app.processing.rembg_processor import process_image
from app.processing.image_utils import validate_image
from app.processing.batch_manager import BatchProcessor
from app.storage.local_storage import LocalStorage
from app.api.jobs import job_manager
from app.services.cloudflare_r2 import get_r2_storage
from app.logging import log_image_processing, log_gpu_metrics
from app.utils.filename_parser import validate_batch_filenames
from app.services.excel_service import get_excel_parts_service
from app.services.parts_tracker import get_parts_tracker

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
    white_background: bool = Query(True),
    compression_quality: int = Query(85, ge=70, le=100),
    max_dimension: int = Query(2048, ge=800, le=4096)
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

    try:
        output_format = "PNG" if format.upper() == "PNG" else "JPEG"
        processed_buffer = process_image(
            file_bytes,
            output_format=output_format,
            white_background=white_background,
            compression_quality=compression_quality,
            max_dimension=max_dimension
        )
        
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
    white_background: bool = Query(True),
    compression_quality: int = Query(85, ge=70, le=100),
    max_dimension: int = Query(2048, ge=800, le=4096)
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
    
    # Validate filenames before processing
    filenames = [f.filename for f in image_files if f.filename]
    validation_results = validate_batch_filenames(filenames)
    
    # Create job
    job_id = job_manager.create_job(len(image_files))
    
    # Start async processing with compression settings
    asyncio.create_task(
        process_bulk_job(
            job_id, 
            image_files, 
            format, 
            white_background,
            compression_quality,
            max_dimension
        )
    )
    
    return JobResponse(
        job_id=job_id,
        status=JobStatus.PROCESSING,
        message=f"Processing {len(image_files)} images",
        validation_results=validation_results
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
    white_background: bool,
    compression_quality: int = 85,
    max_dimension: int = 2048
):
    """Process bulk images in background with batching support."""
    # Log processing start
    log_gpu_metrics(gpu_available=False)  # Enhanced REMBG processing
    
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
        
        # Process all images in batches with compression
        await batch_processor.process_in_batches(
            job_id,
            image_data_list,
            output_format,
            white_background,
            compression_quality,
            max_dimension
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


@router.get("/parts/{symbol_number}", response_model=PartInfo)
async def get_part_info(symbol_number: str):
    """
    Get part information from Excel catalog.

    Used for autocomplete/search in frontend.
    """
    excel_service = get_excel_parts_service()
    tracker = get_parts_tracker()

    if excel_service.unique_parts is None:
        raise HTTPException(
            status_code=503,
            detail="No Excel file loaded. Upload Excel file via /api/excel/upload"
        )

    # Check if part is already processed
    part_status = tracker.get_part_status(symbol_number)
    if part_status and part_status.get('status') == 'completed':
        raise HTTPException(
            status_code=409,
            detail=f"Symbol number '{symbol_number}' has already been processed"
        )

    part_info = excel_service.get_part_info(symbol_number)
    if not part_info:
        raise HTTPException(
            status_code=404,
            detail=f"Symbol number '{symbol_number}' not found in Excel catalog"
        )

    return PartInfo(**part_info)


@router.get("/parts/search")
async def search_parts(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results")
):
    """
    Search parts by part number (for autocomplete).

    Returns matching parts from Excel catalog.
    """
    excel_service = get_excel_parts_service()

    if excel_service.unique_parts is None:
        raise HTTPException(
            status_code=503,
            detail="No Excel file loaded. Upload Excel file via /api/excel/upload"
        )

    results = excel_service.search_parts(q, limit=limit)
    return [PartInfo(**part) for part in results]


@router.post("/process/part/async", response_model=JobResponse)
async def process_part_images_async(
    files: List[UploadFile] = File(...),
    symbol_number: str = Query(..., min_length=1),
    view_numbers: Optional[str] = Query(None, description="Comma-separated view numbers (e.g., '1,2,3')"),
    format: str = Query("PNG", regex="^(PNG|JPEG|JPG)$"),
    white_background: bool = Query(True),
    compression_quality: int = Query(85, ge=70, le=100),
    max_dimension: int = Query(2048, ge=800, le=4096),
    add_label: bool = Query(True),
    label_position: str = Query("bottom-left", regex="^(bottom-left|bottom-right|top-left|top-right|bottom-center)$")
):
    """
    Queue part images for background processing.
    Returns job ID immediately so users can continue with other parts.

    Background processing steps:
    1. Background removal using Enhanced REMBG (Kaggle)
    2. Add white background
    3. Add description label overlay
    4. Save to Cloudflare R2

    Supports variable number of images (1-10).
    """
    # Quick validation
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No images provided")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed")

    # Check if this part has already been processed or is in progress
    tracker = get_parts_tracker()
    if tracker.is_part_processed(symbol_number):
        raise HTTPException(
            status_code=409,
            detail=f"Part {symbol_number} has already been processed. Use the tracking dashboard to see results."
        )

    # Check if part is currently being processed (has active jobs)
    # Get recent jobs for this part number to prevent concurrent processing
    job_manager_instance = job_manager
    recent_jobs = []
    try:
        conn = sqlite3.connect(job_manager_instance.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status FROM jobs
            WHERE job_data LIKE ?
            AND status IN ('queued', 'processing')
            AND datetime(created_at) > datetime('now', '-1 hour')
        """, (f'%"symbol_number": "{symbol_number}"%',))
        recent_jobs = cursor.fetchall()
        conn.close()
    except Exception:
        pass  # If check fails, allow upload (fail-open)

    if recent_jobs:
        raise HTTPException(
            status_code=409,
            detail=f"Part {symbol_number} is currently being processed. Please wait for completion."
        )

    # Generate job ID first for R2 folder structure
    import uuid
    job_id = str(uuid.uuid4())

    # Upload raw images directly to R2 for reliability
    drive_storage = get_r2_storage()
    if not drive_storage:
        raise HTTPException(status_code=500, detail="Storage service unavailable")

    raw_file_paths = []
    for i, file in enumerate(files):
        content = await file.read()
        # Store in R2 under raw/{symbol_number}/ folder for better organization
        r2_key = f"raw/{symbol_number}/{job_id}_{i+1:02d}_{file.filename}"

        try:
            drive_storage.s3_client.put_object(
                Bucket=drive_storage.bucket_name,
                Key=r2_key,
                Body=content,
                ContentType=file.content_type or "image/jpeg"
            )
            raw_file_paths.append({
                "filename": file.filename,
                "r2_key": r2_key,
                "content_type": file.content_type
            })
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}: {str(e)}")

    # Create job metadata for R2 background worker
    job_metadata = {
        "job_id": job_id,
        "symbol_number": symbol_number,
        "raw_file_paths": raw_file_paths,
        "parameters": {
            "view_numbers": view_numbers,
            "format": format,
            "white_background": white_background,
            "compression_quality": compression_quality,
            "max_dimension": max_dimension,
            "add_label": add_label,
            "label_position": label_position
        },
        "status": "queued",
        "created_at": datetime.now().isoformat()
    }

    # Upload job metadata to R2 for worker to process
    try:
        job_key = f"jobs/queued/{job_id}.json"
        drive_storage.s3_client.put_object(
            Bucket=drive_storage.bucket_name,
            Key=job_key,
            Body=json.dumps(job_metadata, indent=2),
            ContentType="application/json"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue job: {str(e)}")

    return JobResponse(
        job_id=job_id,
        status="queued",
        message=f"Part {symbol_number} processing queued. Use /jobs/{job_id}/status to check progress."
    )


@router.post("/process/part", response_model=ProcessPartResponse)
async def process_part_images(
    files: List[UploadFile] = File(...),
    symbol_number: str = Query(..., min_length=1),
    view_numbers: Optional[str] = Query(None, description="Comma-separated view numbers (e.g., '1,2,3')"),
    format: str = Query("PNG", regex="^(PNG|JPEG|JPG)$"),
    white_background: bool = Query(True),
    compression_quality: int = Query(85, ge=70, le=100),
    max_dimension: int = Query(2048, ge=800, le=4096),
    add_label: bool = Query(True),
    label_position: str = Query("bottom-left", regex="^(bottom-left|bottom-right|top-left|top-right|bottom-center)$")
):
    """
    Process images for a part using simplified workflow.
    
    Flow:
    1. Lookup part in Google Sheets
    2. Check for duplicates in Cloudflare R2
    3. Process images with text overlay
    4. Save to Cloudflare R2
    
    Supports variable number of images (1-10).
    """
    from app.services.cloudflare_r2 import get_r2_storage

    # Validate image count
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No images provided")
    
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed")
    
    # Use Excel catalog only
    excel_service = get_excel_parts_service()

    if excel_service.unique_parts is None:
        raise HTTPException(
            status_code=503,
            detail="No Excel file loaded. Upload Excel file via /api/excel/upload"
        )

    part_info = excel_service.get_part_info(symbol_number)
    if not part_info:
        raise HTTPException(
            status_code=404,
            detail=f"Symbol number '{symbol_number}' not found in Excel catalog"
        )
    
    description = part_info.get("description", "")
    location = part_info.get("location", "")
    item_note = part_info.get("item_note", "")
    desc1 = part_info.get("description_1") or description
    desc2 = part_info.get("description_2") or ""
    long_desc = part_info.get("long_description") or (item_note or "")
    
    # Parse view numbers or auto-assign
    if view_numbers:
        try:
            view_nums = [int(v.strip()) for v in view_numbers.split(",")]
            if len(view_nums) != len(files):
                raise HTTPException(
                    status_code=400,
                    detail=f"Number of view numbers ({len(view_nums)}) must match number of images ({len(files)})"
                )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid view_numbers format. Use comma-separated integers.")
    else:
        # Auto-assign view numbers starting from 1
        view_nums = list(range(1, len(files) + 1))
    
    # Check for duplicates in Cloudflare R2
    drive_storage = get_r2_storage()
    if not drive_storage:
        raise HTTPException(
            status_code=503,
            detail="Cloudflare R2 not configured. Check R2 environment variables."
        )
    
    duplicates = drive_storage.check_duplicates(symbol_number, view_nums)
    duplicate_views = [v for v, exists in duplicates.items() if exists]
    
    if duplicate_views:
        raise HTTPException(
            status_code=409,
            detail=f"Images already exist for views: {duplicate_views}. Please use different view numbers or delete existing images."
        )
    
    # Process images
    processed_files = []
    
    try:
        for idx, file in enumerate(files):
            # Read file
            file_bytes = await file.read()
            
            # Validate image
            is_valid, error_msg = validate_image(file_bytes)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid image {idx+1}: {error_msg}")
            
            # Process image with text overlay
            view_num = view_nums[idx]
            output_format = "PNG" if format.upper() == "PNG" else "JPEG"
            
            processed_buffer = process_image(
                file_bytes,
                output_format=output_format,
                white_background=white_background,
                compression_quality=compression_quality,
                max_dimension=max_dimension,
                description=description if add_label else None,
                add_label=add_label,
                label_position=label_position,
                item_note=item_note if item_note else None,
                symbol_number=symbol_number,
                location=location,
                desc1=desc1,
                desc2=desc2,
                long_description=long_desc,
                use_ecommerce_layout=True  # Enable e-commerce card layout
            )
            
            # Generate filename: PartNumber_ViewNumber_Description.jpg
            # Sanitize description for filename
            safe_description = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in description)
            safe_description = safe_description.replace(' ', '_')[:50]  # Limit length
            
            ext = ".jpg" if output_format.upper() in ["JPEG", "JPG"] else ".png"
            filename = f"{symbol_number}_{view_num}_{safe_description}{ext}"
            
            # Get processed bytes
            processed_bytes = processed_buffer.read()
            
            processed_files.append((filename, processed_bytes))
        
        # Save directly to Cloudflare R2 (no local storage)
        drive_storage = get_r2_storage()
        if not drive_storage:
            raise HTTPException(
                status_code=503,
                detail="Cloudflare R2 not configured. Check R2 environment variables."
            )

        # Upload all files to Cloudflare R2
        try:
            saved_files = drive_storage.save_part_images(
                symbol_number=symbol_number,
                image_files=processed_files,
                description=description
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload images to Cloudflare R2: {str(e)}"
            )

        # Mark part as processed in tracker
        tracker = get_parts_tracker()
        tracker.mark_part_processed(symbol_number, len(saved_files))

        return ProcessPartResponse(
            success=True,
            symbol_number=symbol_number,
            description=description,
            location=location,
            item_note=item_note if item_note else None,
            description_1=desc1,
            description_2=desc2,
            long_description=long_desc if long_desc else None,
            files_saved=len(saved_files),
            saved_paths=[{"filename": f.get("filename", ""), "url": f.get("url", "")} for f in saved_files],
            message=f"Successfully processed and saved {len(saved_files)} images for part {symbol_number}"
        )
        
    except HTTPException as e:
        # Mark as failed in tracker for non-404 errors
        if "not found" not in str(e).lower():
            tracker = get_parts_tracker()
            tracker.mark_part_failed(symbol_number, str(e))
        raise
    except Exception as e:
        # Mark part as failed in tracker
        tracker = get_parts_tracker()
        tracker.mark_part_failed(symbol_number, str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/excel/upload")
async def upload_excel_file(file: UploadFile = File(...)):
    """
    Upload and process Excel parts catalog file.

    Uses local Excel file processing and Cloudflare R2 storage.
    """
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")

    try:
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # Load into Excel service
        excel_service = get_excel_parts_service()
        success = excel_service.load_excel_file(temp_path, sheet_name="Data")

        if not success:
            raise HTTPException(status_code=400, detail="Failed to process Excel file")

        # Update parts tracker with total count
        tracker = get_parts_tracker()
        stats = excel_service.get_stats()
        tracker.set_total_parts(stats['total_parts'])

        # Clean up temp file
        os.unlink(temp_path)

        return {
            "success": True,
            "message": f"Excel file processed successfully",
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process Excel file: {str(e)}")


@router.get("/excel/parts/search")
async def search_excel_parts(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results")
):
    """Search parts from Excel catalog."""
    excel_service = get_excel_parts_service()
    if excel_service.unique_parts is None:
        raise HTTPException(status_code=503, detail="No Excel file loaded. Upload an Excel file first.")

    results = excel_service.search_parts(q, limit=limit)
    return results


@router.get("/excel/parts/{symbol_number}")
async def get_excel_part_info(symbol_number: str):
    """Get part information from Excel catalog."""
    excel_service = get_excel_parts_service()
    if excel_service.unique_parts is None:
        raise HTTPException(status_code=503, detail="No Excel file loaded. Upload an Excel file first.")

    part_info = excel_service.get_part_info(symbol_number)
    if not part_info:
        raise HTTPException(status_code=404, detail=f"Symbol number '{symbol_number}' not found in Excel catalog")

    return part_info


@router.get("/tracker/progress")
async def get_tracking_progress():
    """Get overall progress statistics for parts processing."""
    tracker = get_parts_tracker()
    stats = tracker.get_progress_stats()

    return {
        "progress": stats,
        "last_updated": tracker.tracker_file.stat().st_mtime if tracker.tracker_file.exists() else None
    }


@router.get("/tracker/parts/processed")
async def get_processed_parts():
    """Get list of successfully processed parts."""
    tracker = get_parts_tracker()
    processed_parts = tracker.get_processed_parts()

    return {
        "processed_parts": processed_parts,
        "count": len(processed_parts)
    }


@router.get("/tracker/parts/failed")
async def get_failed_parts():
    """Get list of failed parts with error reasons."""
    tracker = get_parts_tracker()
    failed_parts = tracker.get_failed_parts()

    return {
        "failed_parts": failed_parts,
        "count": len(failed_parts)
    }


@router.get("/tracker/parts/remaining")
async def get_remaining_parts():
    """Get list of parts that haven't been processed yet."""
    excel_service = get_excel_parts_service()
    tracker = get_parts_tracker()

    if excel_service.unique_parts is None:
        raise HTTPException(status_code=503, detail="No Excel file loaded. Upload an Excel file first.")

    # Get all part numbers from Excel
    all_parts = excel_service.unique_parts['Symbol Number'].astype(str).tolist()
    remaining_parts = tracker.get_remaining_parts(all_parts)

    return {
        "remaining_parts": remaining_parts[:100],  # Limit to first 100
        "total_remaining": len(remaining_parts)
    }


@router.get("/tracker/parts/{symbol_number}/status")
async def get_part_status(symbol_number: str):
    """Get detailed status of a specific part."""
    tracker = get_parts_tracker()
    status = tracker.get_part_status(symbol_number)

    if not status:
        # Check if part exists in Excel
        excel_service = get_excel_parts_service()
        if excel_service.unique_parts is not None:
            part_info = excel_service.get_part_info(symbol_number)
            if part_info:
                return {"symbol_number": symbol_number, "status": "pending", "exists": True}

        raise HTTPException(status_code=404, detail=f"Symbol number '{symbol_number}' not found")

    return {"symbol_number": symbol_number, **status}


@router.post("/tracker/parts/{symbol_number}/reset")
async def reset_part_status(symbol_number: str):
    """Reset status for a specific part (remove from processed/failed)."""
    tracker = get_parts_tracker()
    tracker.reset_part(symbol_number)

    return {"success": True, "message": f"Reset status for part {symbol_number}"}


@router.get("/tracker/report")
async def get_tracking_report():
    """Get detailed progress report."""
    tracker = get_parts_tracker()
    report_content = tracker.export_report()

    return {
        "report": report_content,
        "stats": tracker.get_progress_stats()
    }


@router.post("/tracker/reset")
async def reset_all_tracking():
    """Reset all tracking data. Use with caution!"""
    tracker = get_parts_tracker()
    tracker.reset_all()

    return {"success": True, "message": "All tracking data has been reset"}


@router.get("/debug/env")
async def debug_environment():
    """Debug endpoint to check environment variables."""
    from app.services.cloudflare_r2 import get_r2_storage

    env_vars = {
        "CLOUDFLARE_ACCOUNT_ID": os.getenv("CLOUDFLARE_ACCOUNT_ID"),
        "CLOUDFLARE_ACCESS_KEY_ID": os.getenv("CLOUDFLARE_ACCESS_KEY_ID"),
        "CLOUDFLARE_SECRET_ACCESS_KEY": os.getenv("CLOUDFLARE_SECRET_ACCESS_KEY"),
        "CLOUDFLARE_BUCKET_NAME": os.getenv("CLOUDFLARE_BUCKET_NAME"),
        "KAGGLE_USERNAME": os.getenv("KAGGLE_USERNAME")
    }

    # Test R2 service initialization
    r2_status = "failed"
    r2_error = None
    r2_stats = None
    try:
        r2_storage = get_r2_storage()
        if r2_storage:
            r2_status = "success"
            r2_stats = r2_storage.get_storage_stats()
        else:
            r2_status = "failed"
    except Exception as e:
        r2_error = str(e)

    return {
        "environment_variables": env_vars,
        "r2_service_status": r2_status,
        "r2_error": r2_error,
        "r2_storage_stats": r2_stats
    }


@router.get("/r2/download-all")
async def download_all_r2_files(
    prefix: Optional[str] = Query(None, description="Optional prefix filter (e.g., 'parts/' to download only processed images)"),
    include_raw: bool = Query(False, description="Include raw uploaded images")
):
    """
    Download all files from Cloudflare R2 bucket as a ZIP archive.
    
    Options:
    - prefix: Filter by prefix (e.g., 'parts/' for processed images only)
    - include_raw: Include raw uploaded images (default: False, only processed images)
    """
    r2_storage = get_r2_storage()
    if not r2_storage:
        raise HTTPException(
            status_code=503,
            detail="Cloudflare R2 not configured. Check R2 environment variables."
        )

    try:
        # Determine prefix
        if prefix:
            search_prefix = prefix
        elif include_raw:
            search_prefix = ""  # Download everything
        else:
            search_prefix = "parts/"  # Default: only processed images

        # List all objects
        all_objects = []
        paginator = r2_storage.s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=r2_storage.bucket_name, Prefix=search_prefix):
            if 'Contents' in page:
                all_objects.extend(page['Contents'])

        if not all_objects:
            raise HTTPException(
                status_code=404,
                detail=f"No files found with prefix '{search_prefix}'"
            )

        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for obj in all_objects:
                s3_key = obj['Key']
                
                # Skip job metadata JSON files
                if s3_key.endswith('.json') and 'jobs/' in s3_key:
                    continue
                
                try:
                    # Download file from R2
                    response = r2_storage.s3_client.get_object(
                        Bucket=r2_storage.bucket_name,
                        Key=s3_key
                    )
                    file_content = response['Body'].read()
                    
                    # Add to ZIP (preserve folder structure)
                    zip_file.writestr(s3_key, file_content)
                    
                except Exception as e:
                    print(f"⚠ Warning: Failed to download {s3_key}: {e}")
                    continue

        zip_buffer.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix_name = search_prefix.replace('/', '_').rstrip('_') if search_prefix else 'all'
        zip_filename = f"r2_backup_{prefix_name}_{timestamp}.zip"

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_filename}"',
                "Content-Length": str(zip_buffer.getbuffer().nbytes)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create download archive: {str(e)}"
        )

