"""Pre-export validation for SharePoint readiness."""
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from app.utils.filename_parser import parse_filename


def validate_export(job_id: str, processed_dir: Path) -> Dict[str, Any]:
    """
    Validate processed images before export.
    
    Checks:
    - All images processed successfully
    - All parts have views
    - No corrupted images
    - Consistent naming
    
    Args:
        job_id: Job ID to validate
        processed_dir: Path to processed images directory
        
    Returns:
        Validation results dictionary
    """
    job_dir = processed_dir / job_id
    
    if not job_dir.exists():
        return {
            "is_valid": False,
            "total_parts": 0,
            "total_images": 0,
            "missing_views": [],
            "corrupted_images": [],
            "warnings": ["Job directory not found"]
        }
    
    # Collect all images organized by part
    parts_data = defaultdict(lambda: {
        "views": [],
        "locations": set(),
        "filenames": []
    })
    
    all_images = []
    corrupted = []
    
    # Scan all images in job directory
    for part_dir in job_dir.iterdir():
        if part_dir.is_dir():
            symbol_number = part_dir.name
            
            for image_file in part_dir.glob("*.*"):
                if image_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    # Parse filename
                    parsed = parse_filename(image_file.name)
                    
                    if parsed.is_valid:
                        parts_data[symbol_number]["views"].append(parsed.view_number)
                        parts_data[symbol_number]["locations"].add(parsed.location)
                        parts_data[symbol_number]["filenames"].append(image_file.name)
                        all_images.append(image_file.name)
                        
                        # Check if file is readable/valid
                        try:
                            with open(image_file, 'rb') as f:
                                # Try to read first few bytes
                                f.read(1024)
                        except Exception:
                            corrupted.append(image_file.name)
                    else:
                        corrupted.append(image_file.name)
    
    # Check for missing views
    missing_views = []
    for symbol_number, data in parts_data.items():
        views = sorted(set(data["views"]), key=lambda x: int(x))
        expected_views = [str(i) for i in range(1, len(views) + 1)]
        
        # Check for gaps in view numbers
        actual_views_int = sorted([int(v) for v in views])
        if actual_views_int:
            expected_range = list(range(1, max(actual_views_int) + 1))
            missing = [str(v) for v in expected_range if v not in actual_views_int]
            
            if missing:
                missing_views.append({
                    "symbol_number": symbol_number,
                    "expected_views": expected_range,
                    "actual_views": actual_views_int,
                    "missing_views": missing
                })
    
    # Generate warnings
    warnings = []
    if len(parts_data) == 0:
        warnings.append("No parts found - check if images were processed")
    
    for symbol_number, data in parts_data.items():
        if len(data["locations"]) > 1:
            warnings.append(f"Part {symbol_number} has multiple locations: {', '.join(data['locations'])}")
    
    # Overall validation
    is_valid = (
        len(all_images) > 0 and
        len(corrupted) == 0 and
        len(missing_views) == 0
    )
    
    return {
        "is_valid": is_valid,
        "total_parts": len(parts_data),
        "total_images": len(all_images),
        "missing_views": missing_views,
        "corrupted_images": corrupted,
        "warnings": warnings
    }

