"""Filename parser and validator for TESCON naming convention."""
import re
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ParsedFilename:
    """Parsed filename components."""
    part_number: str
    view_number: str
    location: str
    original_filename: str
    is_valid: bool
    error_message: Optional[str] = None


def parse_filename(filename: str) -> ParsedFilename:
    """
    Parse and validate filename according to TESCON naming convention.
    
    Expected format: PartNumber_ViewNumber_Location.ext
    Example: 58802935_1_EG1060007.jpg
    
    Args:
        filename: Filename to parse (with or without extension)
        
    Returns:
        ParsedFilename object with validation status
    """
    # Remove extension
    name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
    
    # Pattern: PartNumber_ViewNumber_Location
    # PartNumber: alphanumeric (typically numeric)
    # ViewNumber: numeric (1, 2, 3...)
    # Location: alphanumeric (e.g., EG1060007)
    pattern = r'^([A-Za-z0-9]+)_(\d+)_([A-Za-z0-9]+)$'
    
    match = re.match(pattern, name_without_ext)
    
    if match:
        part_number, view_number, location = match.groups()
        return ParsedFilename(
            part_number=part_number,
            view_number=view_number,
            location=location,
            original_filename=filename,
            is_valid=True,
            error_message=None
        )
    else:
        # Try to provide helpful error message
        error_msg = _get_error_message(name_without_ext)
        
        return ParsedFilename(
            part_number="",
            view_number="",
            location="",
            original_filename=filename,
            is_valid=False,
            error_message=error_msg
        )


def _get_error_message(filename: str) -> str:
    """Generate helpful error message for invalid filename."""
    parts = filename.split('_')
    
    if len(parts) < 3:
        return f"Missing components. Expected format: PartNumber_ViewNumber_Location (found {len(parts)} parts)"
    elif len(parts) > 3:
        return f"Too many underscores. Expected format: PartNumber_ViewNumber_Location (found {len(parts)} parts)"
    else:
        # Check individual components
        part_num, view_num, location = parts
        
        if not view_num.isdigit():
            return f"ViewNumber must be numeric (got '{view_num}')"
        elif not part_num:
            return "PartNumber cannot be empty"
        elif not location:
            return "Location cannot be empty"
        else:
            return "Invalid format. Expected: PartNumber_ViewNumber_Location"


def suggest_filename(filename: str, part_number: str = "", view_number: str = "1", location: str = "") -> str:
    """
    Suggest a valid filename based on user input.
    
    Args:
        filename: Original filename
        part_number: Suggested part number
        view_number: Suggested view number
        location: Suggested location
        
    Returns:
        Suggested valid filename
    """
    # Get extension from original
    ext = filename.rsplit('.', 1)[1] if '.' in filename else 'jpg'
    
    # Build suggested filename
    suggested = f"{part_number}_{view_number}_{location}.{ext}"
    
    return suggested


def validate_batch_filenames(filenames: list[str]) -> dict:
    """
    Validate a batch of filenames.
    
    Args:
        filenames: List of filenames to validate
        
    Returns:
        Dictionary with validation summary
    """
    results = [parse_filename(f) for f in filenames]
    
    valid_files = [r for r in results if r.is_valid]
    invalid_files = [r for r in results if not r.is_valid]
    
    # Count unique part numbers
    unique_parts = set(r.part_number for r in valid_files)
    
    return {
        "total_files": len(filenames),
        "valid_files": len(valid_files),
        "invalid_files": len(invalid_files),
        "unique_parts": len(unique_parts),
        "invalid_details": [
            {
                "filename": r.original_filename,
                "error": r.error_message
            }
            for r in invalid_files
        ],
        "parts_summary": _get_parts_summary(valid_files)
    }


def _get_parts_summary(parsed_files: list[ParsedFilename]) -> dict:
    """Get summary of parts and their view counts."""
    parts_dict = {}
    
    for pf in parsed_files:
        if pf.part_number not in parts_dict:
            parts_dict[pf.part_number] = {
                "views": [],
                "locations": set(),
                "count": 0
            }
        
        parts_dict[pf.part_number]["views"].append(pf.view_number)
        parts_dict[pf.part_number]["locations"].add(pf.location)
        parts_dict[pf.part_number]["count"] += 1
    
    # Convert to list format
    summary = []
    for part_num, data in parts_dict.items():
        summary.append({
            "part_number": part_num,
            "view_count": data["count"],
            "views": sorted(set(data["views"]), key=lambda x: int(x)),
            "locations": list(data["locations"])
        })
    
    return summary

