"""Background removal processor using PicWish API."""
import os
import time
import requests
from PIL import Image
from io import BytesIO
from typing import Optional, List
from app.processing.image_utils import composite_white_background, convert_format
from app.utils.image_compressor import compress_image

# PicWish API configuration
# Note: Verify the exact endpoint in PicWish API documentation
# Common endpoints:
# - Background removal: https://api.picwish.com/v1/remove-background
# - Or: https://techhk.aoscdn.com/api/tasks/visual/removebg
PICWISH_API_URL = os.getenv("PICWISH_API_URL", "https://api.picwish.com/v1/remove-background")
PICWISH_API_KEY = os.getenv("PICWISH_API_KEY", "")


def check_api_available() -> bool:
    """Check if PicWish API is configured."""
    return bool(PICWISH_API_KEY)


def is_model_loaded() -> bool:
    """Check if API is configured (for compatibility)."""
    return check_api_available()


def process_image(
    image_bytes: bytes,
    output_format: str = "PNG",
    white_background: bool = True,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    compression_quality: int = 85,
    max_dimension: int = None
) -> BytesIO:
    """
    Process image to remove background using PicWish API.
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
    if not PICWISH_API_KEY:
        raise Exception("PicWish API key not configured. Set PICWISH_API_KEY environment variable.")
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # Call PicWish API
            # Try different field names based on API version
            files = {"image": ("image.jpg", image_bytes, "image/jpeg")}
            # Some APIs use "image_file" instead of "image"
            # files = {"image_file": ("image.jpg", image_bytes, "image/jpeg")}
            
            headers = {"X-API-Key": PICWISH_API_KEY}
            # Alternative header format: "X-API-KEY" or "Authorization: Bearer {key}"
            
            response = requests.post(
                PICWISH_API_URL,
                files=files,
                headers=headers,
                timeout=60  # 60 second timeout
            )
            
            if response.status_code == 200:
                # Get processed image from response
                output_bytes = response.content
                
                # Load processed image
                processed_image = Image.open(BytesIO(output_bytes))
                
                # Composite onto white background if requested
                if white_background:
                    processed_image = composite_white_background(processed_image)
                
                # Apply compression if specified
                if compression_quality < 95 or max_dimension:
                    processed_image = compress_image(
                        processed_image,
                        quality=compression_quality,
                        max_dimension=max_dimension
                    )
                
                # Convert to requested format
                return convert_format(processed_image, output_format, quality=compression_quality)
            elif response.status_code == 429:
                # Rate limit - wait and retry
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    raise Exception(f"Rate limit exceeded after {max_retries} attempts")
            else:
                # API error
                error_msg = f"API error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_msg)
                except:
                    error_msg = response.text or error_msg
                
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    raise Exception(f"PicWish API error: {error_msg}")
                    
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < max_retries - 1:
                # Exponential backoff for network errors
                delay = retry_delay * (2 ** attempt)
                time.sleep(delay)
                continue
            else:
                raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
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
    Process multiple images in batch.
    
    Args:
        image_bytes_list: List of image bytes
        output_format: Output format ("PNG" or "JPEG")
        white_background: Whether to composite onto white background
        batch_size: Batch size (not used for API, kept for compatibility)
        
    Returns:
        List of BytesIO buffers with processed images
    """
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

