"""Enhanced background removal processor using rembg with BiRefNet."""
import os
import time
import torch
import threading
from PIL import Image
from io import BytesIO
from typing import Optional, Tuple, List, Dict, Any
from rembg import remove, new_session
from app.processing.image_utils import composite_white_background, convert_format

# Global sessions for different models
_sessions: Dict[str, Optional[object]] = {}
_session_lock = threading.Lock()

# Enhanced model configuration - BiRefNet for better quality
_primary_model = "birefnet-general"  # Best quality for general use
_fallback_model = "isnet-general-use"  # Fast fallback
_current_model = None


def check_gpu_availability() -> bool:
    """Check if GPU is available."""
    if torch.cuda.is_available():
        return True
    # Check for Apple Silicon (MPS)
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return True
    return False


def get_device() -> str:
    """Get the best available device with optimization."""
    if torch.cuda.is_available():
        # Set CUDA optimizations
        torch.backends.cudnn.benchmark = True
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_optimal_model() -> str:
    """Select optimal model based on available hardware."""
    device = get_device()

    if device == "cuda":
        # Check GPU memory to decide on model
        try:
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9  # GB
            if gpu_memory >= 8:  # 8GB+ VRAM can handle BiRefNet
                return _primary_model
            else:
                print(f"⚠ Limited GPU memory ({gpu_memory:.1f}GB), using fallback model")
                return _fallback_model
        except:
            return _fallback_model

    return _fallback_model  # CPU or MPS use lighter model


def initialize_processor(model_name: Optional[str] = None):
    """Initialize the enhanced rembg processor with optimal model selection."""
    global _sessions, _current_model

    if model_name is None:
        model_name = get_optimal_model()

    with _session_lock:
        if model_name not in _sessions or _sessions[model_name] is None:
            device = get_device()
            print(f"🚀 Initializing enhanced rembg with model: {model_name}, device: {device}")

            try:
                # Configure providers for optimal performance
                providers = []
                if device == "cuda":
                    providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                elif device == "mps":
                    providers = ['CoreMLExecutionProvider', 'CPUExecutionProvider']
                else:
                    providers = ['CPUExecutionProvider']

                _sessions[model_name] = new_session(model_name, providers=providers)
                _current_model = model_name
                print(f"✅ Enhanced rembg session initialized: {model_name} on {device}")

                # Warm up the model with a small test
                if device in ["cuda", "mps"]:
                    print("🔥 Warming up GPU model...")
                    test_image = Image.new('RGB', (256, 256), color='white')
                    test_buffer = BytesIO()
                    test_image.save(test_buffer, format='PNG')
                    test_buffer.seek(0)
                    remove(test_buffer.getvalue(), session=_sessions[model_name])
                    print("✅ GPU model warmed up")

            except Exception as e:
                print(f"❌ Failed to initialize {model_name}: {str(e)}")
                # Fallback to lighter model
                if model_name != _fallback_model:
                    print(f"🔄 Falling back to {_fallback_model}")
                    initialize_processor(_fallback_model)
                else:
                    raise Exception(f"Failed to initialize any rembg model: {str(e)}")


def is_model_loaded() -> bool:
    """Check if any model is loaded."""
    return bool(_sessions) and any(_sessions.values())


def get_current_session():
    """Get the current active session."""
    if _current_model and _current_model in _sessions:
        return _sessions[_current_model]
    # Return any available session
    for session in _sessions.values():
        if session is not None:
            return session
    return None


def get_performance_stats() -> Dict[str, Any]:
    """Get current performance statistics."""
    device = get_device()
    stats = {
        "device": device,
        "current_model": _current_model,
        "models_loaded": list(_sessions.keys()),
        "gpu_available": check_gpu_availability()
    }

    if device == "cuda" and torch.cuda.is_available():
        try:
            stats.update({
                "gpu_memory_total": f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB",
                "gpu_memory_used": f"{torch.cuda.memory_allocated() / 1e9:.1f}GB",
                "gpu_name": torch.cuda.get_device_name(0)
            })
        except:
            pass

    return stats


