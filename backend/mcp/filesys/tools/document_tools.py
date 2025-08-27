"""Document processing handlers for MCP server."""

import logging
import time
from pathlib import Path
from typing import Any, Optional

from files.backend.extractors import (
    DocumentExtractor,
    DOCXExtractor,
    ImageExtractor,
    PDFExtractor,
    SpreadsheetExtractor,
)
from files.backend.models.document import (
    Document,
    DocumentImage,
    DocumentSection,
    DocumentTable,
)

logger = logging.getLogger(__name__)


async def index_document_tool(
    path: str,
    extract_tables: bool = True,
    extract_images: bool = False,
    storage_backends: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Parse and index documents for searchable storage.

    Args:
        path: Path to the document file
        extract_tables: Whether to extract tables
        extract_images: Whether to extract images
        storage_backends: Storage backends to use

    Returns:
        Document metadata and processing results
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            return {"error": f"File not found: {path}"}

        # Select appropriate extractor
        extractor = await _get_extractor(file_path)
        if not extractor:
            return {"error": f"Unsupported file type: {file_path.suffix}"}

        # Extract content
        start_time = time.time()
        extraction_result = await extractor.extract(
            file_path,
            options={
                "extract_tables": extract_tables,
                "extract_images": extract_images,
            },
        )

        if extraction_result.error_messages:
            return {
                "error": "Extraction failed",
                "messages": extraction_result.error_messages,
            }

        # Create Document model
        document = Document(
            file_path=str(file_path),
            file_type=extraction_result.file_type,
            file_size=extraction_result.file_size,
            title=extraction_result.title or file_path.stem,
            author=extraction_result.author,
            subject=extraction_result.subject,
            keywords=extraction_result.keywords,
            language=extraction_result.language,
            extraction_method=extraction_result.extraction_method,
            processing_time_ms=extraction_result.processing_time_ms,
        )

        # Process and store sections
        section_ids = []
        for section_data in extraction_result.sections:
            section = DocumentSection(
                document_id=document.id,
                level=section_data["level"],
                title=section_data["title"],
                content=section_data["content"],
                order=section_data["order"],
                path=section_data["path"],
            )
            # Store section (would use UnifiedCRUD in real implementation)
            section_ids.append(section.id)

        document.section_ids = [sid for sid in section_ids if sid is not None]

        # Process and store tables
        if extract_tables:
            table_ids = []
            for table_data in extraction_result.tables:
                table = DocumentTable(
                    document_id=document.id,
                    name=table_data.get("name"),
                    headers=table_data["headers"],
                    rows=table_data["rows"],
                    schema=table_data.get("schema", {}),
                )
                # Store table (would use UnifiedCRUD in real implementation)
                table_ids.append(table.id)

            document.table_ids = [tid for tid in table_ids if tid is not None]

        # Process and store images
        if extract_images:
            image_ids = []
            for image_data in extraction_result.images:
                image = DocumentImage(
                    document_id=document.id,
                    file_path=image_data.get("name", ""),
                    mime_type=image_data.get("mime_type", ""),
                    dimensions=image_data.get("dimensions", {}),
                )
                # Store image (would use UnifiedCRUD in real implementation)
                image_ids.append(image.id)

            document.image_ids = [iid for iid in image_ids if iid is not None]

        # Store document (would use UnifiedCRUD in real implementation)
        # For now, return the document as dict
        result = {
            "success": True,
            "document_id": document.id,
            "file_path": document.file_path,
            "file_type": document.file_type,
            "title": document.title,
            "author": document.author,
            "sections_count": len(document.section_ids),
            "tables_count": len(document.table_ids),
            "images_count": len(document.image_ids),
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "storage_backends": storage_backends
            or ["graph", "vector", "relational", "cache"],
        }

        if extraction_result.warnings:
            result["warnings"] = extraction_result.warnings

        return result

    except Exception as e:
        logger.exception(f"Error indexing document {path}")
        return {"error": str(e)}


async def read_document_tool(
    path: str,
    extraction_template: Optional[dict[str, Any]] = None,
    extract_tables: bool = True,
    extract_images: bool = False,
) -> dict[str, Any]:
    """Read and parse documents into structured data.

    Args:
        path: Path to the document file
        extraction_template: Optional template for guided extraction
        extract_tables: Whether to extract tables
        extract_images: Whether to extract images

    Returns:
        Structured document representation
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            return {"error": f"File not found: {path}"}

        # Select appropriate extractor
        extractor = await _get_extractor(file_path)
        if not extractor:
            return {"error": f"Unsupported file type: {file_path.suffix}"}

        # Extract content
        extraction_result = await extractor.extract(
            file_path,
            options={
                "extract_tables": extract_tables,
                "extract_images": extract_images,
            },
        )

        if extraction_result.error_messages:
            return {
                "error": "Extraction failed",
                "messages": extraction_result.error_messages,
            }

        # Build response
        result = {
            "success": True,
            "file_path": str(file_path),
            "file_type": extraction_result.file_type,
            "metadata": {
                "title": extraction_result.title,
                "author": extraction_result.author,
                "subject": extraction_result.subject,
                "keywords": extraction_result.keywords,
                "language": extraction_result.language,
            },
            "content": {
                "full_text": extraction_result.full_text,
                "sections": extraction_result.sections,
            },
            "processing_time_ms": extraction_result.processing_time_ms,
        }

        if extract_tables and extraction_result.tables:
            result["tables"] = extraction_result.tables

        if extract_images and extraction_result.images:
            result["images"] = extraction_result.images

        if extraction_result.warnings:
            result["warnings"] = extraction_result.warnings

        # Apply extraction template if provided
        if extraction_template:
            result["extracted_data"] = _apply_extraction_template(
                extraction_result, extraction_template
            )

        return result

    except Exception as e:
        logger.exception(f"Error reading document {path}")
        return {"error": str(e)}


async def read_image_tool(
    path: str,
    instruction: Optional[str] = None,
    perform_ocr: bool = True,
    extract_chart_data: bool = False,
) -> dict[str, Any]:
    """Analyze images using multimodal LLM.

    Args:
        path: Path to the image file
        instruction: Analysis instruction or template
        perform_ocr: Perform OCR (automatic with Gemini)
        extract_chart_data: Extract data from charts/graphs

    Returns:
        Image analysis results
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            return {"error": f"File not found: {path}"}

        # Use image extractor for metadata
        extractor = ImageExtractor()
        if not await extractor.can_extract(file_path):
            return {"error": f"Not an image file: {file_path.suffix}"}

        # Extract image metadata
        extraction_result = await extractor.extract(
            file_path, options={"perform_ocr": perform_ocr}
        )

        if extraction_result.error_messages:
            return {
                "error": "Extraction failed",
                "messages": extraction_result.error_messages,
            }

        # Get image info
        image_info = extraction_result.images[0] if extraction_result.images else {}

        # Build response
        result = {
            "success": True,
            "file_path": str(file_path),
            "file_type": extraction_result.file_type,
            "metadata": image_info,
            "processing_time_ms": extraction_result.processing_time_ms,
        }

        # Add OCR text if extracted
        if extraction_result.full_text:
            result["extracted_text"] = extraction_result.full_text

        # Placeholder for Gemini integration
        if instruction:
            result["analysis_instruction"] = instruction
            result["analysis_result"] = {
                "status": "pending",
                "message": "Gemini integration not yet implemented. Will analyze with instruction: "
                + instruction,
            }

            if extract_chart_data:
                result["chart_data"] = {
                    "status": "pending",
                    "message": "Chart data extraction will be performed via Gemini",
                }

        if extraction_result.warnings:
            result["warnings"] = extraction_result.warnings

        return result

    except Exception as e:
        logger.exception(f"Error analyzing image {path}")
        return {"error": str(e)}


async def _get_extractor(file_path: Path) -> Optional[DocumentExtractor]:
    """Get appropriate extractor for file type."""
    extractors = [
        PDFExtractor(),
        DOCXExtractor(),
        SpreadsheetExtractor(),
        ImageExtractor(),
    ]

    for extractor in extractors:
        if await extractor.can_extract(file_path):
            return extractor

    return None


def _apply_extraction_template(
    extraction_result: Any, template: dict[str, Any]
) -> dict[str, Any]:
    """Apply extraction template to results."""
    extracted = {}

    # Simple template application
    # In real implementation, this would be more sophisticated
    for key, pattern in template.items():
        if isinstance(pattern, str):
            # Search for pattern in full text
            if (
                extraction_result.full_text
                and pattern.lower() in extraction_result.full_text.lower()
            ):
                # Extract surrounding context
                text = extraction_result.full_text
                idx = text.lower().find(pattern.lower())
                start = max(0, idx - 50)
                end = min(len(text), idx + len(pattern) + 50)
                extracted[key] = text[start:end].strip()
        elif isinstance(pattern, dict):
            # More complex extraction logic
            extracted[key] = {"status": "template_processing_pending"}

    return extracted
