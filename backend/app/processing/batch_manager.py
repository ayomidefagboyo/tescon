"""Batch processing manager for large volume processing."""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from app.processing.picwish_processor import process_image
from app.processing.image_utils import validate_image
from app.storage.local_storage import LocalStorage
from app.api.jobs import job_manager
from app.logging import log_image_processing
from app.utils.filename_parser import parse_filename
import time


class BatchProcessor:
    """Manages batch processing of images with configurable batch size."""
    
    def __init__(self, batch_size: int = 500, max_concurrent: int = 10):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of images to process per batch
            max_concurrent: Maximum concurrent API requests
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.storage = LocalStorage()
    
    async def process_batch(
        self,
        job_id: str,
        image_data_list: List[Dict],
        output_format: str,
        white_background: bool,
        compression_quality: int = 85,
        max_dimension: int = 2048
    ) -> tuple[List[str], int]:
        """
        Process a batch of images with concurrency control.
        
        Args:
            job_id: Job ID
            image_data_list: List of dicts with 'bytes' and 'filename'
            output_format: Output format
            white_background: Whether to add white background
            
        Returns:
            Tuple of (processed_file_paths, failed_count)
        """
        processed_files = []
        failed_count = 0
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_single(image_data: Dict) -> Optional[str]:
            """Process a single image with concurrency control."""
            async with semaphore:
                filename = image_data.get('filename', 'unknown')
                file_bytes = image_data.get('bytes')
                
                if not file_bytes:
                    return None
                
                try:
                    # Validate image
                    is_valid, error_msg = validate_image(file_bytes)
                    if not is_valid:
                        job_manager.add_failed_image(job_id, filename, error_msg)
                        log_image_processing(
                            image_filename=filename,
                            job_id=job_id,
                            success=False,
                            error=error_msg
                        )
                        return None
                    
                    # Parse filename to get part number
                    parsed = parse_filename(filename)
                    
                    # Process image
                    start_time = time.time()
                    format_str = "PNG" if output_format.upper() == "PNG" else "JPEG"
                    
                    # Run in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    processed_buffer = await loop.run_in_executor(
                        None,
                        lambda: process_image(
                            file_bytes, 
                            format_str, 
                            white_background,
                            compression_quality=compression_quality,
                            max_dimension=max_dimension
                        )
                    )
                    
                    processing_time_ms = (time.time() - start_time) * 1000
                    
                    # Save processed image organized by part number
                    original_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                    ext = ".png" if format_str == "PNG" else ".jpg"
                    processed_filename = f"{original_name}{ext}"
                    
                    # Save with part number organization if filename is valid
                    part_number = parsed.part_number if parsed.is_valid else None
                    
                    file_path = self.storage.save_processed(
                        processed_buffer.read(),
                        processed_filename,
                        job_id,
                        part_number=part_number
                    )
                    
                    # Log success
                    log_image_processing(
                        image_filename=filename,
                        job_id=job_id,
                        gpu_used=False,
                        processing_time_ms=processing_time_ms,
                        image_size_bytes=len(file_bytes),
                        success=True
                    )
                    
                    return file_path
                    
                except Exception as e:
                    error_msg = str(e)
                    job_manager.add_failed_image(job_id, filename, error_msg)
                    log_image_processing(
                        image_filename=filename,
                        job_id=job_id,
                        success=False,
                        error=error_msg
                    )
                    return None
        
        # Process all images concurrently (with semaphore limit)
        tasks = [process_single(img_data) for img_data in image_data_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful results
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
            elif result:
                processed_files.append(result)
            else:
                failed_count += 1
        
        return processed_files, failed_count
    
    async def process_in_batches(
        self,
        job_id: str,
        all_image_data: List[Dict],
        output_format: str,
        white_background: bool,
        compression_quality: int = 85,
        max_dimension: int = 2048
    ):
        """
        Process all images in batches.
        
        Args:
            job_id: Job ID
            all_image_data: List of all image data dicts
            output_format: Output format
            white_background: Whether to add white background
        """
        total_images = len(all_image_data)
        all_processed_files = []
        total_failed = 0
        
        # Process in batches
        for i in range(0, total_images, self.batch_size):
            batch = all_image_data[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_images + self.batch_size - 1) // self.batch_size
            
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} images)")
            
            processed_files, failed_count = await self.process_batch(
                job_id,
                batch,
                output_format,
                white_background,
                compression_quality,
                max_dimension
            )
            
            all_processed_files.extend(processed_files)
            total_failed += failed_count
            
            # Update job progress
            job_manager.update_job_progress(
                job_id,
                len(all_processed_files),
                total_failed
            )
        
        # Create ZIP with SharePoint-ready folder structure
        if all_processed_files:
            zip_filename = f"processed_{job_id}.zip"
            zip_path = self.storage.create_zip(
                all_processed_files, 
                zip_filename, 
                job_id,
                preserve_structure=True  # Keep part_number folders
            )
            job_manager.add_processed_file(job_id, zip_path)
        
        # Mark job as completed
        job_manager.complete_job(job_id, success=len(all_processed_files) > 0)