def process_image(
    image_bytes: bytes,
    output_format: str = "PNG",
    white_background: bool = True,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    compression_quality: int = 85,  # Match PicWish parameter
    max_dimension: int = None,      # Match PicWish parameter
    optimization_level: str = "balanced",  # "fast", "balanced", "quality"
    # Text/Layout arguments (matching PicWish processor)
    description: Optional[str] = None,
    add_label: bool = True,
    label_position: str = "bottom-left",
    item_note: Optional[str] = None,
    symbol_number: Optional[str] = None,
    desc1: Optional[str] = None,
    desc2: Optional[str] = None,
    long_description: Optional[str] = None,
    part_number: Optional[str] = None,
    manufacturer: Optional[str] = None,
    use_ecommerce_layout: bool = False
) -> BytesIO:
    """
    Enhanced image processing with optimal model selection and GPU acceleration.

    Args:
        image_bytes: Input image bytes
        output_format: Output format ("PNG" or "JPEG")
        white_background: Whether to composite onto white background
        max_retries: Maximum number of retry attempts
        retry_delay: Initial retry delay in seconds
        compression_quality: JPEG compression quality (85 default)
        max_dimension: Maximum dimension for resizing (None = no resize)
        optimization_level: Processing optimization ("fast", "balanced", "quality")
        description: Text to display in label
        add_label: Whether to add a text label
        label_position: Position of the label
        item_note: Alternative text source
        symbol_number: Part symbol number (for e-commerce layout)
        desc1: Primary description (e-commerce)
        desc2: Secondary description (e-commerce)
        long_description: Detailed description (e-commerce)
        part_number: Manufacturer part number (e-commerce)
        manufacturer: Manufacturer name (e-commerce)
        use_ecommerce_layout: Whether to use the full e-commerce card layout

    Returns:
        BytesIO buffer with processed image

    Raises:
        Exception: If processing fails after all retries
    """
    # Ensure processor is initialized
    current_session = get_current_session()
    if current_session is None:
        initialize_processor()
        current_session = get_current_session()

    if current_session is None:
        raise Exception("Failed to initialize any rembg model")

    last_error = None
    start_time = time.time()

    for attempt in range(max_retries):
        try:
            # Optimize image preprocessing based on level
            processed_bytes = image_bytes

            if optimization_level == "quality":
                # For quality mode, ensure image is optimal size
                try:
                    temp_img = Image.open(BytesIO(image_bytes))
                    # Resize if too large (BiRefNet works best with reasonable sizes)
                    if max(temp_img.size) > 2048:
                        ratio = 2048 / max(temp_img.size)
                        new_size = tuple(int(dim * ratio) for dim in temp_img.size)
                        temp_img = temp_img.resize(new_size, Image.Resampling.LANCZOS)

                        buffer = BytesIO()
                        temp_img.save(buffer, format='PNG', optimize=True)
                        processed_bytes = buffer.getvalue()
                except Exception:
                    pass  # Use original if preprocessing fails

            # Remove background using enhanced session
            with torch.inference_mode() if torch.cuda.is_available() else torch.no_grad():
                output_bytes = remove(processed_bytes, session=current_session)

            # Load processed image
            processed_image = Image.open(BytesIO(output_bytes))

            # Enhanced post-processing
            if white_background:
                processed_image = composite_white_background(processed_image)

            # Add text label or e-commerce layout (feature parity with PicWish)
            if use_ecommerce_layout:
                # Listing-style card: include requested fields when available
                from app.processing.image_utils import create_ecommerce_card_layout
                processed_image = create_ecommerce_card_layout(
                    processed_image,
                    symbol_number=symbol_number,
                    desc1=(desc1 or description).rstrip(',').strip() if (desc1 or description) else None,
                    desc2=desc2.rstrip(',').strip() if desc2 else None,
                    long_description=long_description,  # Only use if it exists, no fallback
                    part_number=part_number,
                    manufacturer=manufacturer,
                    padding=24
                )
            elif add_label and (item_note or description):
                # Fallback: overlay a single combined text block
                from app.processing.image_utils import add_text_label
                processed_image = add_text_label(
                    processed_image,
                    text=item_note or description or "",
                    position=label_position,
                    font_size=None,  # Auto-calculate
                    text_color=(0, 0, 0),  # Black text
                    background_color=(255, 255, 255, 220),  # Semi-transparent white background
                    padding=8,
                    margin=15
                )

            # Apply compression if specified (matching PicWish behavior)
            if compression_quality < 95 or max_dimension:
                from app.utils.image_compressor import compress_image
                processed_image = compress_image(
                    processed_image,
                    quality=compression_quality,
                    max_dimension=max_dimension
                )

            # Performance logging
            processing_time = (time.time() - start_time) * 1000
            if processing_time < 1000:  # Log fast processing
                print(f"⚡ Fast processing: {processing_time:.0f}ms ({_current_model})")

            # Convert to requested format (matching PicWish behavior)
            return convert_format(processed_image, output_format, quality=compression_quality)

        except torch.cuda.OutOfMemoryError as e:
            print(f"🚨 GPU OOM, falling back to CPU for this image")
            # Clear GPU cache and retry with CPU
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            # Try with CPU fallback
            if attempt == 0:  # Only try CPU fallback once
                try:
                    cpu_session = _sessions.get(_fallback_model)
                    if cpu_session is None:
                        initialize_processor(_fallback_model)
                        cpu_session = _sessions.get(_fallback_model)

                    if cpu_session:
                        output_bytes = remove(processed_bytes, session=cpu_session)
                        processed_image = Image.open(BytesIO(output_bytes))
                        if white_background:
                            processed_image = composite_white_background(processed_image)

                        # Apply compression if specified (matching PicWish behavior)
                        if compression_quality < 95 or max_dimension:
                            from app.utils.image_compressor import compress_image
                            processed_image = compress_image(
                                processed_image,
                                quality=compression_quality,
                                max_dimension=max_dimension
                            )

                        return convert_format(processed_image, output_format, quality=compression_quality)
                except Exception:
                    pass

            last_error = e
            if attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)
                time.sleep(delay)
                continue
            else:
                raise

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
    raise Exception(f"Enhanced processing failed after {max_retries} attempts: {last_error}")


