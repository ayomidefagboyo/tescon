"""Image compression utilities for reducing file size."""
from PIL import Image
from io import BytesIO
from typing import Optional


def compress_image(
    image: Image.Image,
    quality: int = 85,
    max_dimension: Optional[int] = None,
    optimize: bool = True
) -> Image.Image:
    """
    Compress and optionally resize an image.
    
    Args:
        image: PIL Image object
        quality: JPEG quality (1-100), lower = smaller file
        max_dimension: Maximum width or height (None = no resize)
        optimize: Whether to optimize the image
        
    Returns:
        Compressed PIL Image
    """
    # Resize if needed
    if max_dimension and (image.width > max_dimension or image.height > max_dimension):
        # Calculate new dimensions while maintaining aspect ratio
        ratio = min(max_dimension / image.width, max_dimension / image.height)
        new_width = int(image.width * ratio)
        new_height = int(image.height * ratio)
        
        # Use LANCZOS for high-quality resizing
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    return image


def get_compressed_size(
    image: Image.Image,
    format: str = "JPEG",
    quality: int = 85
) -> int:
    """
    Get the file size of compressed image without saving.
    
    Args:
        image: PIL Image
        format: Image format
        quality: Compression quality
        
    Returns:
        Size in bytes
    """
    buffer = BytesIO()
    
    if format.upper() == "JPEG":
        # Convert RGBA to RGB for JPEG
        if image.mode == "RGBA":
            image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
    else:
        # PNG
        image.save(buffer, format="PNG", optimize=True)
    
    return buffer.tell()


def calculate_optimal_quality(
    image: Image.Image,
    target_size_kb: int,
    min_quality: int = 70,
    max_quality: int = 95
) -> int:
    """
    Calculate optimal JPEG quality to achieve target file size.
    
    Args:
        image: PIL Image
        target_size_kb: Target file size in KB
        min_quality: Minimum acceptable quality
        max_quality: Maximum quality to try
        
    Returns:
        Optimal quality setting
    """
    target_bytes = target_size_kb * 1024
    
    # Binary search for optimal quality
    low, high = min_quality, max_quality
    best_quality = max_quality
    
    while low <= high:
        mid = (low + high) // 2
        size = get_compressed_size(image, "JPEG", mid)
        
        if size <= target_bytes:
            best_quality = mid
            low = mid + 1  # Try higher quality
        else:
            high = mid - 1  # Try lower quality
    
    return best_quality


def get_compression_presets() -> dict:
    """
    Get predefined compression presets.
    
    Returns:
        Dictionary of preset names and settings
    """
    return {
        "high_quality": {
            "quality": 95,
            "max_dimension": None,
            "description": "Highest quality, larger files"
        },
        "balanced": {
            "quality": 85,
            "max_dimension": 2048,
            "description": "Good quality, moderate size (recommended)"
        },
        "web_optimized": {
            "quality": 80,
            "max_dimension": 1600,
            "description": "Web-optimized, smaller files"
        },
        "compact": {
            "quality": 75,
            "max_dimension": 1200,
            "description": "Compact size, acceptable quality"
        }
    }

