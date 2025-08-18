"""PDF document extractor using PyMuPDF."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, ClassVar

from .base import DocumentExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class PDFExtractor(DocumentExtractor):
    """Extract content from PDF documents using PyMuPDF"""

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {".pdf"}

    async def can_extract(self, file_path: Path) -> bool:
        """Check if this extractor can handle the given file"""
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    async def extract(
        self, file_path: Path, options: dict[str, Any] | None = None
    ) -> ExtractionResult:
        """Extract content from PDF"""
        start_time = time.time()
        options = options or {}

        # Validate file
        await self.validate_file(file_path)

        result = ExtractionResult(
            file_path=str(file_path),
            file_type="pdf",
            file_size=file_path.stat().st_size,
            extraction_method="PyMuPDF",
            processing_time_ms=0,
        )

        try:
            import fitz  # PyMuPDF
        except ImportError:
            result.error_messages.append("PyMuPDF not installed")
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            return result

        try:
            # Open PDF with PyMuPDF
            pdf = fitz.open(file_path)

            # Extract metadata
            metadata = pdf.metadata
            if metadata:
                result.title = metadata.get("title", None)
                result.author = metadata.get("author", None)
                result.subject = metadata.get("subject", None)

                # Extract keywords
                keywords_str = metadata.get("keywords", "")
                if keywords_str:
                    result.keywords = [k.strip() for k in keywords_str.split(",")]

            # Extract text from all pages
            full_text = []
            for page_num in range(pdf.page_count):
                try:
                    page = pdf[page_num]
                    text = page.get_text()
                    if text:
                        full_text.append(text)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
                    result.warnings.append(f"Page {page_num}: {e!s}")

            result.full_text = "\n".join(full_text)

            # Extract sections from text
            if result.full_text:
                result.sections = self.extract_sections_from_text(result.full_text)

            # Extract tables if requested
            if options.get("extract_tables", True):
                tables = await self._extract_tables_with_pymupdf(pdf)
                result.tables = tables

            # Extract images if requested
            if options.get("extract_images", False):
                images = await self._extract_images_with_pymupdf(pdf)
                result.images = images

            pdf.close()

        except Exception as e:
            logger.exception(f"Error extracting PDF {file_path}")
            result.error_messages.append(str(e))

        result.processing_time_ms = int((time.time() - start_time) * 1000)
        return result

    async def _extract_tables_with_pymupdf(self, pdf) -> list[dict[str, Any]]:
        """Extract tables using PyMuPDF"""
        tables = []

        try:
            for page_num in range(pdf.page_count):
                page = pdf[page_num]

                # PyMuPDF can find tables in the page
                page_tables = page.find_tables()

                for table_idx, table in enumerate(page_tables):
                    # Extract table data
                    table_data = table.extract()

                    if not table_data or len(table_data) < 2:
                        continue

                    # First row as headers
                    headers = [
                        str(h) if h else f"Column_{i}"
                        for i, h in enumerate(table_data[0])
                    ]

                    # Rest as rows
                    rows = []
                    for row_data in table_data[1:]:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            if i < len(row_data):
                                row_dict[header] = row_data[i]
                        rows.append(row_dict)

                    if rows:
                        table_info = {
                            "name": f"Table_{page_num}_{table_idx}",
                            "headers": headers,
                            "rows": rows,
                            "schema": self.infer_table_schema(headers, rows),
                            "page": page_num,
                        }
                        tables.append(table_info)

        except Exception as e:
            logger.warning(f"Failed to extract tables: {e}")

        return tables

    async def _extract_images_with_pymupdf(self, pdf) -> list[dict[str, Any]]:
        """Extract images from PDF using PyMuPDF"""
        images = []

        try:
            import fitz

            for page_num in range(pdf.page_count):
                page = pdf[page_num]

                # Get list of images in the page
                image_list = page.get_images()

                for img_idx, img in enumerate(image_list):
                    # img is (xref, smask, width, height, bpc, colorspace, ...)
                    xref = img[0]
                    width = img[2]
                    height = img[3]

                    # Get image data
                    pix = fitz.Pixmap(pdf, xref)

                    # Determine image type
                    if pix.colorspace:
                        if pix.n == 1:
                            mime_type = "image/gray"
                        elif pix.n == 3:
                            mime_type = "image/rgb"
                        elif pix.n == 4:
                            mime_type = "image/rgba"
                        else:
                            mime_type = "image/unknown"
                    else:
                        mime_type = "image/unknown"

                    image_info = {
                        "page": page_num,
                        "name": f"Image_{page_num}_{img_idx}",
                        "dimensions": {"width": width, "height": height},
                        "mime_type": mime_type,
                        "xref": xref,
                    }
                    images.append(image_info)

                    pix = None  # Free memory

        except Exception as e:
            logger.warning(f"Failed to extract images: {e}")

        return images
