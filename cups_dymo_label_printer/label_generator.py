"""
Label image generation module.

Handles creation of label images with text, alignment, and proper sizing.
"""

from typing import Literal, Union
from PIL import Image, ImageDraw, ImageFont

from .config import (
    LABEL_SIZES,
    DEFAULT_LABEL_SIZE,
    DEFAULT_DPI,
    DEFAULT_FONT_SIZE,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_BOLD,
)
from . import fonts


AlignmentType = Literal['left', 'center', 'right']


def create_label_image(
    text: str,
    label_size: str = DEFAULT_LABEL_SIZE,
    font_size: int = DEFAULT_FONT_SIZE,
    align: AlignmentType = 'center',
    dpi: int = DEFAULT_DPI
) -> Image.Image:
    """
    Create a label image with the specified text and settings.

    Args:
        text: The text to display on the label
        label_size: The label size code (e.g., '11354')
        font_size: Font size in points
        align: Text alignment ('left', 'center', or 'right')
        dpi: Resolution in dots per inch

    Returns:
        PIL Image object containing the rendered label

    Raises:
        ValueError: If label_size is not recognized
    """
    if label_size not in LABEL_SIZES:
        raise ValueError(f"Unknown label size: {label_size}")

    size_info = LABEL_SIZES[label_size]

    # Convert mm to pixels at specified DPI
    width_px = int(size_info['width_mm'] * dpi / 25.4)
    height_px = int(size_info['height_mm'] * dpi / 25.4)

    # Create image
    img = Image.new('RGB', (width_px, height_px), 'white')
    draw = ImageDraw.Draw(img)

    # Load font
    font = _load_font(font_size)

    # Calculate text position based on alignment
    x_position = _calculate_text_x_position(draw, text, font, width_px, align)
    y_position = _calculate_text_y_position(draw, text, font, height_px)

    # Draw text
    draw.text((x_position, y_position), text, fill='black', font=font)

    return img


def _load_font(font_size: int) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
    """
    Load the font for label text.

    Args:
        font_size: Font size in points

    Returns:
        Font object (TrueType or default)
    """
    return fonts.load(DEFAULT_FONT_FAMILY, DEFAULT_FONT_BOLD, False, font_size)


def _calculate_text_x_position(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont],
    width_px: int,
    align: AlignmentType
) -> int:
    """
    Calculate the x-coordinate for text based on alignment.

    Args:
        draw: ImageDraw object
        text: The text to position
        font: Font object
        width_px: Image width in pixels
        align: Text alignment

    Returns:
        X-coordinate for text placement
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]

    if align == 'left':
        return 20
    elif align == 'center':
        return (width_px - text_width) // 2
    else:  # right
        return width_px - text_width - 20


def _calculate_text_y_position(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont],
    height_px: int
) -> int:
    """
    Calculate the y-coordinate for vertically centered text.

    Args:
        draw: ImageDraw object
        text: The text to position
        font: Font object
        height_px: Image height in pixels

    Returns:
        Y-coordinate for text placement
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    text_height = bbox[3] - bbox[1]
    return (height_px - text_height) // 2
