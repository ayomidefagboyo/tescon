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
    
    def create_job(self, total_images: int) -> str:
        """Create a new job and return job ID."""
        job_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jobs (job_id, status, total_images, created_at)
            VALUES (?, ?, ?, ?)
        """, (job_id, JobStatus.PROCESSING, total_images, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return job_id
    
    def create_job(self, total_images: int) -> str:
        """Create a new job and return job ID."""
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": JobStatus.PROCESSING,
            "total_images": total_images,
            "processed_count": 0,
            "failed_count": 0,
            "failed_images": [],
            "error_messages": [],
            "processed_files": [],
            "created_at": datetime.now(),
            "completed_at": None
        }
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


# Global job manager instance
job_manager = JobManager()

