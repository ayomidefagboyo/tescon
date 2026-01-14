"""Local filesystem storage operations."""
import os
import uuid
import zipfile
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime, timedelta


class LocalStorage:
    """Handle local filesystem storage operations."""
    
    def __init__(
        self,
        upload_dir: str = "uploads",
        processed_dir: str = "processed",
        cleanup_ttl_hours: int = 24
    ):
        """
        Initialize local storage.
        
        Args:
            upload_dir: Directory for uploaded files
            processed_dir: Directory for processed files
            cleanup_ttl_hours: Hours before files are cleaned up (0 = no cleanup)
        """
        self.upload_dir = Path(upload_dir)
        self.processed_dir = Path(processed_dir)
        self.cleanup_ttl_hours = cleanup_ttl_hours
        
        # Create directories if they don't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def save_upload(self, file_bytes: bytes, original_filename: str) -> str:
        """
        Save uploaded file.
        
        Args:
            file_bytes: File content bytes
            original_filename: Original filename
            
        Returns:
            Unique filename (UUID-based)
        """
        # Generate unique filename
        ext = Path(original_filename).suffix
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = self.upload_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        
        return unique_filename
    
    def get_upload_path(self, filename: str) -> Path:
        """Get full path to uploaded file."""
        return self.upload_dir / filename
    
    def save_processed(
        self, 
        file_bytes: bytes, 
        filename: str, 
        job_id: Optional[str] = None,
        part_number: Optional[str] = None
    ) -> str:
        """
        Save processed image organized by part number.
        
        Args:
            file_bytes: Processed image bytes
            filename: Filename (with extension)
            job_id: Optional job ID for organization
            part_number: Part number for folder organization
            
        Returns:
            Path to saved file (relative)
        """
        if job_id and part_number:
            # Organize by job_id/part_number/filename
            part_dir = self.processed_dir / job_id / part_number
            part_dir.mkdir(parents=True, exist_ok=True)
            file_path = part_dir / filename
        elif job_id:
            # Just job_id organization
            job_dir = self.processed_dir / job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            file_path = job_dir / filename
        else:
            file_path = self.processed_dir / filename
        
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        
        return str(file_path.relative_to(self.processed_dir))
    
    def create_zip(
        self, 
        file_paths: List[str], 
        output_filename: str, 
        job_id: Optional[str] = None,
        preserve_structure: bool = True
    ) -> str:
        """
        Create ZIP archive of processed images with SharePoint-ready structure.
        
        Args:
            file_paths: List of relative file paths to include
            output_filename: Output ZIP filename
            job_id: Optional job ID for organization
            preserve_structure: If True, preserve part_number folder structure
            
        Returns:
            Path to created ZIP file
        """
        if job_id:
            zip_path = self.processed_dir / job_id / output_filename
        else:
            zip_path = self.processed_dir / output_filename
        
        # Sort file paths: by part number (folder), then by filename
        def sort_key(file_path: str) -> tuple:
            """Sort key: (part_number, filename) for proper ordering."""
            path_parts = Path(file_path).parts
            if len(path_parts) >= 2:
                # Has part_number folder: (part_number, filename)
                return (path_parts[-2], path_parts[-1])
            else:
                # No folder: (empty, filename)
                return ("", Path(file_path).name)
        
        sorted_file_paths = sorted(file_paths, key=sort_key)
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in sorted_file_paths:
                full_path = self.processed_dir / file_path
                if full_path.exists():
                    if preserve_structure:
                        # Preserve folder structure (part_number folders)
                        # Remove job_id from path but keep part_number/filename
                        path_parts = Path(file_path).parts
                        if len(path_parts) >= 2:
                            # Keep part_number/filename structure
                            arcname = str(Path(*path_parts[-2:]))
                        else:
                            arcname = Path(file_path).name
                    else:
                        # Flat structure (original behavior)
                        arcname = Path(file_path).name
                    
                    zipf.write(full_path, arcname)
        
        return str(zip_path)
    
    def get_file(self, file_path: str) -> Optional[bytes]:
        """
        Read file from storage.
        
        Args:
            file_path: Relative file path
            
        Returns:
            File bytes or None if not found
        """
        full_path = self.processed_dir / file_path
        if full_path.exists():
            with open(full_path, "rb") as f:
                return f.read()
        return None
    
    def cleanup_old_files(self):
        """Clean up files older than TTL."""
        if self.cleanup_ttl_hours == 0:
            return
        
        cutoff_time = datetime.now() - timedelta(hours=self.cleanup_ttl_hours)
        
        for directory in [self.upload_dir, self.processed_dir]:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        try:
                            file_path.unlink()
                        except Exception as e:
                            print(f"Error deleting {file_path}: {e}")
            
            # Remove empty directories
            for dir_path in directory.rglob("*"):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    try:
                        dir_path.rmdir()
                    except Exception:
                        pass

