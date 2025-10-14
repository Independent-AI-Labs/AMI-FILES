"""Image extractor for various image formats."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, ClassVar

from files.backend.extractors.base import DocumentExtractor, ExtractionResult
from files.backend.services.gemini_client import GeminiClient
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

    async def extract(self, file_path: Path, options: dict[str, Any] | None = None) -> ExtractionResult:
        """Extract metadata from image"""
        start_time = time.time()
        options = options or {}

        # Validate file
        await self.validate_file(file_path)

        result = self._create_result(file_path)

        try:
            with Image.open(file_path) as img:
                image_info = self._build_image_info(img, file_path)
                exif_data = self._extract_exif_data(img)
                self._apply_exif_metadata(result, image_info, exif_data)
                self._enrich_with_image_info(result, image_info, img.info)

                metadata_section = self._build_metadata_section(file_path, img, exif_data)
                result.sections = [metadata_section]
                result.full_text = metadata_section["content"]

                if options.get("perform_ocr", False):
                    await self._append_ocr_section(result, file_path)

        except Exception as e:
            logger.exception(f"Error extracting image {file_path}")
            result.error_messages.append(str(e))

        result.processing_time_ms = int((time.time() - start_time) * 1000)
        return result

    def _create_result(self, file_path: Path) -> ExtractionResult:
        """Build the base ExtractionResult payload."""
        file_ext = file_path.suffix.lower().lstrip(".")
        return ExtractionResult(
            file_path=str(file_path),
            file_type=file_ext,
            file_size=file_path.stat().st_size,
            extraction_method="Pillow",
            title=file_path.stem,
            processing_time_ms=0,
        )

    def _build_image_info(self, img: Image.Image, file_path: Path) -> dict[str, Any]:
        """Collect core image metadata."""
        return {
            "name": file_path.name,
            "dimensions": {"width": img.width, "height": img.height},
            "mime_type": f"image/{(img.format or file_path.suffix.lstrip('.')).lower()}",
            "mode": img.mode,
            "format": img.format,
            "file_size": file_path.stat().st_size,
        }

    def _extract_exif_data(self, img: Image.Image) -> dict[str, Any]:
        """Return EXIF metadata if available."""
        exif_data: dict[str, Any] = {}
        if not hasattr(img, "getexif"):
            return exif_data

        exif = img.getexif()
        if not exif:
            return exif_data

        for tag_id, value in exif.items():
            tag_name = str(TAGS.get(tag_id, tag_id))
            exif_data[tag_name] = self._clean_exif_value(value)
        return exif_data

    def _apply_exif_metadata(
        self,
        result: ExtractionResult,
        image_info: dict[str, Any],
        exif_data: dict[str, Any],
    ) -> None:
        """Attach EXIF-derived metadata to the result and image."""
        if not exif_data:
            return

        image_info["exif"] = exif_data
        result.title = result.title or image_info["name"].rsplit(".", 1)[0]
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

    def _enrich_with_image_info(
        self,
        result: ExtractionResult,
        image_info: dict[str, Any],
        image_metadata: dict[str, Any] | None,
    ) -> None:
        """Store image info and preserve extra metadata."""
        if image_metadata:
            for key, value in image_metadata.items():
                if key in {"exif", "icc_profile"}:
                    continue
                image_info[key] = str(value)

        result.title = result.title or image_info["name"].rsplit(".", 1)[0]
        result.images = [image_info]

    def _build_metadata_section(
        self,
        file_path: Path,
        img: Image.Image,
        exif_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create the primary metadata section for the image."""
        content_lines = [
            f"Image: {file_path.name}",
            f"Dimensions: {img.width}x{img.height}",
            f"Format: {img.format}",
            f"Mode: {img.mode}",
            f"File Size: {file_path.stat().st_size:,} bytes",
        ]

        if exif_data:
            content_lines.append("\nEXIF Data:")
            for key, value in list(exif_data.items())[:20]:
                content_lines.append(f"  {key}: {value}")

        return {
            "level": 1,
            "title": "Image Metadata",
            "content": "\n".join(content_lines),
            "order": 1,
            "path": "1",
        }

    async def _append_ocr_section(self, result: ExtractionResult, file_path: Path) -> None:
        """Perform OCR and append extracted text to the result."""
        ocr_text = await self._perform_ocr(file_path)
        if not ocr_text:
            return

        result.sections.append(
            {
                "level": 1,
                "title": "Extracted Text (OCR)",
                "content": ocr_text,
                "order": len(result.sections) + 1,
                "path": str(len(result.sections) + 1),
            }
        )
        result.full_text = f"{result.full_text}\n\nExtracted Text:\n{ocr_text}" if result.full_text else ocr_text

    def _clean_exif_value(self, value: Any) -> Any:
        """Clean EXIF value for JSON serialization"""
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except Exception:
                return str(value)
        elif isinstance(value, tuple | list):
            return [self._clean_exif_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._clean_exif_value(v) for k, v in value.items()}
        else:
            return str(value)

    async def _perform_ocr(self, file_path: Path) -> str | None:
        """Perform OCR on image to extract text"""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.debug("GEMINI_API_KEY not set, skipping LLM OCR")
            return None

        prompt = "Extract every piece of textual content that appears inside this image. Return the raw text only without additional commentary or formatting."

        try:
            async with GeminiClient(api_key) as client:
                response = await client.analyze_image(file_path, prompt=prompt)
        except Exception as exc:  # Network or provider failures
            logger.warning(f"Gemini OCR failed: {exc}")
            return None

        text = response.get("response")
        return text.strip() if isinstance(text, str) and text.strip() else None
