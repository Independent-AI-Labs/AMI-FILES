"""Image extractor for various image formats."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, ClassVar

import pytesseract
from files.backend.extractors.base import DocumentExtractor, ExtractionResult
from PIL import Image
from PIL.ExifTags import TAGS

logger = logging.getLogger(__name__)


class ImageExtractor(DocumentExtractor):
    """Extract metadata and content from images"""

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
        ".svg",
        ".ico",
    }

    async def can_extract(self, file_path: Path) -> bool:
        """Check if this extractor can handle the given file"""
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    async def extract(
        self, file_path: Path, options: dict[str, Any] | None = None
    ) -> ExtractionResult:
        """Extract metadata from image"""
        start_time = time.time()
        options = options or {}

        # Validate file
        await self.validate_file(file_path)

        file_ext = file_path.suffix.lower()

        result = ExtractionResult(
            file_path=str(file_path),
            file_type=file_ext[1:],  # Remove the dot
            file_size=file_path.stat().st_size,
            extraction_method="Pillow",
            processing_time_ms=0,
        )

        try:
            with Image.open(file_path) as img:
                # Basic metadata
                result.title = file_path.stem

                # Image dimensions and format
                image_info = {
                    "name": file_path.name,
                    "dimensions": {"width": img.width, "height": img.height},
                    "mime_type": f"image/{img.format.lower()}"
                    if img.format
                    else f"image/{file_ext[1:]}",
                    "mode": img.mode,  # RGB, RGBA, L, etc.
                    "format": img.format,
                    "file_size": file_path.stat().st_size,
                }

                # Extract EXIF data if available
                exif_data = {}
                if hasattr(img, "getexif"):
                    exif = img.getexif()
                    if exif:
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            exif_data[tag] = self._clean_exif_value(value)

                    image_info["exif"] = exif_data

                    # Extract common EXIF fields
                    if "Artist" in exif_data:
                        result.author = exif_data["Artist"]
                    if "ImageDescription" in exif_data:
                        image_info["description"] = exif_data["ImageDescription"]
                    if "Copyright" in exif_data:
                        image_info["copyright"] = exif_data["Copyright"]
                    if "DateTime" in exif_data:
                        image_info["date_taken"] = exif_data["DateTime"]
                    if "Make" in exif_data:
                        image_info["camera_make"] = exif_data["Make"]
                    if "Model" in exif_data:
                        image_info["camera_model"] = exif_data["Model"]

                # Get image info dict if available
                if hasattr(img, "info"):
                    for key, value in img.info.items():
                        if key not in ["exif", "icc_profile"]:  # Skip binary data
                            image_info[key] = str(value)

                result.images = [image_info]

                # Create a section with image information
                content_lines = [
                    f"Image: {file_path.name}",
                    f"Dimensions: {img.width}x{img.height}",
                    f"Format: {img.format}",
                    f"Mode: {img.mode}",
                    f"File Size: {file_path.stat().st_size:,} bytes",
                ]

                if exif_data:
                    content_lines.append("\nEXIF Data:")
                    for key, value in list(exif_data.items())[
                        :20
                    ]:  # Limit to first 20 items
                        content_lines.append(f"  {key}: {value}")

                result.sections = [
                    {
                        "level": 1,
                        "title": "Image Metadata",
                        "content": "\n".join(content_lines),
                        "order": 1,
                        "path": "1",
                    }
                ]

                result.full_text = "\n".join(content_lines)

                # Perform OCR if requested
                if options.get("perform_ocr", False):
                    ocr_text = await self._perform_ocr(file_path)
                    if ocr_text:
                        result.sections.append(
                            {
                                "level": 1,
                                "title": "Extracted Text (OCR)",
                                "content": ocr_text,
                                "order": 2,
                                "path": "2",
                            }
                        )
                        result.full_text += f"\n\nExtracted Text:\n{ocr_text}"

        except Exception as e:
            logger.exception(f"Error extracting image {file_path}")
            result.error_messages.append(str(e))

        result.processing_time_ms = int((time.time() - start_time) * 1000)
        return result

    def _clean_exif_value(self, value: Any) -> Any:
        """Clean EXIF value for JSON serialization"""
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except Exception:
                return str(value)
        elif isinstance(value, (tuple, list)):
            return [self._clean_exif_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._clean_exif_value(v) for k, v in value.items()}
        else:
            return str(value)

    async def _perform_ocr(self, file_path: Path) -> str | None:
        """Perform OCR on image to extract text"""
        try:
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)

            return text.strip() if text.strip() else None

        except ImportError:
            logger.debug("pytesseract not installed, skipping OCR")
            return None
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return None
