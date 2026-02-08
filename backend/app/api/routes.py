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
from app.processing.lightweight_processor import process_image
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

    if excel_service.unique_parts is None:
        raise HTTPException(
            status_code=503,
            detail="No Excel file loaded. Upload Excel file via /api/excel/upload"
        )

    # Check R2 storage for existing images (both raw and processed)
    drive_storage = get_r2_storage()
    if drive_storage:
        try:
            # Check for processed images in parts/ folder
            parts_prefix = f"parts/{symbol_number}/"
            parts_response = drive_storage.s3_client.list_objects_v2(
                Bucket=drive_storage.bucket_name,
                Prefix=parts_prefix,
                MaxKeys=1
            )
            if 'Contents' in parts_response and len(parts_response['Contents']) > 0:
                raise HTTPException(
                    status_code=409,
                    detail=f"Symbol number '{symbol_number}' has already been processed. Processed images exist in storage."
                )
            
            # Check for raw images in raw/ folder (uploaded but not yet processed)
            raw_prefix = f"raw/{symbol_number}/"
            raw_response = drive_storage.s3_client.list_objects_v2(
                Bucket=drive_storage.bucket_name,
                Prefix=raw_prefix,
                MaxKeys=1
            )
            if 'Contents' in raw_response and len(raw_response['Contents']) > 0:
                raise HTTPException(
                    status_code=409,
                    detail=f"Symbol number '{symbol_number}' has already been uploaded and is queued for processing. Please check the tracking dashboard."
                )
        except drive_storage.s3_client.exceptions.NoSuchKey:
            pass  # No existing images, OK to proceed
        except HTTPException:
            raise  # Re-raise our 409 error
        except Exception as e:
            # Log but don't block if check fails
            print(f"⚠️  Could not check R2 for duplicates: {e}")

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
    Returns immediately so users can continue with other parts.

    Background processing steps:
    1. Upload images to R2
    2. Add to daily batch job
    3. Process at 7 PM daily
    """
    # Quick validation
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No images provided")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed")

    # Check R2 storage for existing images (both raw and processed)
    drive_storage = get_r2_storage()
    if drive_storage:
        try:
            # Check for processed images in parts/ folder
            parts_prefix = f"parts/{symbol_number}/"
            parts_response = drive_storage.s3_client.list_objects_v2(
                Bucket=drive_storage.bucket_name,
                Prefix=parts_prefix,
                MaxKeys=1
            )
            if 'Contents' in parts_response and len(parts_response['Contents']) > 0:
                raise HTTPException(
                    status_code=409,
                    detail=f"Part {symbol_number} already has processed images in storage. Please use a different symbol number or delete existing images first."
                )
            
            # Check for raw images in raw/ folder (uploaded but not yet processed)
            raw_prefix = f"raw/{symbol_number}/"
            raw_response = drive_storage.s3_client.list_objects_v2(
                Bucket=drive_storage.bucket_name,
                Prefix=raw_prefix,
                MaxKeys=1
            )
            if 'Contents' in raw_response and len(raw_response['Contents']) > 0:
                raise HTTPException(
                    status_code=409,
                    detail=f"Part {symbol_number} has already been uploaded and is queued for processing. Please check the tracking dashboard or wait for processing to complete."
                )
        except drive_storage.s3_client.exceptions.NoSuchKey:
            pass  # No existing images, OK to proceed
        except HTTPException:
            raise  # Re-raise our 409 error
        except Exception as e:
            # Log but don't block upload if check fails
            print(f"⚠️  Could not check for duplicates: {e}")

    # Get part info from Excel catalog
    excel_service = get_excel_parts_service()
    part_info = excel_service.get_part_info(symbol_number)
    if not part_info:
        raise HTTPException(
            status_code=404,
            detail=f"Symbol number '{symbol_number}' not found in Excel catalog"
        )

    # Extract part info for job metadata
    description = part_info.get("description", "")
    desc1 = part_info.get("desc1", "")
    desc2 = part_info.get("desc2", "")
    long_desc = part_info.get("long_text_desc", "")
    item_note = part_info.get("item_note", "")
    location = part_info.get("location", "")

    # Read files into memory (fast, happens before return)
    file_data = []
    for file in files:
        content = await file.read()
        file_data.append({
            'content': content,
            'filename': file.filename,
            'content_type': file.content_type
        })

    # Mark part as queued in tracker (for dashboard visibility)
    tracker = get_parts_tracker()
    tracker.mark_part_queued(symbol_number, len(file_data))

    # Use daily batch job ID
    from datetime import datetime
    job_id = f"job_daily_{datetime.now().strftime('%Y%m%d')}"

    # Start background upload task (don't wait for it)
    import asyncio
    asyncio.create_task(
        upload_to_daily_job_background(
            job_id=job_id,
            symbol_number=symbol_number,
            file_data=file_data,
            description=description,
            desc1=desc1,
            desc2=desc2,
            long_desc=long_desc,
            item_note=item_note,
            location=location,
            view_numbers=view_numbers,
            format=format,
            white_background=white_background,
            compression_quality=compression_quality,
            max_dimension=max_dimension,
            add_label=add_label,
            label_position=label_position
        )
    )

    # Return immediately - user can continue to next part
    return JobResponse(
        job_id=job_id,
        status="queued",
        message=f"Part {symbol_number} queued for processing. Upload continuing in background. You can add more parts now!"
    )


async def upload_to_daily_job_background(
    job_id: str,
    symbol_number: str,
    file_data: list,
    description: str,
    desc1: str,
    desc2: str,
    long_desc: str,
    item_note: str,
    location: str,
    view_numbers: Optional[str],
    format: str,
    white_background: bool,
    compression_quality: int,
    max_dimension: int,
    add_label: bool,
    label_position: str
):
    """Background task to upload images and update daily job."""
    try:
        from datetime import datetime
        import json # Added import for json
        
        # Upload raw images directly to R2 for reliability
        drive_storage = get_r2_storage()
        if not drive_storage:
            print(f"❌ Storage unavailable for {symbol_number}")
            return

        raw_file_paths = []
        timestamp = datetime.now().strftime('%H%M%S')
        
        for i, file_info in enumerate(file_data):
            # Store in R2 under raw/{symbol_number}/ folder
            r2_key = f"raw/{symbol_number}/{job_id}_{timestamp}_{i+1:02d}_{file_info['filename']}"

            try:
                drive_storage.s3_client.put_object(
                    Bucket=drive_storage.bucket_name,
                    Key=r2_key,
                    Body=file_info['content'],
                    ContentType=file_info['content_type'] or "image/jpeg"
                )
                raw_file_paths.append({
                    "filename": file_info['filename'],
                    "r2_key": r2_key,
                    "content_type": file_info['content_type']
                })
                print(f"✅ Uploaded {file_info['filename']} for {symbol_number}")
            except Exception as e:
                print(f"❌ Failed to upload {file_info['filename']}: {e}")

        if not raw_file_paths:
            print(f"❌ No files uploaded for {symbol_number}")
            return

        # Create new part entry
        new_part = {
            "symbol_number": symbol_number,
            "raw_file_paths": raw_file_paths,
            "uploaded_at": datetime.now().isoformat()
        }

        # Try to load existing daily job or create new one
        job_key = f"jobs/queued/{job_id}.json"
        try:
            # Try to get existing job
            response = drive_storage.s3_client.get_object(
                Bucket=drive_storage.bucket_name,
                Key=job_key
            )
            job_metadata = json.loads(response['Body'].read().decode('utf-8'))
            
            # Add new part to existing job
            if 'parts' not in job_metadata:
                job_metadata['parts'] = []
            job_metadata['parts'].append(new_part)
            job_metadata['updated_at'] = datetime.now().isoformat()
            
        except drive_storage.s3_client.exceptions.NoSuchKey:
            # Create new daily job
            job_metadata = {
                "job_id": job_id,
                "status": "queued",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "parts": [new_part]
            }
        except Exception as e:
            print(f"❌ Failed to load job: {e}")
            return

        # Upload updated job metadata to R2
        try:
            drive_storage.s3_client.put_object(
                Bucket=drive_storage.bucket_name,
                Key=job_key,
                Body=json.dumps(job_metadata, indent=2),
                ContentType="application/json"
            )
            print(f"✅ Added {symbol_number} to daily job {job_id}")
        except Exception as e:
            print(f"❌ Failed to update job: {e}")
            
    except Exception as e:
        print(f"❌ Background upload failed for {symbol_number}: {e}")


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
        # Sheet name varies across workbooks; excel_service auto-selects the best sheet
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
        "part_stats": tracker.part_stats,  # Include detailed part stats for timestamp tracking
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


@router.get("/tracker/parts/queued")
async def get_queued_parts():
    """Get list of parts that are queued for processing."""
    tracker = get_parts_tracker()
    queued_parts = tracker.get_queued_parts()

    return {
        "queued_parts": queued_parts,
        "count": len(queued_parts)
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


@router.post("/jobs/complete")
async def job_completion_webhook(
    job_id: str = Query(...),
    status: str = Query(...),
    processor: str = Query(default="unknown"),
    processed_count: int = Query(default=0)
):
    """
    Webhook endpoint for GitHub Actions to notify when job processing completes.
    
    This updates the parts tracker based on completed jobs.
    """
    try:
        tracker = get_parts_tracker()
        r2_storage = get_r2_storage()
        
        if not r2_storage:
            raise HTTPException(status_code=503, detail="R2 storage not available")
        
        # Get job metadata from R2
        try:
            job_response = r2_storage.s3_client.get_object(
                Bucket=r2_storage.bucket_name,
                Key=f"jobs/completed/{job_id}.json"
            )
            job_data = json.loads(job_response['Body'].read().decode('utf-8'))
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found: {e}")
        
        # Extract parts from job data
        parts = job_data.get('parts', [])
        
        # If old format (single part), convert to list
        if not parts and 'symbol_number' in job_data:
            parts = [{'symbol_number': job_data['symbol_number']}]
        
        # Update tracker for each part
        updated_parts = []
        for part in parts:
            symbol_number = part.get('symbol_number')
            if not symbol_number:
                continue
            
            # Check if part was successfully processed (has files in R2)
            parts_prefix = f"parts/{symbol_number}/"
            try:
                parts_response = r2_storage.s3_client.list_objects_v2(
                    Bucket=r2_storage.bucket_name,
                    Prefix=parts_prefix,
                    MaxKeys=1
                )
                
                if 'Contents' in parts_response and len(parts_response['Contents']) > 0:
                    # Part was successfully processed
                    # Count total images
                    all_images_response = r2_storage.s3_client.list_objects_v2(
                        Bucket=r2_storage.bucket_name,
                        Prefix=parts_prefix
                    )
                    image_count = len(all_images_response.get('Contents', []))
                    
                    # Mark as processed
                    tracker.mark_part_processed(symbol_number, image_count)
                    updated_parts.append(symbol_number)
                else:
                    # No processed images found, mark as failed
                    tracker.mark_part_failed(symbol_number, "No processed images found in R2")
                    
            except Exception as e:
                tracker.mark_part_failed(symbol_number, f"Error checking R2: {str(e)}")
        
        return {
            "success": True,
            "job_id": job_id,
            "updated_parts": updated_parts,
            "message": f"Updated tracker for {len(updated_parts)} parts"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")


@router.post("/tracker/sync-from-r2")
async def sync_tracker_from_r2():
    """
    Sync tracker with actual R2 storage state.
    
    This scans R2 storage and updates the tracker to match reality:
    - Parts in parts/ folder → marked as processed
    - Parts in raw/ folder only → marked as queued
    - Parts in neither → remain as pending
    """
    try:
        tracker = get_parts_tracker()
        r2_storage = get_r2_storage()
        excel_service = get_excel_parts_service()
        
        if not r2_storage:
            raise HTTPException(status_code=503, detail="R2 storage not available")
        
        if excel_service.unique_parts is None:
            raise HTTPException(status_code=503, detail="No Excel file loaded")
        
        # Get all parts from Excel
        all_parts = excel_service.unique_parts['Symbol Number'].astype(str).tolist()
        
        # Scan R2 for processed parts (parts/ folder)
        processed_parts = set()
        queued_parts = set()
        
        print("🔄 Scanning R2 storage...")
        
        # Check processed parts
        paginator = r2_storage.s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=r2_storage.bucket_name, Prefix='parts/'):
            for obj in page.get('Contents', []):
                key = obj['Key']
                # Extract symbol number from path: parts/SYMBOL/filename
                parts_path = key.split('/')
                if len(parts_path) >= 2:
                    symbol_number = parts_path[1]
                    processed_parts.add(symbol_number)
        
        # Check queued parts (raw/ folder)
        for page in paginator.paginate(Bucket=r2_storage.bucket_name, Prefix='raw/'):
            for obj in page.get('Contents', []):
                key = obj['Key']
                # Extract symbol number from path: raw/SYMBOL/filename
                parts_path = key.split('/')
                if len(parts_path) >= 2:
                    symbol_number = parts_path[1]
                    # Only mark as queued if not already processed
                    if symbol_number not in processed_parts:
                        queued_parts.add(symbol_number)
        
        # Update tracker
        print(f"📊 Found {len(processed_parts)} processed, {len(queued_parts)} queued")
        
        # Preserve existing stats timestamps where possible
        preserved_stats = {}
        for symbol_number in processed_parts:
            if symbol_number in tracker.part_stats:
                old_stats = tracker.part_stats[symbol_number]
                # Preserve completed_at if it exists
                if old_stats.get('status') == 'completed' and old_stats.get('completed_at'):
                    preserved_stats[symbol_number] = old_stats
        
        # Clear current tracker state
        tracker.processed_parts.clear()
        tracker.queued_parts.clear()
        tracker.failed_parts.clear()
        tracker.part_stats.clear()
        
        # Add processed parts (remove from queued automatically via mark_part_processed)
        for symbol_number in processed_parts:
            # Count images for this part
            prefix = f"parts/{symbol_number}/"
            response = r2_storage.s3_client.list_objects_v2(
                Bucket=r2_storage.bucket_name,
                Prefix=prefix
            )
            image_count = len(response.get('Contents', []))
            
            # Preserve completed_at timestamp if available
            if symbol_number in preserved_stats:
                old_stats = preserved_stats[symbol_number]
                tracker.mark_part_processed(symbol_number, image_count)
                # Restore timestamp
                if symbol_number in tracker.part_stats:
                    tracker.part_stats[symbol_number]['completed_at'] = old_stats['completed_at']
            else:
                tracker.mark_part_processed(symbol_number, image_count)
        
        # Add queued parts (only if not already processed)
        for symbol_number in queued_parts:
            if symbol_number not in processed_parts:
                # Count raw images
                prefix = f"raw/{symbol_number}/"
                response = r2_storage.s3_client.list_objects_v2(
                    Bucket=r2_storage.bucket_name,
                    Prefix=prefix
                )
                image_count = len(response.get('Contents', []))
                tracker.mark_part_queued(symbol_number, image_count)
        
        # Save tracker
        tracker.save_tracker()
        
        # Get updated stats
        stats = tracker.get_progress_stats()
        
        return {
            "success": True,
            "message": "Tracker synced with R2 storage",
            "stats": stats,
            "processed_parts_count": len(processed_parts),
            "queued_parts_count": len(queued_parts)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync tracker: {str(e)}")
