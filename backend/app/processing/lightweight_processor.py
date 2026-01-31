"""
Lightweight processor for Render deployment.
Queues jobs for Kaggle processing instead of local processing.
"""

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import io


def process_image(
    image_bytes: bytes,
    output_format: str = "PNG",
    white_background: bool = True,
    compression_quality: int = 85,
    max_dimension: int = 2048,
    # Text/Layout arguments (for compatibility)
    description: str = None,
    add_label: bool = False,
    label_position: str = "bottom-left",
    item_note: str = None,
    symbol_number: str = None,
    desc1: str = "",
    desc2: str = "",
    long_description: str = None,
    part_number: str = None,
    manufacturer: str = None,
    location: str = None,
    use_ecommerce_layout: bool = False
) -> BytesIO:
    """
    Lightweight processor for Render deployment.

    This creates a placeholder image indicating that processing
    will happen via Kaggle. For actual processing, jobs are
    queued to R2 and processed by Kaggle workers.

    Returns a simple processed image with basic background removal simulation.
    """

    # For single image processing endpoint, create a simple placeholder
    # In practice, all real processing happens via Kaggle

    try:
        # Load and process the image using basic PIL
        img = Image.open(BytesIO(image_bytes))

        # Convert to RGBA for transparency handling
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Apply white background if requested
        if white_background:
            # Create white background
            white_bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
            # Paste image on white background
            white_bg.paste(img, (0, 0), img)
            img = white_bg.convert('RGB')

        # Resize if necessary
        if max_dimension and (img.width > max_dimension or img.height > max_dimension):
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        # Add simple label if requested
        if add_label and (description or symbol_number):
            draw = ImageDraw.Draw(img)

            # Try to use a simple font
            try:
                # Use default font
                font_size = max(20, img.width // 40)
                font = ImageFont.load_default()
            except:
                font = None

            # Create label text
            label_parts = []
            if symbol_number:
                label_parts.append(f"Part: {symbol_number}")
            if description:
                label_parts.append(description[:50])

            if label_parts:
                label_text = " | ".join(label_parts)

                # Position label
                if label_position.startswith("bottom"):
                    y_pos = img.height - 30
                else:
                    y_pos = 10

                if "right" in label_position:
                    x_pos = img.width - 200
                elif "center" in label_position:
                    x_pos = img.width // 2 - 100
                else:
                    x_pos = 10

                # Draw label with background
                text_bbox = draw.textbbox((x_pos, y_pos), label_text, font=font)
                draw.rectangle(text_bbox, fill=(255, 255, 255, 200))
                draw.text((x_pos, y_pos), label_text, fill=(0, 0, 0), font=font)

        # Convert to requested format
        output_buffer = BytesIO()

        if output_format.upper() == "PNG":
            img.save(output_buffer, format="PNG", optimize=True)
        else:
            # JPEG
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(output_buffer, format="JPEG", quality=compression_quality, optimize=True)

        output_buffer.seek(0)
        return output_buffer

    except Exception as e:
        # Return error placeholder
        error_img = Image.new('RGB', (400, 300), (255, 255, 255))
        draw = ImageDraw.Draw(error_img)
        draw.text((50, 150), f"Processing Error: {str(e)[:50]}", fill=(255, 0, 0))

        error_buffer = BytesIO()
        error_img.save(error_buffer, format="PNG")
        error_buffer.seek(0)
        return error_buffer


def is_model_loaded() -> bool:
    """Check if processing is available (always True for lightweight processor)."""
    return True


def check_api_available() -> bool:
    """Check if API is available (always True for compatibility)."""
    return True