"""Document processing handlers for MCP server."""

import logging
import os
import time
from pathlib import Path
from typing import Any

from files.backend.extractors.base import DocumentExtractor
from files.backend.extractors.docx_extractor import DOCXExtractor
from files.backend.extractors.image_extractor import ImageExtractor
from files.backend.extractors.pdf_extractor import PDFExtractor
from files.backend.extractors.spreadsheet_extractor import SpreadsheetExtractor
from files.backend.models.document import (
    Document,
    DocumentImage,
    DocumentSection,
    DocumentTable,
)
from files.backend.services.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


async def index_document_tool(
    path: str,
    extract_tables: bool = True,
    extract_images: bool = False,
    storage_backends: list[str] | None = None,
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

        extractor = await _get_extractor(file_path)
        if not extractor:
            return {"error": f"Unsupported file type: {file_path.suffix}"}

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

        document = _build_document_model(file_path, extraction_result)
        document.section_ids = _build_sections(document.id, extraction_result.sections)

        if extract_tables:
            document.table_ids = _build_tables(document.id, extraction_result.tables)
        if extract_images:
            document.image_ids = _build_images(document.id, extraction_result.images)

        result = _build_index_response(document, start_time, storage_backends)

        if extraction_result.warnings:
            result["warnings"] = extraction_result.warnings

        return result

    except Exception as e:
        logger.exception(f"Error indexing document {path}")
        return {"error": str(e)}


async def read_document_tool(
    path: str,
    extraction_template: dict[str, Any] | None = None,
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
            result["extracted_data"] = _apply_extraction_template(extraction_result, extraction_template)

        return result

    except Exception as e:
        logger.exception(f"Error reading document {path}")
        return {"error": str(e)}


async def read_image_tool(
    path: str,
    instruction: str | None = None,
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
        extraction_result = await extractor.extract(file_path, options={"perform_ocr": perform_ocr})

        if extraction_result.error_messages:
            return {
                "error": "Extraction failed",
                "messages": extraction_result.error_messages,
            }

        result = _build_image_read_response(file_path, extraction_result)
        if instruction:
            await _augment_image_with_gemini(
                result,
                file_path,
                instruction,
                extract_chart_data,
            )

        if extraction_result.warnings:
            result["warnings"] = extraction_result.warnings

        return result

    except Exception as e:
        logger.exception(f"Error analyzing image {path}")
        return {"error": str(e)}


async def _get_extractor(file_path: Path) -> DocumentExtractor | None:
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


def _build_document_model(file_path: Path, extraction_result: Any) -> Document:
    """Construct the in-memory Document model from extraction output."""
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
    assert document.id is not None, "Document should have an ID from StorageModel"
    return document


def _coerce_document_id(document_id: str | int | None) -> str | None:
    """Return a string identifier when provided."""

    if document_id is None:
        return None
    return str(document_id)


def _build_sections(document_id: str | int | None, sections: list[dict[str, Any]]) -> list[str]:
    """Instantiate DocumentSection models and capture their IDs."""
    document_id_str = _coerce_document_id(document_id)
    if document_id_str is None:
        return []

    section_ids: list[str] = []
    for section_data in sections:
        section = DocumentSection(
            document_id=document_id_str,
            level=int(section_data["level"]),
            title=str(section_data["title"]),
            content=str(section_data["content"]),
            order=int(section_data["order"]),
            path=str(section_data["path"]),
        )
        if section.id:
            section_ids.append(section.id)

    return section_ids


def _build_tables(document_id: str | int | None, tables: list[dict[str, Any]]) -> list[str]:
    """Instantiate DocumentTable models and capture their IDs."""
    document_id_str = _coerce_document_id(document_id)
    if document_id_str is None:
        return []

    table_ids: list[str] = []
    for table_data in tables:
        headers = [str(header) for header in table_data.get("headers", [])]
        rows = table_data.get("rows", [])
        safe_rows = [dict(row) for row in rows if isinstance(row, dict)]
        schema_raw = table_data.get("schema", {})
        table_schema = {str(k): str(v) for k, v in schema_raw.items()} if isinstance(schema_raw, dict) else {}

        table = DocumentTable(
            document_id=document_id_str,
            name=table_data.get("name"),
            headers=headers,
            rows=safe_rows,
            table_schema=table_schema,
        )
        if table.id:
            table_ids.append(table.id)

    return table_ids


def _build_images(document_id: str | int | None, images: list[dict[str, Any]]) -> list[str]:
    """Instantiate DocumentImage models and capture their IDs."""
    document_id_str = _coerce_document_id(document_id)
    if document_id_str is None:
        return []

    image_ids: list[str] = []
    for image_data in images:
        file_path = str(image_data.get("file_path") or image_data.get("path") or image_data.get("name") or "")
        mime_type = str(image_data.get("mime_type", ""))
        dimensions_raw = image_data.get("dimensions", {})
        dimensions = {}
        if isinstance(dimensions_raw, dict):
            width = dimensions_raw.get("width")
            height = dimensions_raw.get("height")
            if isinstance(width, int):
                dimensions["width"] = width
            if isinstance(height, int):
                dimensions["height"] = height
        file_size_value = image_data.get("file_size")
        file_size = int(file_size_value) if isinstance(file_size_value, int | float) else None

        chart_data_raw = image_data.get("chart_data")

        image = DocumentImage(
            document_id=document_id_str,
            file_path=file_path,
            mime_type=mime_type,
            dimensions=dimensions,
            file_size=file_size,
            caption=image_data.get("caption") or image_data.get("description"),
            alt_text=image_data.get("alt_text"),
            chart_data=chart_data_raw if isinstance(chart_data_raw, dict) else None,
        )
        if image.id:
            image_ids.append(image.id)

    return image_ids


def _build_index_response(
    document: Document,
    start_time: float,
    storage_backends: list[str] | None,
) -> dict[str, Any]:
    """Create the response payload for document indexing."""
    return {
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
        "storage_backends": storage_backends or ["graph", "vector", "relational", "cache"],
    }


def _apply_extraction_template(extraction_result: Any, template: dict[str, Any]) -> dict[str, Any]:
    """Apply extraction template to results."""
    extracted = {}

    # Simple template application
    # In real implementation, this would be more sophisticated
    for key, pattern in template.items():
        if isinstance(pattern, str):
            # Search for pattern in full text
            if extraction_result.full_text and pattern.lower() in extraction_result.full_text.lower():
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


def _build_image_read_response(file_path: Path, extraction_result: Any) -> dict[str, Any]:
    """Construct the base response payload for image reads."""
    image_info = extraction_result.images[0] if extraction_result.images else {}
    result: dict[str, Any] = {
        "success": True,
        "file_path": str(file_path),
        "file_type": extraction_result.file_type,
        "metadata": image_info,
        "processing_time_ms": extraction_result.processing_time_ms,
    }
    if extraction_result.full_text:
        result["extracted_text"] = extraction_result.full_text
    return result


async def _augment_image_with_gemini(
    result: dict[str, Any],
    file_path: Path,
    instruction: str,
    extract_chart_data: bool,
) -> None:
    """Optionally augment image analysis with Gemini."""
    result["analysis_instruction"] = instruction
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        result["analysis_result"] = {
            "status": "unavailable",
            "message": "Gemini API key not configured. Set GEMINI_API_KEY to enable image analysis.",
        }
        if extract_chart_data:
            result["chart_data"] = {
                "status": "unavailable",
                "message": "Chart data extraction requires the Gemini API key.",
            }
        return

    try:
        async with GeminiClient(gemini_api_key) as client:
            if extract_chart_data:
                chart_analysis = await client.extract_chart_data(file_path)
                result["chart_data"] = {
                    "status": "success",
                    "data": chart_analysis,
                }
            else:
                analysis = await client.analyze_image(file_path, instruction)
                result["analysis_result"] = {
                    "status": "success",
                    "data": analysis,
                }
    except Exception as exc:  # pragma: no cover - network/LLM errors
        logger.exception(f"Gemini analysis failed for {file_path}")
        result["analysis_result"] = {
            "status": "error",
            "message": f"Gemini analysis failed: {exc!s}",
        }
        if extract_chart_data:
            result["chart_data"] = {
                "status": "error",
                "message": f"Chart data extraction failed: {exc!s}",
            }
