"""API routes for image processing."""
import os
import time
import zipfile
import asyncio
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from app.models import PartInfo, ProcessPartResponse, JobResponse, JobStatus, JobStatusResponse
from app.processing.picwish_processor import process_image, check_api_available
from app.processing.image_utils import validate_image
from app.processing.batch_manager import BatchProcessor
from app.storage.local_storage import LocalStorage
from app.api.jobs import job_manager
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


@router.get("/parts/{part_number}", response_model=PartInfo)
async def get_part_info(part_number: str):
    """
    Get part information from Google Sheets.
    
    Used for autocomplete/search in frontend.
    """
    from app.services.google_sheets import get_sheets_service
    
    sheets_service = get_sheets_service()
    if not sheets_service:
        raise HTTPException(
            status_code=503,
            detail="Google Sheets service not configured. Check GOOGLE_CLOUD_SETUP.md"
        )
    
    part_info = sheets_service.get_part_info(part_number)
    if not part_info:
        raise HTTPException(
            status_code=404,
            detail=f"Part number '{part_number}' not found in Google Sheet"
        )
    
    return PartInfo(**part_info)


@router.get("/parts/search")
async def search_parts(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results")
):
    """
    Search parts by part number (for autocomplete).
    
    Returns matching parts from Google Sheets.
    """
    from app.services.google_sheets import get_sheets_service
    
    sheets_service = get_sheets_service()
    if not sheets_service:
        raise HTTPException(
            status_code=503,
            detail="Google Sheets service not configured. Check GOOGLE_CLOUD_SETUP.md"
        )
    
    results = sheets_service.search_parts(q, limit=limit)
    return [PartInfo(**part) for part in results]


@router.post("/process/part", response_model=ProcessPartResponse)
async def process_part_images(
    files: List[UploadFile] = File(...),
    part_number: str = Query(..., min_length=1),
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
    2. Check for duplicates in Google Drive
    3. Process images with text overlay
    4. Save to Google Drive
    
    Supports variable number of images (1-10).
    """
    from app.services.google_sheets import get_sheets_service
    from app.services.google_drive_storage import get_drive_storage
    
    # Validate image count
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No images provided")
    
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed")
    
    # Try Excel service first, fallback to Google Sheets
    excel_service = get_excel_parts_service()
    part_info = None

    if excel_service.unique_parts is not None:
        # Use Excel catalog
        part_info = excel_service.get_part_info(part_number)
        if not part_info:
            raise HTTPException(
                status_code=404,
                detail=f"Part number '{part_number}' not found in Excel catalog"
            )
    else:
        # Fallback to Google Sheets
        from app.services.google_sheets import get_sheets_service
        sheets_service = get_sheets_service()
        if not sheets_service:
            raise HTTPException(
                status_code=503,
                detail="No Excel file loaded and Google Sheets not configured. Upload Excel file or check GOOGLE_CLOUD_SETUP.md"
            )

        part_info = sheets_service.get_part_info(part_number)
        if not part_info:
            raise HTTPException(
                status_code=404,
                detail=f"Part number '{part_number}' not found in Google Sheet"
            )
    
    description = part_info.get("description", "")
    location = part_info.get("location", "")
    item_note = part_info.get("item_note", "")
    
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
    
    # Check for duplicates in Google Drive
    drive_storage = get_drive_storage()
    if not drive_storage:
        raise HTTPException(
            status_code=503,
            detail="Google Drive service not configured. Check GOOGLE_CLOUD_SETUP.md"
        )
    
    duplicates = drive_storage.check_duplicates(part_number, view_nums)
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
                use_ecommerce_layout=True  # Enable e-commerce card layout
            )
            
            # Generate filename: PartNumber_ViewNumber_Description.jpg
            # Sanitize description for filename
            safe_description = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in description)
            safe_description = safe_description.replace(' ', '_')[:50]  # Limit length
            
            ext = ".jpg" if output_format.upper() in ["JPEG", "JPG"] else ".png"
            filename = f"{part_number}_{view_num}_{safe_description}{ext}"
            
            # Get processed bytes
            processed_bytes = processed_buffer.read()
            
            processed_files.append((filename, processed_bytes))
        
        # Save to local storage and Google Drive
        saved_files = []
        local_paths = []

        # Save locally first
        for filename, processed_bytes in processed_files:
            local_path = storage.save_processed_file(processed_bytes, filename, part_number)
            if local_path:
                local_paths.append(local_path)
                saved_files.append({"filename": filename, "url": f"/api/download/{filename}"})

        # Upload to Google Drive
        from app.services.google_drive import get_drive_service
        drive_service = get_drive_service()
        if drive_service.is_available() and local_paths:
            success = drive_service.upload_part_images(part_number, local_paths)
            if success:
                print(f"✓ Successfully uploaded {len(local_paths)} images to Google Drive for part {part_number}")
            else:
                print(f"⚠ Warning: Failed to upload some images to Google Drive for part {part_number}")

        # Mark part as processed in tracker
        tracker = get_parts_tracker()
        tracker.mark_part_processed(part_number, len(saved_files))

        return ProcessPartResponse(
            success=True,
            part_number=part_number,
            description=description,
            location=location,
            item_note=item_note if item_note else None,
            files_saved=len(saved_files),
            saved_paths=[{"filename": f["filename"], "url": f["url"]} for f in saved_files],
            message=f"Successfully processed and saved {len(saved_files)} images for part {part_number}"
        )
        
    except HTTPException:
        # Mark as failed in tracker for non-404 errors
        if "not found" not in str(e).lower():
            tracker = get_parts_tracker()
            tracker.mark_part_failed(part_number, str(e))
        raise
    except Exception as e:
        # Mark part as failed in tracker
        tracker = get_parts_tracker()
        tracker.mark_part_failed(part_number, str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/excel/upload")
async def upload_excel_file(file: UploadFile = File(...)):
    """
    Upload and process Excel parts catalog file.

    Replaces Google Sheets functionality with local Excel file processing.
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


@router.get("/excel/parts/{part_number}")
async def get_excel_part_info(part_number: str):
    """Get part information from Excel catalog."""
    excel_service = get_excel_parts_service()
    if excel_service.unique_parts is None:
        raise HTTPException(status_code=503, detail="No Excel file loaded. Upload an Excel file first.")

    part_info = excel_service.get_part_info(part_number)
    if not part_info:
        raise HTTPException(status_code=404, detail=f"Part number '{part_number}' not found in Excel catalog")

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


@router.get("/tracker/parts/{part_number}/status")
async def get_part_status(part_number: str):
    """Get detailed status of a specific part."""
    tracker = get_parts_tracker()
    status = tracker.get_part_status(part_number)

    if not status:
        # Check if part exists in Excel
        excel_service = get_excel_parts_service()
        if excel_service.unique_parts is not None:
            part_info = excel_service.get_part_info(part_number)
            if part_info:
                return {"part_number": part_number, "status": "pending", "exists": True}

        raise HTTPException(status_code=404, detail=f"Part number '{part_number}' not found")

    return {"part_number": part_number, **status}


@router.post("/tracker/parts/{part_number}/reset")
async def reset_part_status(part_number: str):
    """Reset status for a specific part (remove from processed/failed)."""
    tracker = get_parts_tracker()
    tracker.reset_part(part_number)

    return {"success": True, "message": f"Reset status for part {part_number}"}


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

