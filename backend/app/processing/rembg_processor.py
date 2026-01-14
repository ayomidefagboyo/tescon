"""Background removal processor using rembg."""
import os
import time
import torch
from PIL import Image
from io import BytesIO
from typing import Optional, Tuple, List
from rembg import remove, new_session
from app.processing.image_utils import composite_white_background, convert_format

# Global session for rembg model
_session: Optional[object] = None
_model_name = "isnet-general-use"


def check_gpu_availability() -> bool:
    """Check if GPU is available."""
    if torch.cuda.is_available():
        return True
    # Check for Apple Silicon (MPS)
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return True
    return False


def get_device() -> str:
    """Get the best available device."""
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def initialize_processor():
    """Initialize the rembg processor with IS-Net model."""
    global _session
    
    if _session is None:
        device = get_device()
        print(f"Initializing rembg with device: {device}")
        _session = new_session(_model_name, providers=[device])
        print(f"✓ rembg session initialized with {_model_name}")


def is_model_loaded() -> bool:
    """Check if model is loaded."""
    return _session is not None


def process_image(
    image_bytes: bytes,
    output_format: str = "PNG",
    white_background: bool = True,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> BytesIO:
    """
    Process image to remove background and optionally add white background.
    Includes retry logic with exponential backoff.
    
    Args:
        image_bytes: Input image bytes
        output_format: Output format ("PNG" or "JPEG")
        white_background: Whether to composite onto white background
        max_retries: Maximum number of retry attempts
        retry_delay: Initial retry delay in seconds
        
    Returns:
        BytesIO buffer with processed image
        
    Raises:
        Exception: If processing fails after all retries
    """
    global _session
    
    if _session is None:
        initialize_processor()
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # Remove background using rembg
            output_bytes = remove(image_bytes, session=_session)
            
            # Load processed image
            processed_image = Image.open(BytesIO(output_bytes))
            
            # Composite onto white background if requested
            if white_background:
                processed_image = composite_white_background(processed_image)
            
            # Convert to requested format
            return convert_format(processed_image, output_format)
            
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                # Exponential backoff
                delay = retry_delay * (2 ** attempt)
                time.sleep(delay)
                continue
            else:
                raise
    
    # Should never reach here, but just in case
    raise Exception(f"Processing failed after {max_retries} attempts: {last_error}")


def process_images_batch(
    image_bytes_list: List[bytes],
    output_format: str = "PNG",
    white_background: bool = True,
    batch_size: Optional[int] = None
) -> List[BytesIO]:
    """
    Process multiple images in batch (GPU optimization).
    
    Args:
        image_bytes_list: List of image bytes
        output_format: Output format ("PNG" or "JPEG")
        white_background: Whether to composite onto white background
        batch_size: Batch size for GPU processing (None = auto-detect)
        
    Returns:
        List of BytesIO buffers with processed images
    """
    global _session
    
    if _session is None:
        initialize_processor()
    
    # For now, process sequentially
    # Future: Implement true batch processing if rembg supports it
    results = []
    for image_bytes in image_bytes_list:
        try:
            result = process_image(image_bytes, output_format, white_background)
            results.append(result)
        except Exception as e:
            # Add None for failed images
            results.append(None)
    
    return results


def process_image_file(
    input_path: str,
    output_path: str,
    output_format: str = "PNG",
    white_background: bool = True
) -> bool:
    """
    Process image file from disk.
    
    Args:
        input_path: Path to input image
        output_path: Path to save processed image
        output_format: Output format ("PNG" or "JPEG")
        white_background: Whether to composite onto white background
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(input_path, "rb") as f:
            image_bytes = f.read()
        
        processed_buffer = process_image(image_bytes, output_format, white_background)
        
        with open(output_path, "wb") as f:
            f.write(processed_buffer.read())
        
        return True
    except Exception as e:
        print(f"Error processing image {input_path}: {e}")
        return False

