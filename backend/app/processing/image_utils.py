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
    location: Optional[str] = None,
    desc1: Optional[str] = None,
    desc2: Optional[str] = None,
    long_description: Optional[str] = None,
    padding: int = 20,
    text_area_height_ratio: float = 0.25
) -> Image.Image:
    """
    Create e-commerce card layout with image on top and separate description fields below.

    Args:
        image: PIL Image (product image with white background)
        symbol_number: Part symbol number
        location: Part location
        desc1: Primary description
        desc2: Secondary description
        long_description: Long description text
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

    # Build requested lines with formatting:
    #  - Line 1: Symbol Number and Location on same line (if both exist)
    #  - Line 2+: each description on its own line
    lines: List[str] = []
    sym = norm(symbol_number)
    loc = norm(location)
    if sym or loc:
        if sym and loc:
            lines.append(f"SYMBOL NUMBER: {sym}    LOCATION: {loc}")
        elif sym:
            lines.append(f"SYMBOL NUMBER: {sym}")
        else:
            lines.append(f"LOCATION: {loc}")
    if norm(desc1):
        lines.append(f"DESCRIPTION 1: {norm(desc1)}")
    if norm(desc2):
        lines.append(f"DESCRIPTION 2: {norm(desc2)}")
    if norm(long_description):
        lines.append(f"LONG DESCRIPTION: {norm(long_description)}")

    # If nothing to render, return framed image
    if not lines:
        return framed_image.copy()

    # Brand blue color
    BRAND_BLUE = (33, 98, 161)  # #2162a1

    # Calculate dimensions
    img_width, img_height = framed_image.size

    # Minimal top padding
    top_padding = max(6, int(img_height * 0.012))

    # Fixed larger font sizes for better readability
    LABEL_FONT_SIZE = 56  # Labels like "SYMBOL NUMBER:", "LOCATION:", etc. (bigger than values)
    VALUE_FONT_SIZE = 48  # Values/content text
    max_text_width = img_width - (padding * 2)

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

    # Word-wrap each line independently and collect all text elements
    all_text_elements: List[Tuple[str, str, str]] = []  # [(text, font_type, alignment_key), ...]

    for label, value in processed_lines:
        # Handle label (56px, tight line height)
        if label:
            # Word wrap label if needed
            label_words = label.split()
            current_label = ""
            for word in label_words:
                test = current_label + (" " if current_label else "") + word
                bbox = temp_draw.textbbox((0, 0), test, font=label_font)
                if (bbox[2] - bbox[0]) <= max_text_width:
                    current_label = test
                else:
                    if current_label:
                        all_text_elements.append((current_label, "label", f"label_{len(all_text_elements)}"))
                        current_label = word
                    else:
                        all_text_elements.append((word, "label", f"label_{len(all_text_elements)}"))
                        current_label = ""
            if current_label:
                all_text_elements.append((current_label, "label", f"label_{len(all_text_elements)}"))

        # Handle value (48px, slightly relaxed line height)
        if value:
            # Word wrap value if needed
            value_words = value.split()
            current_value = ""
            for word in value_words:
                test = current_value + (" " if current_value else "") + word
                bbox = temp_draw.textbbox((0, 0), test, font=value_font)
                if (bbox[2] - bbox[0]) <= max_text_width:
                    current_value = test
                else:
                    if current_value:
                        all_text_elements.append((current_value, "value", f"value_{len(all_text_elements)}"))
                        current_value = word
                    else:
                        all_text_elements.append((word, "value", f"value_{len(all_text_elements)}"))
                        current_value = ""
            if current_value:
                all_text_elements.append((current_value, "value", f"value_{len(all_text_elements)}"))

    # Calculate total text height with different line heights
    total_text_height = 0
    line_heights = []

    for text, font_type, _ in all_text_elements:
        if font_type == "label":
            bbox = temp_draw.textbbox((0, 0), "Ag", font=label_font)
            line_height = bbox[3] - bbox[1]
            # Tight line height for labels
            total_text_height += line_height
            line_heights.append(line_height)
        else:  # value
            bbox = temp_draw.textbbox((0, 0), "Ag", font=value_font)
            line_height = bbox[3] - bbox[1]
            # Slightly relaxed line height for values (1.2x)
            adjusted_height = int(line_height * 1.2)
            total_text_height += adjusted_height
            line_heights.append(adjusted_height)

    # Add spacing between elements
    element_spacing = 8
    if all_text_elements:
        total_text_height += (len(all_text_elements) - 1) * element_spacing

    text_area_height = total_text_height + (padding * 2)

    # Create final canvas
    card_height = top_padding + img_height + text_area_height
    card_image = Image.new("RGB", (img_width, card_height), (255, 255, 255))

    # Paste framed image
    card_image.paste(framed_image, (0, top_padding))

    # Draw text
    draw = ImageDraw.Draw(card_image)

    if all_text_elements and text_area_height > 0:
        text_area_start_y = top_padding + img_height
        current_y = text_area_start_y + padding

        for i, (text, font_type, _) in enumerate(all_text_elements):
            font = label_font if font_type == "label" else value_font
            draw.text((padding, current_y), text, fill=BRAND_BLUE, font=font)
            current_y += line_heights[i] + element_spacing

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

