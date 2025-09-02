"""DOCX document extractor."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, ClassVar

from .base import DocumentExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class DOCXExtractor(DocumentExtractor):
    """Extract content from DOCX documents"""

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {".docx", ".doc"}

    async def can_extract(self, file_path: Path) -> bool:
        """Check if this extractor can handle the given file"""
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    async def extract(
        self, file_path: Path, options: dict[str, Any] | None = None
    ) -> ExtractionResult:
        """Extract content from DOCX"""
        start_time = time.time()
        options = options or {}

        # Validate file
        await self.validate_file(file_path)

        result = ExtractionResult(
            file_path=str(file_path),
            file_type="docx",
            file_size=file_path.stat().st_size,
            extraction_method="python-docx",
            processing_time_ms=0,
        )

        try:
            from docx import Document
        except ImportError:
            result.error_messages.append("python-docx not installed")
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            return result

        try:
            doc = Document(str(file_path))

            # Extract metadata from core properties
            if doc.core_properties:
                result.title = doc.core_properties.title
                result.author = doc.core_properties.author
                result.subject = doc.core_properties.subject
                if doc.core_properties.keywords:
                    result.keywords = [
                        k.strip() for k in doc.core_properties.keywords.split(",")
                    ]
                result.language = doc.core_properties.language or "en"

            # Extract paragraphs and build sections
            sections = []
            current_section = None
            current_content: list[str] = []
            section_counter = 0

            for paragraph in doc.paragraphs:
                # Check if paragraph is a heading
                if paragraph.style and "Heading" in paragraph.style.name:
                    # Save previous section
                    if current_section:
                        current_section["content"] = "\n".join(current_content).strip()
                        sections.append(current_section)

                    # Start new section
                    section_counter += 1
                    level = self._get_heading_level_from_style(paragraph.style.name)
                    current_section = {
                        "level": level,
                        "title": paragraph.text.strip(),
                        "order": section_counter,
                        "path": str(section_counter),
                        "style": paragraph.style.name,
                    }
                    current_content = []
                else:
                    # Add to current section content
                    if paragraph.text.strip():
                        current_content.append(paragraph.text)

            # Save last section
            if current_section:
                current_section["content"] = "\n".join(current_content).strip()
                sections.append(current_section)

            # If no sections found, create from all paragraphs
            if not sections:
                all_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                if all_text:
                    sections.append(
                        {
                            "level": 1,
                            "title": "Document Content",
                            "content": all_text,
                            "order": 1,
                            "path": "1",
                        }
                    )

            result.sections = sections

            # Extract full text
            result.full_text = "\n".join(p.text for p in doc.paragraphs)

            # Extract tables
            if options.get("extract_tables", True):
                tables = await self._extract_tables(doc)
                result.tables = tables

            # Extract images
            if options.get("extract_images", False):
                images = await self._extract_images(doc, file_path)
                result.images = images

        except Exception as e:
            logger.exception(f"Error extracting DOCX {file_path}")
            result.error_messages.append(str(e))

        result.processing_time_ms = int((time.time() - start_time) * 1000)
        return result

    def _get_heading_level_from_style(self, style_name: str) -> int:
        """Extract heading level from style name"""
        if "Heading" not in style_name:
            return 1

        # Try to extract number from style name
        import re

        match = re.search(r"\d+", style_name)
        if match:
            level = int(match.group())
            return min(level, 6)

        return 1

    async def _extract_tables(self, doc: Any) -> list[dict[str, Any]]:
        """Extract tables from document"""
        tables = []

        try:
            for table_idx, table in enumerate(doc.tables):
                # Extract headers from first row
                if len(table.rows) == 0:
                    continue

                headers: list[str] = []
                for cell in table.rows[0].cells:
                    header_text = cell.text.strip()
                    if not header_text:
                        header_text = f"Column_{len(headers)}"
                    headers.append(header_text)

                # Extract data rows
                rows = []
                for row in table.rows[1:]:
                    row_data = {}
                    for idx, cell in enumerate(row.cells):
                        if idx < len(headers):
                            row_data[headers[idx]] = cell.text.strip()
                    if any(row_data.values()):  # Skip empty rows
                        rows.append(row_data)

                if rows:
                    table_data = {
                        "name": f"Table_{table_idx}",
                        "headers": headers,
                        "rows": rows,
                        "schema": self.infer_table_schema(headers, rows),
                    }
                    tables.append(table_data)

        except Exception as e:
            logger.warning(f"Failed to extract tables: {e}")

        return tables

    async def _extract_images(self, doc: Any, file_path: Path) -> list[dict[str, Any]]:
        """Extract images from document"""
        images = []

        try:
            # Access document relationships
            for rel in doc.part.rels.values():
                if "image" in rel.reltype:
                    image_part = rel.target_part

                    # Get image data
                    image_data = image_part.blob

                    # Determine image type from content type
                    content_type = image_part.content_type

                    # Get image filename
                    image_name = image_part.partname.split("/")[-1]

                    image_info = {
                        "name": image_name,
                        "mime_type": content_type,
                        "file_size": len(image_data),
                    }

                    # Try to get dimensions if PIL is available
                    try:
                        import io

                        from PIL import Image

                        img = Image.open(io.BytesIO(image_data))
                        image_info["dimensions"] = {
                            "width": img.width,
                            "height": img.height,
                        }
                    except ImportError:
                        pass
                    except Exception as e:
                        logger.debug(f"Could not get image dimensions: {e}")

                    images.append(image_info)

        except Exception as e:
            logger.warning(f"Failed to extract images: {e}")

        return images