def process_images_batch(
    image_bytes_list: List[bytes],
    output_format: str = "PNG",
    white_background: bool = True,
    batch_size: Optional[int] = None,
    compression_quality: int = 85,  # Match PicWish parameter
    max_dimension: int = None,      # Match PicWish parameter
    optimization_level: str = "balanced",
    progress_callback: Optional[callable] = None
) -> List[Optional[BytesIO]]:
    """
    Enhanced batch processing optimized for large datasets (20k+ images).

    Args:
        image_bytes_list: List of image bytes
        output_format: Output format ("PNG" or "JPEG")
        white_background: Whether to composite onto white background
        batch_size: Batch size for memory management (None = auto-detect)
        compression_quality: JPEG compression quality (85 default)
        max_dimension: Maximum dimension for resizing (None = no resize)
        optimization_level: Processing optimization level
        progress_callback: Optional callback for progress tracking

    Returns:
        List of BytesIO buffers with processed images (None for failed)
    """
    total_images = len(image_bytes_list)
    if total_images == 0:
        return []

    # Ensure processor is initialized
    current_session = get_current_session()
    if current_session is None:
        initialize_processor()

    # Auto-detect optimal batch size based on available resources
    if batch_size is None:
        device = get_device()
        if device == "cuda" and torch.cuda.is_available():
            try:
                # Base batch size on GPU memory
                gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
                if gpu_memory_gb >= 12:
                    batch_size = 8  # Large GPU
                elif gpu_memory_gb >= 8:
                    batch_size = 4  # Medium GPU
                else:
                    batch_size = 2  # Small GPU
            except:
                batch_size = 4
        else:
            batch_size = 1  # CPU processing

    print(f"🚀 Enhanced batch processing: {total_images} images, batch_size={batch_size}, device={get_device()}")

    results = []
    successful_count = 0
    failed_count = 0
    start_time = time.time()

    # Process in batches with memory management
    for batch_start in range(0, total_images, batch_size):
        batch_end = min(batch_start + batch_size, total_images)
        batch_images = image_bytes_list[batch_start:batch_end]

        print(f"📦 Processing batch {batch_start//batch_size + 1}/{(total_images + batch_size - 1)//batch_size} "
              f"(images {batch_start+1}-{batch_end})")

        batch_results = []
        batch_start_time = time.time()

        for i, image_bytes in enumerate(batch_images):
            try:
                # Process single image with enhanced settings
                result = process_image(
                    image_bytes,
                    output_format,
                    white_background,
                    compression_quality=compression_quality,
                    max_dimension=max_dimension,
                    optimization_level=optimization_level
                )
                batch_results.append(result)
                successful_count += 1

                # Progress callback
                if progress_callback:
                    progress_callback(batch_start + i + 1, total_images, successful_count, failed_count)

            except Exception as e:
                print(f"❌ Failed to process image {batch_start + i + 1}: {str(e)[:100]}")
                batch_results.append(None)
                failed_count += 1

                # Progress callback for failures
                if progress_callback:
                    progress_callback(batch_start + i + 1, total_images, successful_count, failed_count)

        results.extend(batch_results)

        # Batch performance stats
        batch_time = time.time() - batch_start_time
        batch_size_actual = len(batch_images)
        avg_time_per_image = (batch_time / batch_size_actual) * 1000

        print(f"✅ Batch completed: {batch_size_actual} images in {batch_time:.1f}s "
              f"({avg_time_per_image:.0f}ms/image)")

        # Memory cleanup between batches
        if torch.cuda.is_available() and batch_start + batch_size < total_images:
            torch.cuda.empty_cache()
            time.sleep(0.1)  # Brief pause for memory cleanup

    # Final stats
    total_time = time.time() - start_time
    avg_time_per_image = (total_time / total_images) * 1000
    success_rate = (successful_count / total_images) * 100

    print(f"🎉 Batch processing complete!")
    print(f"📊 Total: {total_images} images in {total_time:.1f}s ({avg_time_per_image:.0f}ms/image)")
    print(f"✅ Success: {successful_count} ({success_rate:.1f}%)")
    print(f"❌ Failed: {failed_count}")
    print(f"💾 Model: {_current_model}, Device: {get_device()}")

    return results


