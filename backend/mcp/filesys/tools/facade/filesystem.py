"""Filesystem operations facade tool."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from files.backend.mcp.filesys.tools.filesystem_tools import (
    create_dirs_tool,
    delete_paths_tool,
    find_paths_tool,
    list_dir_tool,
    modify_file_tool,
    read_from_file_tool,
    replace_in_file_tool,
    write_to_file_tool,
)
from loguru import logger


async def _handle_list(
    root_dir: Path,
    path: str | None,
    recursive: bool,
    pattern: str | None,
    limit: int,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle list action."""
    return await list_dir_tool(root_dir, path or ".", recursive, pattern, limit)


async def _handle_create(root_dir: Path, paths: list[str] | None, **_kwargs: Any) -> dict[str, Any]:
    """Handle create action."""
    if not paths:
        return {"error": "paths required for create action"}
    return await create_dirs_tool(root_dir, paths)


async def _handle_find(
    root_dir: Path,
    patterns: list[str] | None,
    path: str | None,
    keywords_path_name: list[str] | None,
    keywords_file_content: list[str] | None,
    regex_keywords: bool,
    use_fast_search: bool,
    max_workers: int,
    recursive: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle find action."""
    return await find_paths_tool(
        root_dir,
        patterns,
        path or ".",
        keywords_path_name,
        keywords_file_content,
        regex_keywords,
        use_fast_search,
        max_workers,
        recursive,
    )


async def _handle_read(
    root_dir: Path,
    path: str | None,
    start_line: int | None,
    end_line: int | None,
    start_offset_inclusive: int,
    end_offset_inclusive: int,
    offset_type: str,
    output_format: str,
    file_encoding: str,
    add_line_numbers: bool | None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle read action."""
    if not path:
        return {"error": "path required for read action"}
    return await read_from_file_tool(
        root_dir,
        path,
        start_line,
        end_line,
        start_offset_inclusive,
        end_offset_inclusive,
        offset_type,
        output_format,
        file_encoding,
        add_line_numbers,
    )


async def _handle_write(
    root_dir: Path,
    path: str | None,
    content: str | None,
    mode: str,
    input_format: str,
    file_encoding: str,
    validate_with_llm: bool,
    session_id: str | None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle write action."""
    if not path:
        return {"error": "path required for write action"}
    if content is None:
        return {"error": "content required for write action"}
    return await write_to_file_tool(
        root_dir,
        path,
        content,
        mode,
        input_format,
        file_encoding,
        validate_with_llm,
        session_id,
    )


async def _handle_delete(root_dir: Path, paths: list[str] | None, **_kwargs: Any) -> dict[str, Any]:
    """Handle delete action."""
    if not paths:
        return {"error": "paths required for delete action"}
    return await delete_paths_tool(root_dir, paths)


async def _handle_modify(
    root_dir: Path,
    path: str | None,
    start_offset_inclusive: int,
    end_offset_inclusive: int,
    new_content: str | None,
    offset_type: str,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle modify action."""
    if not path:
        return {"error": "path required for modify action"}
    if new_content is None:
        return {"error": "new_content required for modify action"}
    return await modify_file_tool(
        root_dir,
        path,
        start_offset_inclusive,
        end_offset_inclusive,
        new_content,
        offset_type,
    )


async def _handle_replace(
    root_dir: Path,
    path: str | None,
    old_content: str | None,
    new_content: str | None,
    is_regex: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle replace action."""
    if not path:
        return {"error": "path required for replace action"}
    if old_content is None:
        return {"error": "old_content required for replace action"}
    if new_content is None:
        return {"error": "new_content required for replace action"}
    return await replace_in_file_tool(root_dir, path, old_content, new_content, is_regex)


_ACTION_HANDLERS: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
    "list": _handle_list,
    "create": _handle_create,
    "find": _handle_find,
    "read": _handle_read,
    "write": _handle_write,
    "delete": _handle_delete,
    "modify": _handle_modify,
    "replace": _handle_replace,
}


async def filesystem_tool(
    root_dir: Path,
    action: Literal["list", "create", "find", "read", "write", "delete", "modify", "replace"],
    path: str | None = None,
    paths: list[str] | None = None,
    content: str | None = None,
    recursive: bool = False,
    pattern: str | None = None,
    limit: int = 100,
    patterns: list[str] | None = None,
    keywords_path_name: list[str] | None = None,
    keywords_file_content: list[str] | None = None,
    regex_keywords: bool = False,
    use_fast_search: bool = True,
    max_workers: int = 8,
    start_line: int | None = None,
    end_line: int | None = None,
    start_offset_inclusive: int = 0,
    end_offset_inclusive: int = -1,
    offset_type: str = "line",
    output_format: str = "raw_utf8",
    file_encoding: str = "utf-8",
    add_line_numbers: bool | None = None,
    mode: str = "text",
    input_format: str = "raw_utf8",
    validate_with_llm: bool = True,
    session_id: str | None = None,
    new_content: str | None = None,
    old_content: str | None = None,
    is_regex: bool = False,
) -> dict[str, Any]:
    """Filesystem operations facade.

    Args:
        root_dir: Root directory for operations
        action: Action to perform
        path: File or directory path
        paths: List of paths
        content: File content
        recursive: Recursive directory listing
        pattern: Glob pattern for filtering
        limit: Maximum results to return
        patterns: List of glob patterns
        keywords_path_name: Keywords to search in paths
        keywords_file_content: Keywords to search in file contents
        regex_keywords: Treat keywords as regex
        use_fast_search: Use optimized search algorithm
        max_workers: Maximum parallel workers
        start_line: Start line number
        end_line: End line number
        start_offset_inclusive: Start offset
        end_offset_inclusive: End offset
        offset_type: Offset type (line or byte)
        output_format: Output format
        file_encoding: File encoding
        add_line_numbers: Add line numbers to output
        mode: Write mode (text or binary)
        input_format: Input format for content
        validate_with_llm: Run LLM validation for Python files
        session_id: Session ID for validation context
        new_content: New content
        old_content: Content to replace
        is_regex: Treat old_content as regex

    Returns:
        Dict with action-specific results
    """
    logger.debug(f"filesystem_tool: action={action}, path={path}")

    handler = _ACTION_HANDLERS.get(action)
    if not handler:
        return {"error": f"Unknown action: {action}"}

    return await handler(
        root_dir=root_dir,
        path=path,
        paths=paths,
        content=content,
        recursive=recursive,
        pattern=pattern,
        limit=limit,
        patterns=patterns,
        keywords_path_name=keywords_path_name,
        keywords_file_content=keywords_file_content,
        regex_keywords=regex_keywords,
        use_fast_search=use_fast_search,
        max_workers=max_workers,
        start_line=start_line,
        end_line=end_line,
        start_offset_inclusive=start_offset_inclusive,
        end_offset_inclusive=end_offset_inclusive,
        offset_type=offset_type,
        output_format=output_format,
        file_encoding=file_encoding,
        add_line_numbers=add_line_numbers,
        mode=mode,
        input_format=input_format,
        validate_with_llm=validate_with_llm,
        session_id=session_id,
        new_content=new_content,
        old_content=old_content,
        is_regex=is_regex,
    )
