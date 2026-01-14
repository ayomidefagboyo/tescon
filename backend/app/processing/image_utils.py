"""Image manipulation utilities."""
from PIL import Image
from io import BytesIO
from typing import Tuple, Optional


def composite_white_background(image: Image.Image) -> Image.Image:
    """
    Composite an image with transparency onto a white background.
    
    Args:
        image: PIL Image with alpha channel
        
    Returns:
        PIL Image with white background (RGB, no alpha)
    """
    if image.mode == "RGBA":
        # Create white background
        white_bg = Image.new("RGB", image.size, (255, 255, 255))
        # Composite image onto white background
        white_bg.paste(image, mask=image.split()[3])  # Use alpha channel as mask
        return white_bg
    elif image.mode == "RGB":
        # Already RGB, return as-is
        return image.copy()
    else:
        # Convert to RGB
        return image.convert("RGB")


def convert_format(image: Image.Image, format: str, quality: int = 95) -> BytesIO:
    """
    Convert image to specified format.
    
    Args:
        image: PIL Image
        format: Target format ("PNG" or "JPEG")
        quality: JPEG quality (1-100, only for JPEG)
        
    Returns:
        BytesIO buffer with converted image
    """
    buffer = BytesIO()
    
    if format.upper() == "JPEG" or format.upper() == "JPG":
        # Convert RGBA to RGB for JPEG
        if image.mode == "RGBA":
            image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
    else:
        # PNG
        image.save(buffer, format="PNG", optimize=True)
    
    buffer.seek(0)
    return buffer


def validate_image(image_bytes: bytes, max_size_mb: int = 100) -> Tuple[bool, Optional[str]]:
    """
    Validate image file.
    
    Args:
        image_bytes: Image file bytes
        max_size_mb: Maximum file size in MB
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    max_size_bytes = max_size_mb * 1024 * 1024
    if len(image_bytes) > max_size_bytes:
        return False, f"Image exceeds maximum size of {max_size_mb}MB"
    
    # Try to open as image
    try:
        image = Image.open(BytesIO(image_bytes))
        image.verify()
        
        # Check format
        allowed_formats = ["JPEG", "PNG", "WEBP"]
        if image.format not in allowed_formats:
            return False, f"Unsupported format: {image.format}. Allowed: {', '.join(allowed_formats)}"
        
        return True, None
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"

