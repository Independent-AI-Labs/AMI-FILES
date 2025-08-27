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


async def list_dir_tool(
    root_dir: Path,
    path: str = ".",
    recursive: bool = False,
    pattern: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List directory contents."""
    logger.debug(
        f"Listing directory: path={path}, recursive={recursive}, pattern={pattern}, limit={limit}"
    )

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
            safe_path = validate_path(root_dir, path_str)
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
    logger.debug(
        f"Finding paths: patterns={patterns}, path={path}, recursive={recursive}"
    )

    try:
        validated_path = validate_path(root_dir, path)

        if not validated_path.is_dir():
            return {"error": f"Path is not a directory: {path}"}

        found = []

        # If patterns provided, use glob matching
        if patterns:
            for pattern in patterns:
                if recursive:
                    for item in validated_path.rglob(pattern):
                        found.append(str(item.relative_to(root_dir)))
                else:
                    for item in validated_path.glob(pattern):
                        found.append(str(item.relative_to(root_dir)))

        # If keywords provided, use keyword search
        if keywords_path_name or keywords_file_content:
            if use_fast_search:
                searcher = FastFileSearcher(max_workers=max_workers)
                try:
                    results = await searcher.search_files(
                        validated_path,
                        keywords_path_name,
                        keywords_file_content,
                        regex_keywords,
                        max_results=10000,
                    )
                    # Convert to relative paths
                    for result in results:
                        try:
                            rel_path = Path(result).relative_to(root_dir)
                            found.append(str(rel_path))
                        except ValueError:
                            found.append(result)
                finally:
                    searcher.close()
            else:
                # Fallback to FileUtils search
                results = FileUtils.find_files(
                    validated_path,
                    keywords_path_name,
                    keywords_file_content,
                    regex_keywords,
                )
                for result in results:
                    try:
                        rel_path = Path(result).relative_to(root_dir)
                        found.append(str(rel_path))
                    except ValueError:
                        found.append(result)

        return {"success": True, "paths": found, "total_found": len(found)}
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

        # Determine if binary
        is_binary = not FileUtils.is_text_file(safe_path)

        # Auto-detect line numbers based on file type if not specified
        if add_line_numbers is None:
            add_line_numbers = FileUtils.is_source_code_file(safe_path)

        # Handle legacy start_line/end_line parameters
        if start_line is not None or end_line is not None:
            offset_type = "line"
            start_offset_inclusive = (start_line - 1) if start_line else 0
            end_offset_inclusive = (end_line - 1) if end_line else -1

        # Parse enum values
        offset_enum = OffsetType[offset_type.upper()]
        output_enum = OutputFormat[output_format.replace("-", "_").upper()]

        # Force byte mode for binary files
        if is_binary:
            offset_enum = OffsetType.BYTE

        # Read content based on offset type
        if offset_enum == OffsetType.BYTE:
            with safe_path.open("rb") as f:
                if start_offset_inclusive > 0:
                    f.seek(start_offset_inclusive)
                if end_offset_inclusive == -1:
                    content = f.read()
                else:
                    length = end_offset_inclusive - start_offset_inclusive + 1
                    content = f.read(length)
        else:
            # Text mode reading
            with safe_path.open(encoding=file_encoding) as f:
                lines = f.readlines()

            if offset_enum == OffsetType.LINE:
                end = (
                    len(lines)
                    if end_offset_inclusive == -1
                    else end_offset_inclusive + 1
                )
                selected_lines = lines[start_offset_inclusive:end]

                # Add line numbers if requested
                if add_line_numbers:
                    formatted_lines = []
                    for i, line in enumerate(selected_lines):
                        line_num = start_offset_inclusive + i + 1
                        line_content = line.rstrip("\n")
                        formatted_lines.append(f"{line_num}|{line_content}")
                    content = "\n".join(formatted_lines).encode(file_encoding)
                else:
                    content = "".join(selected_lines).encode(file_encoding)
            else:  # CHAR
                full_text = "".join(lines)
                end = (
                    len(full_text)
                    if end_offset_inclusive == -1
                    else end_offset_inclusive + 1
                )
                selected_text = full_text[start_offset_inclusive:end]
                content = selected_text.encode(file_encoding)

        # Encode output
        if output_enum == OutputFormat.RAW_UTF8:
            if is_binary:
                result_content = FileUtils.encode_content(content, OutputFormat.BASE64)
            else:
                result_content = content.decode(file_encoding, errors="replace")
        else:
            result_content = FileUtils.encode_content(content, output_enum)

        return {
            "success": True,
            "content": result_content,
            "encoding": file_encoding if not is_binary else "binary",
            "format": output_format,
        }
    except Exception as e:
        logger.error(f"Failed to read file {path}: {e}")
        return {"error": str(e)}


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

        # Create parent directories if needed
        safe_path.parent.mkdir(parents=True, exist_ok=True)

        # Parse input format
        input_enum = InputFormat[input_format.replace("-", "_").upper()]

        # Decode content if needed
        write_content: str | bytes
        if mode == "binary":
            if input_enum == InputFormat.RAW_UTF8:
                write_content = content.encode("utf-8")
            else:
                write_content = FileUtils.decode_content(content, input_enum)
        else:
            if input_enum != InputFormat.RAW_UTF8:
                decoded = FileUtils.decode_content(content, input_enum)
                write_content = decoded.decode(file_encoding)
            else:
                write_content = content

        # Validate with pre-commit if enabled
        if validate_with_precommit:
            validator = PreCommitValidator()
            validation_result = await validator.validate_content(
                safe_path,
                write_content,
                encoding=file_encoding,
            )

            if not validation_result["valid"]:
                error_details = (
                    "\n".join(validation_result["errors"])
                    if validation_result["errors"]
                    else "Pre-commit hooks failed"
                )
                return {
                    "error": f"Pre-commit validation failed:\n{error_details}",
                    "validation_errors": validation_result["errors"],
                }

            # Use the potentially modified content from pre-commit
            write_content = validation_result["modified_content"]

            # Log if content was modified by hooks
            if write_content != content and validation_result["errors"]:
                logger.info(f"Pre-commit hooks modified {path}")

        # Write the validated content
        if mode == "binary":
            if isinstance(write_content, bytes):
                safe_path.write_bytes(write_content)
            else:
                safe_path.write_bytes(write_content.encode(file_encoding))
        else:
            if isinstance(write_content, str):
                safe_path.write_text(write_content, encoding=file_encoding)
            else:
                safe_path.write_text(
                    write_content.decode(file_encoding), encoding=file_encoding
                )

        return {
            "success": True,
            "path": str(safe_path.relative_to(root_dir)),
            "bytes_written": len(
                write_content
                if isinstance(write_content, bytes)
                else write_content.encode(file_encoding)
            ),
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
                safe_path = validate_path(root_dir, path_str)

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

        result = {"deleted": deleted}
        if errors:
            result["errors"] = errors
        else:
            result["success"] = True  # type: ignore[assignment]

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
    logger.debug(
        f"Modifying file: path={path}, start={start_offset_inclusive}, "
        f"end={end_offset_inclusive}, offset_type={offset_type}"
    )

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
            new_lines = (
                lines[:start_idx]
                + [new_content + ("\n" if not new_content.endswith("\n") else "")]
                + lines[end_idx + 1 :]
            )
            new_full_content = "".join(new_lines)
        elif offset_type == "byte":
            if start_offset_inclusive < 0 or end_offset_inclusive >= len(content):
                return {"error": "Byte offsets out of range"}

            new_full_content = (
                content[:start_offset_inclusive]
                + new_content
                + content[end_offset_inclusive + 1 :]
            )
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
    root_dir: Path, path: str, pattern: str, replacement: str, regex: bool = False
) -> dict[str, Any]:
    """Replace text in file."""
    logger.debug(f"Replacing in file: path={path}, pattern={pattern}, regex={regex}")

    try:
        safe_path = validate_path(root_dir, path, allow_write=False)

        if not safe_path.exists():
            return {"error": f"File does not exist: {path}"}

        content = safe_path.read_text(encoding="utf-8")

        if regex:
            new_content = re.sub(pattern, replacement, content)
            count = len(re.findall(pattern, content))
        else:
            count = content.count(pattern)
            new_content = content.replace(pattern, replacement)

        safe_path.write_text(new_content, encoding="utf-8")

        return {
            "success": True,
            "path": str(safe_path.relative_to(root_dir)),
            "replacements": count,
        }
    except Exception as e:
        logger.error(f"Failed to replace in file {path}: {e}")
        return {"error": str(e)}
