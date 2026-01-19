"""Image manipulation utilities."""
from PIL import Image, ImageDraw, ImageFont
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


def add_text_label(
    image: Image.Image,
    text: str,
    position: str = "bottom-left",
    font_size: Optional[int] = None,
    text_color: Tuple[int, int, int] = (0, 0, 0),
    background_color: Optional[Tuple[int, int, int, int]] = (255, 255, 255, 220),
    padding: int = 10,
    margin: int = 20
) -> Image.Image:
    """
    Add text label to image.
    
    Args:
        image: PIL Image (RGB or RGBA)
        text: Text to overlay
        position: Position of text ("bottom-left", "bottom-right", "top-left", "top-right", "bottom-center")
        font_size: Font size in pixels (auto-calculated if None)
        text_color: RGB color tuple for text (default: black)
        background_color: RGBA color tuple for background box (None = no background)
        padding: Padding around text in pixels
        margin: Margin from edges in pixels
        
    Returns:
        PIL Image with text overlay
    """
    if not text or not text.strip():
        return image.copy()
    
    # Ensure image is RGB (for drawing)
    if image.mode == "RGBA":
        # Create RGB copy for drawing
        draw_image = Image.new("RGB", image.size, (255, 255, 255))
        draw_image.paste(image, mask=image.split()[3] if image.mode == "RGBA" else None)
    else:
        draw_image = image.copy()
    
    draw = ImageDraw.Draw(draw_image)
    
    # Calculate font size based on image dimensions if not specified
    if font_size is None:
        # Font size as percentage of image height (adjustable)
        font_size = max(16, int(min(image.width, image.height) * 0.03))
    
    # Try to load a nice font, fallback to default
    try:
        # Try to use a system font (works on most systems)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            try:
                # Try Arial on Windows/Linux
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate text position
    img_width, img_height = image.size
    
    if position == "bottom-left":
        text_x = margin
        text_y = img_height - text_height - margin - (padding * 2 if background_color else 0)
    elif position == "bottom-right":
        text_x = img_width - text_width - margin - (padding * 2 if background_color else 0)
        text_y = img_height - text_height - margin - (padding * 2 if background_color else 0)
    elif position == "top-left":
        text_x = margin
        text_y = margin
    elif position == "top-right":
        text_x = img_width - text_width - margin - (padding * 2 if background_color else 0)
        text_y = margin
    elif position == "bottom-center":
        text_x = (img_width - text_width) // 2 - (padding if background_color else 0)
        text_y = img_height - text_height - margin - (padding * 2 if background_color else 0)
    else:
        # Default to bottom-left
        text_x = margin
        text_y = img_height - text_height - margin - (padding * 2 if background_color else 0)
    
    # Draw background box if specified
    if background_color:
        box_x1 = text_x - padding
        box_y1 = text_y - padding
        box_x2 = text_x + text_width + padding
        box_y2 = text_y + text_height + padding
        
        # Create overlay for semi-transparent background
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            [(box_x1, box_y1), (box_x2, box_y2)],
            fill=background_color
        )
        
        # Composite overlay onto image
        draw_image = Image.alpha_composite(
            draw_image.convert("RGBA"),
            overlay
        ).convert("RGB")
        draw = ImageDraw.Draw(draw_image)
    
    # Draw text
    draw.text((text_x, text_y), text, fill=text_color, font=font)
    
    return draw_image


def create_ecommerce_card_layout(
    image: Image.Image,
    item_note: str,
    padding: int = 20,
    text_area_height_ratio: float = 0.25
) -> Image.Image:
    """
    Create e-commerce card layout with image on top and item note below.

    Args:
        image: PIL Image (product image with white background)
        item_note: Item note text to display below image
        padding: Padding around text in pixels
        text_area_height_ratio: Height of text area as ratio of image height (0.25 = 25%)

    Returns:
        PIL Image with e-commerce card layout
    """
    if not item_note or not item_note.strip():
        return image.copy()

    # Amazon blue color
    AMAZON_BLUE = (33, 98, 161)  # #2162a1

    # Calculate dimensions
    img_width, img_height = image.size
    
    # Increase text area height for better readability (25% instead of 15%)
    text_area_height = max(80, int(img_height * text_area_height_ratio))
    
    # Add minimal top padding to reduce excessive white space
    top_padding = max(10, int(img_height * 0.02))  # 2% of image height, min 10px

    # Create new canvas with extended height for text area and top padding
    card_height = top_padding + img_height + text_area_height
    card_image = Image.new("RGB", (img_width, card_height), (255, 255, 255))

    # Paste original image with top padding (not at absolute top)
    card_image.paste(image, (0, top_padding))

    # Draw on the card
    draw = ImageDraw.Draw(card_image)

    # Calculate optimal font size based on text length and area
    max_text_width = img_width - (padding * 2)
    max_font_size = text_area_height - (padding * 2)

    # Start with a much larger, more readable font size (increased from 0.6 to 0.75)
    base_font_size = max(32, min(56, int(text_area_height * 0.75)))

    # Adjust font size based on text length - larger minimum sizes for better readability
    text_length = len(item_note)
    if text_length > 100:
        font_size = max(24, int(base_font_size * 0.8))  # Increased minimum
    elif text_length > 60:
        font_size = max(28, int(base_font_size * 0.9))  # Increased minimum
    elif text_length > 30:
        font_size = max(32, int(base_font_size * 0.95))  # Increased minimum
    else:
        font_size = base_font_size

    # Try to load a good font
    font = None
    try:
        # Try system fonts in order of preference
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "/System/Library/Fonts/Arial.ttf",       # macOS
            "arial.ttf",                             # Windows/Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            "/usr/share/fonts/TTF/arial.ttf"         # Linux
        ]

        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except:
                continue

        if font is None:
            font = ImageFont.load_default()

    except:
        font = ImageFont.load_default()

    # Word wrap the text to fit within the text area
    words = item_note.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_text_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
                current_line = word
            else:
                # Single word is too long, add it anyway
                lines.append(word)
                current_line = ""

    if current_line:
        lines.append(current_line)

    # If text is too long for the area, reduce font size and try again
    while len(lines) > 3 and font_size > 18:  # Max 3 lines, minimum 18px (increased from 10px)
        font_size = max(18, int(font_size * 0.9))
        try:
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
        except:
            pass

        # Recalculate word wrap with smaller font
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]

            if text_width <= max_text_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    lines.append(word)
                    current_line = ""

        if current_line:
            lines.append(current_line)

    # Calculate total text height
    if lines:
        bbox = draw.textbbox((0, 0), lines[0], font=font)
        line_height = bbox[3] - bbox[1]
        # Increased line spacing for better readability (from 4px to 6px)
        total_text_height = len(lines) * line_height + (len(lines) - 1) * 6

        # Center text vertically in text area (accounting for top padding)
        text_area_start_y = top_padding + img_height
        text_start_y = text_area_start_y + (text_area_height - total_text_height) // 2

        # Draw each line
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]

            # Center text horizontally
            text_x = (img_width - line_width) // 2
            text_y = text_start_y + i * (line_height + 6)  # Updated line spacing

            # Draw the text in Amazon blue
            draw.text((text_x, text_y), line, fill=AMAZON_BLUE, font=font)

    return card_image


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

