"""Export and validation endpoints."""
from fastapi import APIRouter, HTTPException
from pathlib import Path
from app.models import ExportValidationResponse
from app.utils.export_validator import validate_export
from app.storage.local_storage import LocalStorage
from app.api.jobs import job_manager
import os

router = APIRouter()

# Initialize storage
storage = LocalStorage(
    upload_dir=os.getenv("UPLOAD_DIR", "uploads"),
    processed_dir=os.getenv("PROCESSED_DIR", "processed"),
)


@router.get("/jobs/{job_id}/validate-export", response_model=ExportValidationResponse)
async def validate_job_export(job_id: str):
    """
    Validate job before export.
    
    Checks for:
    - Missing views
    - Corrupted images
    - Proper folder structure
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Run validation
    results = validate_export(job_id, storage.processed_dir)
    
    return ExportValidationResponse(**results)

