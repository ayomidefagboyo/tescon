"""Pydantic models for API requests and responses."""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class JobStatus(str, Enum):
    """Job processing status."""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ParsedFilenameInfo(BaseModel):
    """Parsed filename information."""
    part_number: str
    view_number: str
    location: str  # Now used as description (e.g., BEARING, FAN TYPE)
    original_filename: str
    is_valid: bool
    error_message: Optional[str] = None


class FilenameValidationResponse(BaseModel):
    """Batch filename validation response."""
    total_files: int
    valid_files: int
    invalid_files: int
    unique_parts: int
    invalid_details: List[Dict[str, str]]
    parts_summary: List[Dict[str, Any]]


class RenameRequest(BaseModel):
    """Request to rename a file."""
    original_filename: str
    part_number: str
    view_number: str
    location: str  # Now description field


class CompressionSettings(BaseModel):
    """Image compression settings."""
    quality: int = 85
    max_dimension: Optional[int] = 2048
    preset: Optional[str] = "balanced"


class JobResponse(BaseModel):
    """Job creation response."""
    job_id: str
    status: JobStatus
    message: str
    validation_results: Optional[FilenameValidationResponse] = None


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: JobStatus
    total_images: int
    processed_count: int
    failed_count: int
    failed_images: Optional[List[str]] = None
    error_messages: Optional[List[str]] = None
    parts_organized: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response."""
    model_config = {"protected_namespaces": ()}

    status: str
    gpu_available: bool
    model_loaded: bool


class ExportValidationResponse(BaseModel):
    """Pre-export validation results."""
    is_valid: bool
    total_parts: int
    total_images: int
    missing_views: List[Dict[str, Any]]
    corrupted_images: List[str]
    warnings: List[str]


class PartInfo(BaseModel):
    """Part information from Google Sheets."""
    part_number: str
    description: str
    location: str
    item_note: str


class ProcessPartResponse(BaseModel):
    """Response for part processing."""
    success: bool
    part_number: str
    description: str
    location: str
    item_note: Optional[str] = None
    files_saved: int
    saved_paths: List[Dict[str, str]]
    message: str
