"""
CUPS printer service module.

Handles communication with CUPS for printing labels.
"""

import os
import re
import tempfile
from typing import Any, Optional
from PIL import Image
import cups

from .config import DEFAULT_PRINTER_NAME, LABEL_SIZES


_MEDIA_RE = re.compile(r'w(\d+)h(\d+)')


def orient_for_media(image: Image.Image, label_size: str) -> Image.Image:
    """
    Rotate the rendered image 90 degrees when its aspect differs from the media's.

    The CUPS media (``wNNNhNNN``) fixes the paper orientation; a design drawn
    in the other shape is rotated here (clockwise) so it prints as previewed.
    """
    match = _MEDIA_RE.fullmatch(LABEL_SIZES[label_size]['cups'])
    media_w, media_h = int(match.group(1)), int(match.group(2))
    if (image.width > image.height) != (media_w > media_h):
        return image.transpose(Image.Transpose.ROTATE_270)
    return image


class PrinterService:
    """Service for interacting with CUPS printer."""

    def __init__(self, printer_name: str = DEFAULT_PRINTER_NAME):
        """
        Initialize the printer service.

        Args:
            printer_name: Name of the printer in CUPS
        """
        self.printer_name = printer_name
        self._connection: Optional[cups.Connection] = None

    @property
    def connection(self) -> cups.Connection:
        """
        Get or create CUPS connection.

        Returns:
            Active CUPS connection
        """
        if self._connection is None:
            self._connection = cups.Connection()
        return self._connection

    def print_image(
        self,
        image: Image.Image,
        label_size: str,
        copies: int = 1,
        job_title: str = "Label"
    ) -> int:
        """
        Print a label image to the Dymo printer.

        Args:
            image: PIL Image to print
            label_size: Label size code (e.g., '11354')
            copies: Number of copies to print
            job_title: Title for the print job

        Returns:
            CUPS job ID

        Raises:
            ValueError: If label_size is not recognized
            RuntimeError: If printing fails
        """
        if label_size not in LABEL_SIZES:
            raise ValueError(f"Unknown label size: {label_size}")

        # Save image (rotated to the media's aspect) to temporary file
        tmp_path = self._save_temp_image(orient_for_media(image, label_size))

        try:
            # Get print options
            options = self._get_print_options(label_size, copies)

            # Submit print job
            job_id = self.connection.printFile(
                self.printer_name,
                tmp_path,
                job_title,
                options
            )

            return job_id

        except Exception as e:
            raise RuntimeError(f"Failed to print: {str(e)}") from e

        finally:
            # Clean up temporary file
            self._cleanup_temp_file(tmp_path)

    def _save_temp_image(self, image: Image.Image) -> str:
        """
        Save image to a temporary file.

        Args:
            image: PIL Image to save

        Returns:
            Path to temporary file
        """
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            image.save(tmp.name, 'PNG')
            return tmp.name

    def _cleanup_temp_file(self, path: str) -> None:
        """
        Remove temporary file.

        Args:
            path: Path to file to remove
        """
        try:
            os.unlink(path)
        except OSError:
            pass  # Ignore errors during cleanup

    def _get_print_options(self, label_size: str, copies: int) -> dict[str, str]:
        """
        Get CUPS print options for the specified label.

        Args:
            label_size: Label size code
            copies: Number of copies

        Returns:
            Dictionary of CUPS print options
        """
        size_info = LABEL_SIZES[label_size]

        return {
            'media': size_info['cups'],
            'fit-to-page': 'True',
            # portrait, no CUPS auto-rotation: the image is already oriented
            'orientation-requested': '3',
            'copies': str(copies)
        }

    def get_printer_status(self) -> dict[str, Any]:
        """
        Get the current status of the printer.

        Returns:
            Dictionary with printer status information
        """
        try:
            printers = self.connection.getPrinters()
            if self.printer_name in printers:
                return printers[self.printer_name]
            return {'error': 'Printer not found'}
        except Exception as e:
            return {'error': str(e)}
