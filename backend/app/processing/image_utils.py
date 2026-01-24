"""Image manipulation utilities."""
from PIL import Image, ImageDraw, ImageFont, ImageChops
from io import BytesIO
from typing import Tuple, Optional, List


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


def fit_subject_to_canvas(
    image: Image.Image,
    background_color: Tuple[int, int, int] = (255, 255, 255),
    diff_threshold: int = 14,
    margin_ratio: float = 0.06
) -> Image.Image:
    """
    Reduce excessive whitespace by detecting the non-background subject,
    cropping to its bounds, then scaling and centering it back onto the
    original canvas.

    Useful when the subject sits low in frame (common on mobile), which
    otherwise results in a large empty area at the top.
    """
    img = image.convert("RGB") if image.mode != "RGB" else image
    w, h = img.size
    if w <= 0 or h <= 0:
        return img.copy()

    bg = Image.new("RGB", img.size, background_color)
    diff = ImageChops.difference(img, bg).convert("L")
    mask = diff.point(lambda p: 255 if p > diff_threshold else 0)
    bbox = mask.getbbox()
    if not bbox:
        return img.copy()

    left, top, right, bottom = bbox
    pad = int(min(w, h) * 0.01)
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(w, right + pad)
    bottom = min(h, bottom + pad)

    subject = img.crop((left, top, right, bottom))
    sw, sh = subject.size
    if sw <= 0 or sh <= 0:
        return img.copy()

    margin = int(min(w, h) * margin_ratio)
    target_w = max(1, w - (2 * margin))
    target_h = max(1, h - (2 * margin))
    scale = min(target_w / sw, target_h / sh)
    new_w = max(1, int(sw * scale))
    new_h = max(1, int(sh * scale))

    subject_resized = subject.resize((new_w, new_h), Image.LANCZOS)
    out = Image.new("RGB", (w, h), background_color)
    x = (w - new_w) // 2
    y = (h - new_h) // 2
    out.paste(subject_resized, (x, y))
    return out


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
    symbol_number: Optional[str] = None,
    desc1: Optional[str] = None,
    desc2: Optional[str] = None,
    long_description: Optional[str] = None,
    part_number: Optional[str] = None,
    manufacturer: Optional[str] = None,
    padding: int = 20,
    text_area_height_ratio: float = 0.25
) -> Image.Image:
    """
    Create e-commerce card layout with image on top and separate description fields below.

    Layout:
    1. Symbol Number and Part Number (on same line)
    2. Manufacturer
    3. Description 1
    4. Description 2
    5. Long Description

    Args:
        image: PIL Image (product image with white background)
        symbol_number: Part symbol number
        desc1: Primary description
        desc2: Secondary description
        long_description: Long description text
        part_number: Part number
        manufacturer: Manufacturer name
        padding: Padding around text in pixels
        text_area_height_ratio: Height of text area as ratio of image height (0.25 = 25%)

    Returns:
        PIL Image with e-commerce card layout
    """
    # Normalize framing so subject fills the image area better
    framed_image = fit_subject_to_canvas(image)

    def norm(v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    # Build layout lines:
    # 1. Symbol Number and Part Number on same line
    # 2. Manufacturer
    # 3. Description 1
    # 4. Description 2
    # 5. Long Description
    lines: List[str] = []

    sym = norm(symbol_number)
    part_num = norm(part_number)
    manuf = norm(manufacturer)
    description1 = norm(desc1)
    description2 = norm(desc2)
    long_desc = norm(long_description)

    # Line 1: Symbol Number and Part Number on same line
    if sym and part_num:
        lines.append(f"SYMBOL NUMBER: {sym}    PART NUMBER: {part_num}")
    elif sym:
        lines.append(f"SYMBOL NUMBER: {sym}")
    elif part_num:
        lines.append(f"PART NUMBER: {part_num}")

    # Line 2: Manufacturer
    if manuf:
        lines.append(f"MANUFACTURER: {manuf}")

    # Line 3: Description 1
    if description1:
        lines.append(f"DESCRIPTION 1: {description1}")

    # Line 4: Description 2
    if description2:
        lines.append(f"DESCRIPTION 2: {description2}")

    # Line 5: Long Description
    if long_desc:
        lines.append(f"LONG DESCRIPTION: {long_desc}")

    # If nothing to render, return framed image
    if not lines:
        return framed_image.copy()

    # Amazon-style dark gray color for professional look
    TEXT_COLOR = (15, 17, 17)  # #0F1111 - Amazon's standard text color
    
    # Calculate dimensions
    img_width, img_height = framed_image.size

    # Minimal top padding
    top_padding = max(6, int(img_height * 0.012))

    # Larger font sizes for better legibility
    LABEL_FONT_SIZE = 64  # Labels (e.g., "SYMBOL NUMBER:") - increased for legibility
    VALUE_FONT_SIZE = 56  # Values/content text - increased for legibility
    max_text_width = img_width - (padding * 2)

    def wrap_text(text: str, max_width: int, font, draw) -> List[str]:
        """Wrap text to fit within max_width, returning list of lines."""
        if not text:
            return [""]

        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            # Test if adding this word would exceed max width
            test_line = current_line + (" " if current_line else "") + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                current_line = test_line
            else:
                # Word doesn't fit, start new line
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Single word is too long, add it anyway to avoid infinite loop
                    lines.append(word)
                    current_line = ""

        if current_line:
            lines.append(current_line)

        return lines if lines else [""]

    # Load fonts - try bold variants first, then regular
    label_font = None
    value_font = None

    try:
        # Try bold fonts first for labels
        bold_font_paths = [
            "/System/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Arial-Black.ttf",
            "arialbd.ttf",  # Windows Arial Bold
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/arialbd.ttf",
            "/System/Library/Fonts/Helvetica Bold.ttc"
        ]

        # Try regular fonts for fallback
        regular_font_paths = [
            "/System/Library/Fonts/Arial.ttf",
            "arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/arial.ttf",
            "/System/Library/Fonts/Helvetica Neue.ttc"
        ]

        # Load label font (bold, 56px)
        for font_path in bold_font_paths + regular_font_paths:
            try:
                label_font = ImageFont.truetype(font_path, LABEL_FONT_SIZE)
                break
            except:
                continue

        # Load value font (bold, 48px)
        for font_path in bold_font_paths + regular_font_paths:
            try:
                value_font = ImageFont.truetype(font_path, VALUE_FONT_SIZE)
                break
            except:
                continue

        # Fallback to default if needed
        if label_font is None:
            label_font = ImageFont.load_default()
        if value_font is None:
            value_font = ImageFont.load_default()

    except:
        # Ultimate fallback
        label_font = ImageFont.load_default()
        value_font = ImageFont.load_default()

    # Create temporary canvas for text measurement
    temp_image = Image.new("RGB", (img_width, 100), (255, 255, 255))
    temp_draw = ImageDraw.Draw(temp_image)

    # Process each line to separate labels from values and handle word wrapping
    processed_lines: List[Tuple[str, str]] = []  # [(label, value), ...]

    for line in lines:
        # Handle lines with multiple label-value pairs (separated by 4 spaces)
        if "    " in line:
            pairs = line.split("    ")
        else:
            pairs = [line]

        for pair in pairs:
            if ": " in pair:
                label, value = pair.split(": ", 1)
                label = label + ":"
            else:
                # Handle pairs without colon separator
                label = ""
                value = pair
            processed_lines.append((label, value))

    # Calculate label indentation width (width of "LONG DESCRIPTION: " for proper alignment)
    label_indent_bbox = temp_draw.textbbox((0, 0), "LONG DESCRIPTION: ", font=label_font)
    label_indent_width = label_indent_bbox[2] - label_indent_bbox[0]

    # Create drawing instructions for each line with proper word wrapping
    drawing_lines: List[List[Tuple[str, str]]] = []  # [[(text, font_type), ...], ...]

    i = 0
    while i < len(processed_lines):
        label, value = processed_lines[i]

        # Handle combined symbol number/part number line
        if label and value and i + 1 < len(processed_lines):
            next_label, next_value = processed_lines[i + 1]
            if next_label and next_value and (
                ("SYMBOL NUMBER" in label and "PART NUMBER" in next_label) or
                ("PART NUMBER" in label and "SYMBOL NUMBER" in next_label)
            ):
                # Check if the combined line fits, otherwise wrap individual values
                combined_text = f"{label} {value}    {next_label} {next_value}"
                bbox = temp_draw.textbbox((0, 0), combined_text, font=label_font)
                if (bbox[2] - bbox[0]) <= max_text_width:
                    # Fits on one line
                    combined_line = []
                    combined_line.append((label, "label"))
                    combined_line.append((value, "value"))
                    combined_line.append(("    ", "spacer"))
                    combined_line.append((next_label, "label"))
                    combined_line.append((next_value, "value"))
                    drawing_lines.append(combined_line)
                else:
                    # Too long, wrap each value separately
                    # Add symbol number line
                    if value:
                        wrapped_values = wrap_text(value, max_text_width - label_indent_width, value_font, temp_draw)
                        for j, wrapped_value in enumerate(wrapped_values):
                            current_line = []
                            if j == 0:
                                current_line.append((label, "label"))
                            else:
                                current_line.append((f"indent_{label_indent_width}", "indent"))
                            current_line.append((wrapped_value, "value"))
                            drawing_lines.append(current_line)

                    # Add part number line
                    if next_value:
                        wrapped_values = wrap_text(next_value, max_text_width - label_indent_width, value_font, temp_draw)
                        for j, wrapped_value in enumerate(wrapped_values):
                            current_line = []
                            if j == 0:
                                current_line.append((next_label, "label"))
                            else:
                                current_line.append((f"indent_{label_indent_width}", "indent"))
                            current_line.append((wrapped_value, "value"))
                            drawing_lines.append(current_line)

                i += 2
                continue

        # Handle regular description lines with word wrapping
        if label and value:
            # Word wrap the value if it's too long
            wrapped_lines = wrap_text(value, max_text_width - label_indent_width, value_font, temp_draw)
            for j, wrapped_value in enumerate(wrapped_lines):
                current_line = []
                if j == 0:  # First line gets the label
                    current_line.append((label, "label"))
                else:  # Subsequent lines are indented
                    current_line.append((f"indent_{label_indent_width}", "indent"))
                current_line.append((wrapped_value, "value"))
                drawing_lines.append(current_line)
        elif label:
            drawing_lines.append([(label, "label")])
        elif value:
            # Word wrap standalone value
            wrapped_lines = wrap_text(value, max_text_width, value_font, temp_draw)
            for wrapped_value in wrapped_lines:
                drawing_lines.append([(wrapped_value, "value")])

        i += 1

    # Calculate total text height based on drawing lines
    total_text_height = 0
    line_heights = []

    for line_elements in drawing_lines:
        # Find the maximum height needed for this line (use the tallest font)
        max_line_height = 0
        for text, font_type in line_elements:
            if font_type == "label":
                bbox = temp_draw.textbbox((0, 0), "Ag", font=label_font)
                height = bbox[3] - bbox[1]
            elif font_type == "value":
                bbox = temp_draw.textbbox((0, 0), "Ag", font=value_font)
                height = bbox[3] - bbox[1]
            else:  # spacer
                height = 0
            max_line_height = max(max_line_height, height)

        total_text_height += max_line_height
        line_heights.append(max_line_height)

    # Add spacing between lines - increased for better readability
    line_spacing = 18  # More spacing for cleaner look
    if drawing_lines:
        total_text_height += (len(drawing_lines) - 1) * line_spacing

    text_area_height = total_text_height + padding + (padding * 2)  # Extra bottom padding

    # Create final canvas
    card_height = top_padding + img_height + text_area_height
    card_image = Image.new("RGB", (img_width, card_height), (255, 255, 255))

    # Paste framed image
    card_image.paste(framed_image, (0, top_padding))

    # Draw text
    draw = ImageDraw.Draw(card_image)

    if drawing_lines and text_area_height > 0:
        text_area_start_y = top_padding + img_height
        current_y = text_area_start_y  # No top padding - text starts right after image

        for line_idx, line_elements in enumerate(drawing_lines):
            current_x = padding  # Keep horizontal padding

            for text, font_type in line_elements:
                if font_type == "label":
                    font = label_font
                elif font_type == "value":
                    font = value_font
                elif font_type.startswith("indent_"):
                    # Handle indentation for wrapped lines
                    indent_width = int(font_type.split("_")[1])
                    current_x += indent_width
                    continue
                else:  # spacer
                    # For spacers, just advance x position
                    bbox = temp_draw.textbbox((0, 0), text, font=label_font)
                    current_x += (bbox[2] - bbox[0])
                    continue

                draw.text((current_x, current_y), text, fill=TEXT_COLOR, font=font)

                # Advance x position for next element
                bbox = temp_draw.textbbox((0, 0), text, font=font)
                current_x += (bbox[2] - bbox[0])

            current_y += line_heights[line_idx] + line_spacing

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

