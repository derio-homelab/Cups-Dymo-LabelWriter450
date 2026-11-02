"""
Configuration for Dymo label sizes and printer settings.
"""

from typing import TypedDict


class LabelSize(TypedDict):
    """Definition of a Dymo label size."""
    name: str
    width_mm: int
    height_mm: int
    cups: str


# Common Dymo label sizes (in mm and CUPS points)
LABEL_SIZES: dict[str, LabelSize] = {
    '11354': {
        'name': '2-1/4" x 1-1/4" (57x32mm) Multipurpose',
        'width_mm': 57,
        'height_mm': 32,
        'cups': 'w162h90'
    },
    '30252': {
        'name': '1-1/8" x 3-1/2" (28x89mm) Address',
        'width_mm': 28,
        'height_mm': 89,
        'cups': 'w79h252'
    },
    '30323': {
        'name': '2-1/8" x 4" (54x101mm) Shipping',
        'width_mm': 54,
        'height_mm': 101,
        'cups': 'w153h286'
    },
    '30256': {
        'name': '2-5/16" x 4" (59x101mm) Shipping',
        'width_mm': 59,
        'height_mm': 101,
        'cups': 'w167h286'
    },
    '99012': {
        'name': '3-1/2" x 1-1/8" (89x36mm) Large Address',
        'width_mm': 89,
        'height_mm': 36,
        'cups': 'w252h102'
    },
}

# Default label size
DEFAULT_LABEL_SIZE = '11354'

# Default printer name in CUPS
DEFAULT_PRINTER_NAME = 'dymo'

# Image generation settings
DEFAULT_DPI = 300
DEFAULT_FONT_SIZE = 40
DEFAULT_FONT_FAMILY = 'DejaVu Sans'
DEFAULT_FONT_BOLD = True