def optimize_for_large_dataset():
    """
    Optimize system settings for processing large datasets (20k+ images).
    Call this before processing large batches.
    """
    if torch.cuda.is_available():
        # Enable optimizations for large datasets
        torch.backends.cudnn.benchmark = True
        torch.backends.cuda.matmul.allow_tf32 = True

        # Set memory management
        torch.cuda.empty_cache()

        # Print GPU info
        gpu_name = torch.cuda.get_device_name(0)
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"🔧 GPU optimized for large dataset: {gpu_name} ({total_memory:.1f}GB)")

    print("⚡ System optimized for large dataset processing")


def estimate_processing_time(num_images: int) -> Dict[str, float]:
    """
    Estimate processing time for a given number of images.

    Args:
        num_images: Number of images to process

    Returns:
        Dictionary with time estimates in seconds
    """
    device = get_device()
    stats = get_performance_stats()

    # Base processing times per image (in seconds)
    if device == "cuda":
        if _current_model == "birefnet-general":
            base_time = 0.35  # BiRefNet on GPU
        else:
            base_time = 0.25  # IS-Net on GPU
    elif device == "mps":
        base_time = 0.8  # Apple Silicon
    else:
        base_time = 8.0  # CPU processing

    # Add overhead for batch processing
    overhead_factor = 1.1  # 10% overhead for batch management

    estimated_total = num_images * base_time * overhead_factor

    return {
        "total_seconds": estimated_total,
        "total_minutes": estimated_total / 60,
        "total_hours": estimated_total / 3600,
        "per_image_ms": base_time * 1000,
        "device": device,
        "model": _current_model or "unknown"
    }


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

