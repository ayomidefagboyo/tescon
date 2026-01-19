"""Filename validation endpoints."""
from typing import List
from fastapi import APIRouter, UploadFile, File
from app.models import FilenameValidationResponse, RenameRequest, ParsedFilenameInfo
from app.utils.filename_parser import parse_filename, validate_batch_filenames, suggest_filename

router = APIRouter()


@router.post("/validate/filenames", response_model=FilenameValidationResponse)
async def validate_filenames(files: List[UploadFile] = File(...)):
    """
    Validate filenames before processing.
    
    Returns validation summary with invalid files flagged.
    """
    filenames = [file.filename for file in files if file.filename]
    results = validate_batch_filenames(filenames)
    
    return FilenameValidationResponse(**results)


@router.post("/validate/parse", response_model=ParsedFilenameInfo)
async def parse_single_filename(filename: str):
    """
    Parse and validate a single filename.
    
    Returns parsed components and validation status.
    """
    result = parse_filename(filename)
    return ParsedFilenameInfo(
        symbol_number=result.symbol_number,
        view_number=result.view_number,
        location=result.location,
        original_filename=result.original_filename,
        is_valid=result.is_valid,
        error_message=result.error_message
    )


@router.post("/validate/suggest")
async def suggest_valid_filename(rename_request: RenameRequest) -> dict:
    """
    Suggest a valid filename based on user input.
    """
    suggested = suggest_filename(
        rename_request.original_filename,
        rename_request.symbol_number,
        rename_request.view_number,
        rename_request.location
    )
    
    return {
        "original": rename_request.original_filename,
        "suggested": suggested,
        "is_valid": parse_filename(suggested).is_valid
    }

