"""Enhanced batch processing manager with intelligent processor selection."""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from app.processing.processor_selector import (
    get_processor_selector,
    ProcessorType,
    process_with_optimal_selection
)
from app.processing.image_utils import validate_image
from app.storage.local_storage import LocalStorage
from app.api.jobs import job_manager
from app.logging import log_image_processing
from app.utils.filename_parser import parse_filename
import time


class EnhancedBatchProcessor:
    """Enhanced batch processing with intelligent processor selection and optimization."""

    def __init__(self, batch_size: int = 500, max_concurrent: int = 10, priority: str = "balanced"):
        """
        Initialize enhanced batch processor.

        Args:
            batch_size: Number of images to process per batch
            max_concurrent: Maximum concurrent requests
            priority: Processing priority ('speed', 'quality', 'cost', 'balanced')
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.priority = priority
        self.storage = LocalStorage()
        self.processor_selector = get_processor_selector()

    def get_processing_recommendations(self, num_images: int) -> Dict:
        """Get processor recommendations for the batch."""
        return self.processor_selector.get_recommendations_for_batch(num_images)
    
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
                    
                    # Process image with intelligent processor selection
                    start_time = time.time()
                    format_str = "PNG" if output_format.upper() == "PNG" else "JPEG"

                    # Set processing requirements
                    requirements = {
                        'priority': self.priority,
                        'batch_size': len(image_data_list),
                        'budget_limit': 0.05 if self.priority != 'cost' else 0.01
                    }

                    # Run in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    processed_buffer = await loop.run_in_executor(
                        None,
                        lambda: process_with_optimal_selection(
                            file_bytes,
                            requirements,
                            output_format=format_str,
                            white_background=white_background,
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
                    symbol_number = parsed.symbol_number if parsed.is_valid else None
                    
                    file_path = self.storage.save_processed(
                        processed_buffer.read(),
                        processed_filename,
                        job_id,
                        symbol_number=symbol_number
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
                preserve_structure=True  # Keep symbol_number folders
            )
            job_manager.add_processed_file(job_id, zip_path)
        
        # Mark job as completed
        job_manager.complete_job(job_id, success=len(all_processed_files) > 0)


# Keep original class for backwards compatibility
class BatchProcessor(EnhancedBatchProcessor):
    """Backwards compatible batch processor."""

    def __init__(self, batch_size: int = 500, max_concurrent: int = 10):
        super().__init__(batch_size, max_concurrent, priority="balanced")


def create_optimized_processor_for_large_dataset(num_images: int) -> EnhancedBatchProcessor:
    """Create an optimized processor for large datasets (20k+ images)."""

    # Get recommendations
    temp_processor = EnhancedBatchProcessor()
    recommendations = temp_processor.get_processing_recommendations(num_images)

    print(f"🎯 Processing {num_images:,} images - Recommendations:")
    for priority, rec in recommendations.items():
        cost = rec['cost_estimate']['total_cost_usd']
        time_hours = rec['cost_estimate']['estimated_time_hours']
        print(f"  {priority}: {rec['processor']} - ${cost:.2f}, {time_hours:.1f}h")

    # For large datasets, prioritize cost efficiency
    optimal_priority = "cost" if num_images > 5000 else "balanced"

    # Auto-select batch size based on dataset size
    if num_images > 10000:
        batch_size = 1000  # Large batches for efficiency
        max_concurrent = 20
    elif num_images > 1000:
        batch_size = 500
        max_concurrent = 15
    else:
        batch_size = 100
        max_concurrent = 10

    processor = EnhancedBatchProcessor(
        batch_size=batch_size,
        max_concurrent=max_concurrent,
        priority=optimal_priority
    )

    print(f"🚀 Created optimized processor: batch_size={batch_size}, "
          f"priority={optimal_priority}, concurrent={max_concurrent}")

    return processor

