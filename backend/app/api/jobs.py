"""Job management for async bulk processing."""
import uuid
import json
import sqlite3
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from app.models import JobStatus


class JobManager:
    """Job manager with persistent storage (SQLite)."""
    
    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                total_images INTEGER NOT NULL,
                processed_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                failed_images TEXT,
                error_messages TEXT,
                processed_files TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def _serialize_list(self, items: List[str]) -> str:
        """Serialize list to JSON string."""
        return json.dumps(items) if items else "[]"
    
    def _deserialize_list(self, json_str: str) -> List[str]:
        """Deserialize JSON string to list."""
        if not json_str:
            return []
        try:
            return json.loads(json_str)
        except:
            return []
    
    def _dict_to_job(self, row: tuple) -> dict:
        """Convert database row to job dict."""
        return {
            "job_id": row[0],
            "status": row[1],
            "total_images": row[2],
            "processed_count": row[3],
            "failed_count": row[4],
            "failed_images": self._deserialize_list(row[5]),
            "error_messages": self._deserialize_list(row[6]),
            "processed_files": self._deserialize_list(row[7]),
            "created_at": datetime.fromisoformat(row[8]) if row[8] else None,
            "completed_at": datetime.fromisoformat(row[9]) if row[9] else None,
        }
    
    def create_job(self, total_images: int = None, job_type: str = "batch", **kwargs) -> str:
        """Create a new job and return job ID."""
        job_id = str(uuid.uuid4())

        # For part processing, total_images is the number of files
        if job_type == "process_part":
            total_images = len(kwargs.get("file_data", []))

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if table has job_type column, add if missing
        try:
            cursor.execute("SELECT job_type FROM jobs LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE jobs ADD COLUMN job_type TEXT DEFAULT 'batch'")
            cursor.execute("ALTER TABLE jobs ADD COLUMN job_data TEXT")

        # Store job data as JSON for process_part jobs
        job_data = None
        if job_type == "process_part":
            job_data = json.dumps({
                "part_number": kwargs.get("part_number"),
                "file_data": kwargs.get("file_data"),
                "parameters": kwargs.get("parameters")
            })

        cursor.execute("""
            INSERT INTO jobs (job_id, status, total_images, job_type, job_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (job_id, JobStatus.QUEUED, total_images, job_type, job_data, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        # Start processing the job in background
        if job_type == "process_part":
            asyncio.create_task(self._process_part_job(job_id))
        return job_id
    
    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._dict_to_job(row)
        return None
    
    def update_job_progress(self, job_id: str, processed_count: int, failed_count: int = 0):
        """Update job progress."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs 
            SET processed_count = ?, failed_count = ?
            WHERE job_id = ?
        """, (processed_count, failed_count, job_id))
        conn.commit()
        conn.close()
    
    def add_processed_file(self, job_id: str, file_path: str):
        """Add processed file to job."""
        job = self.get_job(job_id)
        if job:
            processed_files = job["processed_files"]
            if file_path not in processed_files:
                processed_files.append(file_path)
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE jobs 
                    SET processed_files = ?
                    WHERE job_id = ?
                """, (self._serialize_list(processed_files), job_id))
                conn.commit()
                conn.close()
    
    def add_failed_image(self, job_id: str, filename: str, error: str):
        """Add failed image to job."""
        job = self.get_job(job_id)
        if job:
            failed_images = job["failed_images"]
            error_messages = job["error_messages"]
            
            if filename not in failed_images:
                failed_images.append(filename)
                error_messages.append(error)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE jobs 
                    SET failed_images = ?, error_messages = ?, failed_count = failed_count + 1
                    WHERE job_id = ?
                """, (self._serialize_list(failed_images), self._serialize_list(error_messages), job_id))
                conn.commit()
                conn.close()
    
    def complete_job(self, job_id: str, success: bool = True):
        """Mark job as completed or failed."""
        status = JobStatus.COMPLETED if success else JobStatus.FAILED
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs 
            SET status = ?, completed_at = ?
            WHERE job_id = ?
        """, (status, datetime.now().isoformat(), job_id))
        conn.commit()
        conn.close()
    
    def cleanup_old_jobs(self, days: int = 7):
        """Remove jobs older than specified days."""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM jobs 
            WHERE completed_at IS NOT NULL AND completed_at < ?
        """, (cutoff_iso,))
        conn.commit()
        conn.close()
    
    def pause_job(self, job_id: str):
        """Pause a running job."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs 
            SET status = 'paused'
            WHERE job_id = ? AND status = 'processing'
        """, (job_id,))
        conn.commit()
        conn.close()
    
    def resume_job(self, job_id: str):
        """Resume a paused job."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs 
            SET status = 'processing'
            WHERE job_id = ? AND status = 'paused'
        """, (job_id,))
        conn.commit()
        conn.close()
        return True

    async def _process_part_job(self, job_id: str):
        """Process a part job in the background."""
        try:
            # Update status to processing
            self.update_job_status(job_id, JobStatus.PROCESSING)

            # Get job data
            job = self.get_job(job_id)
            if not job or not job.get("job_data"):
                self.update_job_status(job_id, JobStatus.FAILED, "No job data found")
                return

            job_data = json.loads(job["job_data"])
            part_number = job_data["part_number"]
            file_data = job_data["file_data"]
            params = job_data["parameters"]

            # Import processing functions here to avoid circular imports
            from app.services.cloudflare_r2 import get_r2_storage
            from app.services.excel_service import get_excel_parts_service
            from app.processing.picwish_processor import process_image
            from app.processing.image_utils import validate_image
            from app.services.parts_tracker import get_parts_tracker

            # Get part info from Excel
            excel_service = get_excel_parts_service()
            if excel_service.unique_parts is None:
                self.update_job_status(job_id, JobStatus.FAILED, "Excel catalog not loaded")
                return

            part_info = excel_service.get_part_info(part_number)
            if not part_info:
                self.update_job_status(job_id, JobStatus.FAILED, f"Part {part_number} not found in catalog")
                return

            description = part_info.get("description", "")

            # Parse view numbers
            view_numbers = params.get("view_numbers")
            if view_numbers:
                view_nums = [int(v.strip()) for v in view_numbers.split(",")]
            else:
                view_nums = list(range(1, len(file_data) + 1))

            # Check R2 availability
            drive_storage = get_r2_storage()
            if not drive_storage:
                self.update_job_status(job_id, JobStatus.FAILED, "Cloudflare R2 not configured")
                return

            # Process each image
            processed_files = []
            processed_count = 0

            for idx, file_info in enumerate(file_data):
                try:
                    # Validate image
                    file_bytes = file_info["content"]
                    is_valid, error_msg = validate_image(file_bytes)
                    if not is_valid:
                        self.add_failed_image(job_id, f"Image {idx+1}: {error_msg}")
                        continue

                    # Process image
                    view_num = view_nums[idx] if idx < len(view_nums) else idx + 1
                    output_format = "PNG" if params.get("format", "PNG").upper() == "PNG" else "JPEG"

                    processed_buffer = process_image(
                        file_bytes,
                        output_format=output_format,
                        white_background=params.get("white_background", True),
                        compression_quality=params.get("compression_quality", 85),
                        max_dimension=params.get("max_dimension", 2048),
                        description=description if params.get("add_label", True) else None,
                        add_label=params.get("add_label", True),
                        label_position=params.get("label_position", "bottom-left"),
                        item_note=part_info.get("item_note"),
                        use_ecommerce_layout=True
                    )

                    # Generate filename
                    safe_description = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in description)
                    safe_description = safe_description.replace(' ', '_')[:50]
                    ext = ".jpg" if output_format.upper() in ["JPEG", "JPG"] else ".png"
                    filename = f"{part_number}_{view_num}_{safe_description}{ext}"

                    processed_bytes = processed_buffer.read()
                    processed_files.append((filename, processed_bytes))
                    processed_count += 1

                    # Update progress
                    self.update_job_progress(job_id, processed_count)

                except Exception as e:
                    self.add_failed_image(job_id, f"Image {idx+1} processing failed: {str(e)}")

            if not processed_files:
                self.update_job_status(job_id, JobStatus.FAILED, "No images processed successfully")
                return

            # Upload to Cloudflare R2
            try:
                saved_files = drive_storage.save_part_images(
                    part_number=part_number,
                    image_files=processed_files,
                    description=description
                )

                # Mark part as processed
                tracker = get_parts_tracker()
                tracker.mark_part_processed(part_number, len(saved_files))

                # Complete the job
                self.update_job_status(job_id, JobStatus.COMPLETED, f"Successfully processed {len(saved_files)} images")

            except Exception as e:
                self.update_job_status(job_id, JobStatus.FAILED, f"Cloudflare R2 upload failed: {str(e)}")

        except Exception as e:
            self.update_job_status(job_id, JobStatus.FAILED, f"Job processing failed: {str(e)}")


# Global job manager instance
job_manager = JobManager()

