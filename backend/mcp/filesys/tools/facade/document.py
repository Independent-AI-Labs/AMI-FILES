"""Document processing facade tool."""

from collections.abc import Awaitable, Callable
from typing import Any, Literal

from files.backend.mcp.filesys.tools.document_tools import (
    index_document_tool,
    read_document_tool,
    read_image_tool,
)
from loguru import logger


async def _handle_index(
    path: str,
    extract_tables: bool,
    extract_images: bool,
    storage_backends: list[str] | None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle index action."""
    return await index_document_tool(path, extract_tables, extract_images, storage_backends)


async def _handle_read(
    path: str,
    extraction_template: dict[str, Any] | None,
    extract_tables: bool,
    extract_images: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle read action."""
    return await read_document_tool(path, extraction_template, extract_tables, extract_images)


async def _handle_read_image(
    path: str,
    instruction: str | None,
    perform_ocr: bool,
    extract_chart_data: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle read_image action."""
    return await read_image_tool(path, instruction, perform_ocr, extract_chart_data)


_ACTION_HANDLERS: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
    "index": _handle_index,
    "read": _handle_read,
    "read_image": _handle_read_image,
}


async def document_tool(
    action: Literal["index", "read", "read_image"],
    path: str,
    extraction_template: dict[str, Any] | None = None,
    extract_tables: bool = True,
    extract_images: bool = False,
    storage_backends: list[str] | None = None,
    instruction: str | None = None,
    perform_ocr: bool = True,
    extract_chart_data: bool = False,
) -> dict[str, Any]:
    """Document processing facade.

    Args:
        action: Action to perform (index, read, read_image)
        path: Path to document or image file
        extraction_template: Template for guided extraction
        extract_tables: Whether to extract tables
        extract_images: Whether to extract images
        storage_backends: Storage backends for indexing
        instruction: Analysis instruction
        perform_ocr: Perform OCR on image
        extract_chart_data: Extract chart data

    Returns:
        Dict with action-specific results
    """
    logger.debug(f"document_tool: action={action}, path={path}")

    handler = _ACTION_HANDLERS.get(action)
    if not handler:
        return {"error": f"Unknown action: {action}"}

    return await handler(
        path=path,
        extraction_template=extraction_template,
        extract_tables=extract_tables,
        extract_images=extract_images,
        storage_backends=storage_backends,
        instruction=instruction,
        perform_ocr=perform_ocr,
        extract_chart_data=extract_chart_data,
    )
