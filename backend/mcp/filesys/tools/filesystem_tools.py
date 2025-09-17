"""Filesystem tool functions for Filesys MCP server."""

import re
import shutil
from pathlib import Path
from typing import Any

from files.backend.mcp.filesys.utils.fast_search import FastFileSearcher
from files.backend.mcp.filesys.utils.file_utils import (
    FileUtils,
    InputFormat,
    OffsetType,
    OutputFormat,
)
from files.backend.mcp.filesys.utils.path_utils import validate_path
from files.backend.mcp.filesys.utils.precommit_validator import PreCommitValidator
from loguru import logger

LINE_BREAK = "\n"


async def list_dir_tool(
    root_dir: Path,
    path: str = ".",
    recursive: bool = False,
    pattern: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List directory contents."""
    logger.debug(f"Listing directory: path={path}, recursive={recursive}, pattern={pattern}, limit={limit}")

    try:
        # Validate and resolve the path
        safe_path = validate_path(root_dir, path, allow_write=False)

        if not safe_path.exists():
            return {"error": f"Path does not exist: {path}"}

        if not safe_path.is_dir():
            return {"error": f"Path is not a directory: {path}"}

        items = []
        count = 0

        if recursive:
            # Recursive listing
            for item in safe_path.rglob(pattern or "*"):
                if count >= limit:
                    break
                rel_path = item.relative_to(root_dir)
                items.append(
                    {
                        "path": str(rel_path),
                        "type": "dir" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None,
                    }
                )
                count += 1
        else:
            # Non-recursive listing
            for item in safe_path.glob(pattern or "*"):
                if count >= limit:
                    break
                rel_path = item.relative_to(root_dir)
                items.append(
                    {
                        "path": str(rel_path),
                        "type": "dir" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None,
                    }
                )
                count += 1

        return {
            "success": True,
            "items": items,
            "total_found": count,
            "limit_reached": count >= limit,
        }

    except Exception as e:
        logger.error(f"Failed to list directory {path}: {e}")
        return {"error": str(e)}


async def create_dirs_tool(root_dir: Path, paths: list[str]) -> dict[str, Any]:
    """Create directories."""
    logger.debug(f"Creating directories: {paths}")

    try:
        created = []
        for path_str in paths:
            safe_path = validate_path(root_dir, path_str, allow_write=False)
            safe_path.mkdir(parents=True, exist_ok=True)
            created.append(str(safe_path.relative_to(root_dir)))

        return {"success": True, "created": created}
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        return {"error": str(e)}


async def find_paths_tool(
    root_dir: Path,
    patterns: list[str] | None = None,
    path: str = ".",
    keywords_path_name: list[str] | None = None,
    keywords_file_content: list[str] | None = None,
    regex_keywords: bool = False,
    use_fast_search: bool = True,
    max_workers: int = 8,
    recursive: bool = True,
) -> dict[str, Any]:
    """Find paths matching patterns or keywords."""
    logger.debug(f"Finding paths: patterns={patterns}, path={path}, recursive={recursive}")

    try:
        validated_path = validate_path(root_dir, path)

        if not validated_path.is_dir():
            return {"error": f"Path is not a directory: {path}"}

        matches: list[str] = []
        if patterns:
            matches.extend(_collect_pattern_matches(root_dir, validated_path, patterns, recursive))

        if keywords_path_name or keywords_file_content:
            keywords = await _collect_keyword_matches(
                root_dir,
                validated_path,
                keywords_path_name,
                keywords_file_content,
                regex_keywords,
                use_fast_search,
                max_workers,
            )
            matches.extend(keywords)

        return {"success": True, "paths": matches, "total_found": len(matches)}
    except Exception as e:
        logger.error(f"Failed to find paths: {e}")
        return {"error": str(e)}


async def read_from_file_tool(
    root_dir: Path,
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
    start_offset_inclusive: int = 0,
    end_offset_inclusive: int = -1,
    offset_type: str = "line",
    output_format: str = "raw_utf8",
    file_encoding: str = "utf-8",
    add_line_numbers: bool | None = None,
) -> dict[str, Any]:
    """Read file contents with advanced options."""
    logger.debug(f"Reading file: path={path}")

    try:
        safe_path = validate_path(root_dir, path, allow_write=False)

        if not safe_path.exists():
            return {"error": f"File does not exist: {path}"}

        if not safe_path.is_file():
            return {"error": f"Path is not a file: {path}"}

        # Check file size
        FileUtils.check_file_size(safe_path)

        is_binary = not FileUtils.is_text_file(safe_path)
        add_line_numbers = _resolve_line_number_hint(add_line_numbers, safe_path)

        offset_enum, start_offset_inclusive, end_offset_inclusive = _resolve_offsets(
            offset_type,
            start_offset_inclusive,
            end_offset_inclusive,
            start_line,
            end_line,
            is_binary,
        )
        output_enum = OutputFormat[output_format.replace("-", "_").upper()]

        content = _read_file_segment(
            safe_path,
            offset_enum,
            start_offset_inclusive,
            end_offset_inclusive,
            file_encoding,
            add_line_numbers,
        )

        result_content = _encode_read_content(content, output_enum, is_binary, file_encoding)

        return {
            "success": True,
            "content": result_content,
            "encoding": file_encoding if not is_binary else "binary",
            "format": output_format,
        }
    except Exception as e:
        logger.error(f"Failed to read file {path}: {e}")
        return {"error": str(e)}


def _collect_pattern_matches(
    root_dir: Path,
    validated_path: Path,
    patterns: list[str],
    recursive: bool,
) -> list[str]:
    """Return pattern-based matches within the validated path."""
    matches: list[str] = []
    iterator = validated_path.rglob if recursive else validated_path.glob
    for pattern in patterns:
        for item in iterator(pattern):
            matches.append(str(item.relative_to(root_dir)))
    return matches


async def _collect_keyword_matches(
    root_dir: Path,
    validated_path: Path,
    keywords_path_name: list[str] | None,
    keywords_file_content: list[str] | None,
    regex_keywords: bool,
    use_fast_search: bool,
    max_workers: int,
) -> list[str]:
    """Return keyword-based matches using fast search or fallback scan."""
    if use_fast_search:
        searcher = FastFileSearcher(max_workers=max_workers)
        try:
            results = await searcher.search_files(
                validated_path,
                keywords_path_name,
                keywords_file_content,
                regex_keywords,
                max_results=10_000,
            )
        finally:
            searcher.close()
    else:
        results = FileUtils.find_files(
            validated_path,
            keywords_path_name,
            keywords_file_content,
            regex_keywords,
        )

    return [_normalise_relative_path(root_dir, Path(result)) for result in results]


def _normalise_relative_path(root_dir: Path, candidate: Path) -> str:
    """Convert a candidate path to project-relative form when possible."""
    try:
        return str(candidate.relative_to(root_dir))
    except ValueError:
        return str(candidate)


def _resolve_line_number_hint(add_line_numbers: bool | None, safe_path: Path) -> bool:
    """Infer whether to display line numbers when parameter is not provided."""
    return FileUtils.is_source_code_file(safe_path) if add_line_numbers is None else add_line_numbers


def _resolve_offsets(
    offset_type: str,
    start_offset_inclusive: int,
    end_offset_inclusive: int,
    start_line: int | None,
    end_line: int | None,
    is_binary: bool,
) -> tuple[OffsetType, int, int]:
    """Resolve final offset configuration for file reads."""
    if start_line is not None or end_line is not None:
        offset_type = "line"
        start_offset_inclusive = (start_line - 1) if start_line else 0
        end_offset_inclusive = (end_line - 1) if end_line else -1

    offset_enum = OffsetType[offset_type.upper()]
    if is_binary:
        offset_enum = OffsetType.BYTE
    return offset_enum, start_offset_inclusive, end_offset_inclusive


def _read_file_segment(
    safe_path: Path,
    offset_enum: OffsetType,
    start_offset_inclusive: int,
    end_offset_inclusive: int,
    file_encoding: str,
    add_line_numbers: bool,
) -> bytes:
    """Read the requested segment from disk."""
    if offset_enum == OffsetType.BYTE:
        return _read_binary_segment(safe_path, start_offset_inclusive, end_offset_inclusive)

    lines = _read_all_lines(safe_path, file_encoding)
    if offset_enum == OffsetType.LINE:
        return _read_line_segment(lines, start_offset_inclusive, end_offset_inclusive, add_line_numbers, file_encoding)

    return _read_character_segment(lines, start_offset_inclusive, end_offset_inclusive, file_encoding)


def _read_binary_segment(path: Path, start: int, end: int) -> bytes:
    """Read byte-oriented segment from path."""
    with path.open("rb") as handle:
        if start > 0:
            handle.seek(start)
        if end == -1:
            return handle.read()
        length = end - start + 1
        return handle.read(length)


def _read_all_lines(path: Path, encoding: str) -> list[str]:
    """Return all lines from a text file."""
    with path.open(encoding=encoding) as handle:
        return handle.readlines()


def _read_line_segment(
    lines: list[str],
    start: int,
    end: int,
    add_line_numbers: bool,
    encoding: str,
) -> bytes:
    """Return selected lines encoded as bytes."""
    end_index = len(lines) if end == -1 else end + 1
    selected_lines = lines[start:end_index]
    if add_line_numbers:
        formatted = [f"{start + index + 1}|{line.rstrip(LINE_BREAK)}" for index, line in enumerate(selected_lines)]
        return LINE_BREAK.join(formatted).encode(encoding)
    return "".join(selected_lines).encode(encoding)


def _read_character_segment(
    lines: list[str],
    start: int,
    end: int,
    encoding: str,
) -> bytes:
    """Return selected characters encoded as bytes."""
    full_text = "".join(lines)
    end_index = len(full_text) if end == -1 else end + 1
    return full_text[start:end_index].encode(encoding)


def _encode_read_content(
    content: bytes,
    output_enum: OutputFormat,
    is_binary: bool,
    file_encoding: str,
) -> str | bytes:
    """Encode the raw content according to output settings."""
    if output_enum == OutputFormat.RAW_UTF8:
        return FileUtils.encode_content(content, OutputFormat.BASE64) if is_binary else content.decode(file_encoding, errors="replace")
    return FileUtils.encode_content(content, output_enum)


def _decode_write_content(
    content: str,
    mode: str,
    input_enum: InputFormat,
    file_encoding: str,
) -> str | bytes:
    """Decode user-provided content into the format to be written."""
    if mode == "binary":
        return content.encode("utf-8") if input_enum == InputFormat.RAW_UTF8 else FileUtils.decode_content(content, input_enum)

    if input_enum == InputFormat.RAW_UTF8:
        return content

    decoded_bytes = FileUtils.decode_content(content, input_enum)
    return decoded_bytes.decode(file_encoding)


async def _run_precommit_validation(
    safe_path: Path,
    write_content: str | bytes,
    file_encoding: str,
    validate_with_precommit: bool,
) -> tuple[str | bytes, dict[str, Any] | None]:
    """Run pre-commit validation when enabled."""
    if not validate_with_precommit:
        return write_content, None

    validator = PreCommitValidator()
    validation_result = await validator.validate_content(safe_path, write_content, encoding=file_encoding)

    if not validation_result["valid"]:
        error_details = "\n".join(validation_result["errors"]) if validation_result["errors"] else "Pre-commit hooks failed"
        return write_content, {
            "error": f"Pre-commit validation failed:\n{error_details}",
            "validation_errors": validation_result["errors"],
        }

    modified_content = validation_result["modified_content"]
    if modified_content != write_content and validation_result["errors"]:
        logger.info(f"Pre-commit hooks modified {safe_path}")

    return modified_content, None


def _write_validated_content(
    safe_path: Path,
    write_content: str | bytes,
    mode: str,
    file_encoding: str,
) -> None:
    """Persist content to disk using the correct mode."""
    if mode == "binary":
        data = write_content if isinstance(write_content, bytes) else write_content.encode(file_encoding)
        safe_path.write_bytes(data)
        return

    text = write_content if isinstance(write_content, str) else write_content.decode(file_encoding)
    safe_path.write_text(text, encoding=file_encoding)


def _calculate_bytes_written(write_content: str | bytes, file_encoding: str) -> int:
    """Determine the number of bytes written to disk."""
    if isinstance(write_content, bytes):
        return len(write_content)
    return len(write_content.encode(file_encoding))


async def write_to_file_tool(
    root_dir: Path,
    path: str,
    content: str,
    mode: str = "text",
    input_format: str = "raw_utf8",
    file_encoding: str = "utf-8",
    validate_with_precommit: bool = True,
) -> dict[str, Any]:
    """Write content to file with pre-commit validation."""
    logger.debug(f"Writing to file: path={path}")

    try:
        safe_path = validate_path(root_dir, path, allow_write=False)

        safe_path.parent.mkdir(parents=True, exist_ok=True)
        input_enum = InputFormat[input_format.replace("-", "_").upper()]
        write_content = _decode_write_content(content, mode, input_enum, file_encoding)

        write_content, error_response = await _run_precommit_validation(
            safe_path,
            write_content,
            file_encoding,
            validate_with_precommit,
        )
        if error_response:
            return error_response

        _write_validated_content(safe_path, write_content, mode, file_encoding)

        return {
            "success": True,
            "path": str(safe_path.relative_to(root_dir)),
            "bytes_written": _calculate_bytes_written(write_content, file_encoding),
        }
    except Exception as e:
        logger.error(f"Failed to write file {path}: {e}")
        return {"error": str(e)}


async def delete_paths_tool(root_dir: Path, paths: list[str]) -> dict[str, Any]:
    """Delete files or directories."""
    logger.debug(f"Deleting paths: {paths}")

    try:
        deleted = []
        errors = []

        for path_str in paths:
            try:
                safe_path = validate_path(root_dir, path_str, allow_write=False)

                if not safe_path.exists():
                    errors.append(f"{path_str}: File or directory does not exist")
                    continue

                if safe_path.is_dir():
                    shutil.rmtree(safe_path)
                else:
                    safe_path.unlink()

                deleted.append(str(safe_path.relative_to(root_dir)))
            except Exception as e:
                errors.append(f"{path_str}: {e!s}")

        result: dict[str, Any] = {"deleted": deleted}
        if errors:
            result["errors"] = errors
        else:
            result["success"] = True

        return result
    except Exception as e:
        logger.error(f"Failed to delete paths: {e}")
        return {"error": str(e)}


async def modify_file_tool(
    root_dir: Path,
    path: str,
    start_offset_inclusive: int,
    end_offset_inclusive: int,
    new_content: str,
    offset_type: str = "line",
) -> dict[str, Any]:
    """Modify file by replacing content at specific offsets."""
    logger.debug(f"Modifying file: path={path}, start={start_offset_inclusive}, " f"end={end_offset_inclusive}, offset_type={offset_type}")

    try:
        safe_path = validate_path(root_dir, path, allow_write=False)

        if not safe_path.exists():
            return {"error": f"File does not exist: {path}"}

        content = safe_path.read_text(encoding="utf-8")

        if offset_type == "line":
            lines = content.splitlines(keepends=True)
            # Convert to 0-based indexing
            start_idx = start_offset_inclusive - 1
            end_idx = end_offset_inclusive - 1

            if start_idx < 0 or end_idx >= len(lines):
                return {"error": "Line offsets out of range"}

            # Replace the lines
            new_lines = [
                *lines[:start_idx],
                new_content + ("\n" if not new_content.endswith("\n") else ""),
                *lines[end_idx + 1 :],
            ]
            new_full_content = "".join(new_lines)
        elif offset_type == "byte":
            if start_offset_inclusive < 0 or end_offset_inclusive >= len(content):
                return {"error": "Byte offsets out of range"}

            new_full_content = content[:start_offset_inclusive] + new_content + content[end_offset_inclusive + 1 :]
        else:
            return {"error": f"Invalid offset_type: {offset_type}"}

        safe_path.write_text(new_full_content, encoding="utf-8")

        return {
            "success": True,
            "path": str(safe_path.relative_to(root_dir)),
            "message": f"Modified {path}",
        }
    except Exception as e:
        logger.error(f"Failed to modify file {path}: {e}")
        return {"error": str(e)}


async def replace_in_file_tool(
    root_dir: Path,
    path: str,
    old_content: str,
    new_content: str,
    is_regex: bool = False,
) -> dict[str, Any]:
    """Replace text in file."""
    logger.debug(f"Replacing in file: path={path}, old_content={old_content}, is_regex={is_regex}")

    try:
        safe_path = validate_path(root_dir, path, allow_write=False)

        if not safe_path.exists():
            return {"error": f"File does not exist: {path}"}

        content = safe_path.read_text(encoding="utf-8")

        if is_regex:
            new_file_content = re.sub(old_content, new_content, content)
            count = len(re.findall(old_content, content))
        else:
            count = content.count(old_content)
            new_file_content = content.replace(old_content, new_content)

        safe_path.write_text(new_file_content, encoding="utf-8")

        return {
            "success": True,
            "path": str(safe_path.relative_to(root_dir)),
            "replacements": count,
        }
    except Exception as e:
        logger.error(f"Failed to replace in file {path}: {e}")
        return {"error": str(e)}
