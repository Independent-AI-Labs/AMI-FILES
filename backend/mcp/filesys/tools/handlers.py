"""Tool handler implementations for filesystem operations."""

import re
import shutil
from pathlib import Path
from typing import Any

from loguru import logger

from backend.mcp.filesys.fast_search import FastFileSearcher
from backend.mcp.filesys.file_utils import (
    FileUtils,
    InputFormat,
    OffsetType,
    OutputFormat,
)
from backend.mcp.filesys.precommit_validator import PreCommitValidator


async def list_dir(
    root_dir: Path, path: str, limit: int = 100, recursive: bool = False
) -> dict[str, Any]:
    """List directory contents.

    Args:
        root_dir: Root directory for operations
        path: Directory path to list
        limit: Maximum number of items to return
        recursive: Whether to list recursively

    Returns:
        Result with directory listing
    """
    try:
        validated_path = FileUtils.validate_file_path(path, root_dir)

        if not validated_path.is_dir():
            return {"error": f"Path is not a directory: {path}"}

        items = []
        count = 0

        if recursive:
            # Recursive listing
            for item_path in validated_path.rglob("*"):
                if count >= limit:
                    break
                relative_path = item_path.relative_to(validated_path)
                item_type = "dir" if item_path.is_dir() else "file"
                items.append({"path": str(relative_path), "type": item_type})
                count += 1
        else:
            # Non-recursive listing
            for item_path in validated_path.iterdir():
                if count >= limit:
                    break
                item_type = "dir" if item_path.is_dir() else "file"
                items.append({"path": item_path.name, "type": item_type})
                count += 1

        return {
            "result": {
                "directory": str(path),
                "items": items,
                "total_found": count,
                "limit_reached": count >= limit,
            }
        }

    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"Failed to list directory {path}: {e}")
        return {"error": str(e)}


async def create_dirs(root_dir: Path, path: str) -> dict[str, Any]:
    """Create directory and parent directories.

    Args:
        root_dir: Root directory for operations
        path: Directory path to create

    Returns:
        Result with creation status
    """
    try:
        validated_path = FileUtils.validate_file_path(path, root_dir)

        if validated_path.exists():
            if validated_path.is_dir():
                return {"result": {"message": f"Directory already exists: {path}"}}
            return {"error": f"Path exists but is not a directory: {path}"}

        validated_path.mkdir(parents=True, exist_ok=True)
        return {"result": {"message": f"Directory created: {path}"}}

    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return {"error": str(e)}


async def find_paths(
    root_dir: Path,
    path: str,
    keywords_path_name: list[str] | None = None,
    keywords_file_content: list[str] | None = None,
    regex_keywords: bool = False,
    use_fast_search: bool = True,
    max_workers: int = 8,
) -> dict[str, Any]:
    """Find files matching keywords using fast multithreaded search.

    Args:
        root_dir: Root directory for operations
        path: Directory to search in
        keywords_path_name: Keywords for path/name matching
        keywords_file_content: Keywords for content matching
        regex_keywords: Whether keywords are regex patterns
        use_fast_search: Use fast multithreaded search with pyahocorasick
        max_workers: Number of worker threads for parallel search

    Returns:
        Result with matching files
    """
    try:
        validated_path = FileUtils.validate_file_path(path, root_dir)

        if not validated_path.is_dir():
            return {"error": f"Path is not a directory: {path}"}

        # Use fast search if enabled and we have keywords
        if use_fast_search and (keywords_path_name or keywords_file_content):
            searcher = FastFileSearcher(max_workers=max_workers)
            try:
                results = await searcher.search_files(
                    validated_path,
                    keywords_path_name,
                    keywords_file_content,
                    regex_keywords,
                    max_results=10000,
                )
            finally:
                searcher.close()
        else:
            # Fall back to original implementation
            results = FileUtils.find_files(
                validated_path,
                keywords_path_name,
                keywords_file_content,
                regex_keywords,
            )

        # Convert absolute paths to relative paths from root_dir
        relative_results = []
        for result_path in results:
            try:
                relative = Path(result_path).relative_to(root_dir)
                relative_results.append(str(relative))
            except ValueError:
                # If can't make relative, use absolute
                relative_results.append(result_path)

        return {
            "result": {
                "directory": str(path),
                "matches": relative_results,
                "total_found": len(relative_results),
            }
        }

    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"Failed to find paths in {path}: {e}")
        return {"error": str(e)}


async def read_from_file(
    root_dir: Path,
    path: str,
    start_offset_inclusive: int = 0,
    end_offset_inclusive: int = -1,
    offset_type: str = "line",
    output_format: str = "raw_utf8",
    file_encoding: str = "utf-8",
) -> dict[str, Any]:
    """Read content from a file.

    Args:
        root_dir: Root directory for operations
        path: File path to read
        start_offset_inclusive: Start offset
        end_offset_inclusive: End offset (-1 for end of file)
        offset_type: Type of offset (line, char, byte)
        output_format: Output format
        file_encoding: File encoding

    Returns:
        Result with file content
    """
    try:
        validated_path = FileUtils.validate_file_path(path, root_dir)

        if not validated_path.exists():
            return {"error": f"File does not exist: {path}"}

        if not validated_path.is_file():
            return {"error": f"Path is not a file: {path}"}

        # Check file size
        FileUtils.check_file_size(validated_path)

        # Determine if binary
        is_binary = not FileUtils.is_text_file(validated_path)

        # Parse enum values
        offset_enum = OffsetType[offset_type.upper()]
        output_enum = OutputFormat[output_format.replace("-", "_").upper()]

        # Force byte mode for binary files
        if is_binary:
            offset_enum = OffsetType.BYTE

        # Read content based on offset type
        if offset_enum == OffsetType.BYTE:
            with validated_path.open("rb") as f:
                if start_offset_inclusive > 0:
                    f.seek(start_offset_inclusive)
                if end_offset_inclusive == -1:
                    content = f.read()
                else:
                    length = end_offset_inclusive - start_offset_inclusive + 1
                    content = f.read(length)
        else:
            # Text mode reading
            with validated_path.open(encoding=file_encoding) as f:
                lines = f.readlines()

            if offset_enum == OffsetType.LINE:
                end = (
                    len(lines)
                    if end_offset_inclusive == -1
                    else end_offset_inclusive + 1
                )
                selected_lines = lines[start_offset_inclusive:end]
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
                # For binary files, return base64 encoded
                result_content = FileUtils.encode_content(content, OutputFormat.BASE64)
            else:
                result_content = content.decode(file_encoding, errors="replace")
        else:
            result_content = FileUtils.encode_content(content, output_enum)

        return {
            "result": {
                "path": str(path),
                "content": result_content,
                "encoding": file_encoding if not is_binary else "binary",
                "format": output_format,
            }
        }

    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"Failed to read file {path}: {e}")
        return {"error": str(e)}


async def write_to_file(
    root_dir: Path,
    path: str,
    content: str,
    mode: str = "text",
    input_format: str = "raw_utf8",
    file_encoding: str = "utf-8",
    validate_with_precommit: bool = True,
) -> dict[str, Any]:
    """Write content to a file with optional pre-commit validation.

    Args:
        root_dir: Root directory for operations
        path: File path to write
        content: Content to write
        mode: Write mode (text/binary)
        input_format: Input format
        file_encoding: File encoding
        validate_with_precommit: Run pre-commit hooks before writing

    Returns:
        Result with write status
    """
    try:
        validated_path = FileUtils.validate_file_path(path, root_dir)

        # Create parent directories if needed
        validated_path.parent.mkdir(parents=True, exist_ok=True)

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
                validated_path,
                write_content,
                encoding=file_encoding,
            )

            if not validation_result["valid"]:
                return {
                    "error": "Pre-commit validation failed",
                    "validation_errors": validation_result["errors"],
                }

            # Use the potentially modified content from pre-commit
            write_content = validation_result["modified_content"]

            # Check if content was modified by hooks
            if write_content != content and validation_result["errors"]:
                logger.info(f"Pre-commit hooks modified {path}")

        # Write the validated content
        if mode == "binary":
            if isinstance(write_content, bytes):
                validated_path.write_bytes(write_content)
            else:
                validated_path.write_bytes(write_content.encode(file_encoding))
        else:
            if isinstance(write_content, str):
                validated_path.write_text(write_content, encoding=file_encoding)
            else:
                validated_path.write_text(
                    write_content.decode(file_encoding), encoding=file_encoding
                )

        return {
            "result": {
                "message": f"Successfully wrote to {path}",
                "path": str(path),
                "bytes_written": len(
                    write_content
                    if isinstance(write_content, bytes)
                    else write_content.encode(file_encoding)
                ),
            }
        }

    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"Failed to write file {path}: {e}")
        return {"error": str(e)}


async def delete_paths(root_dir: Path, paths: list[str]) -> dict[str, Any]:
    """Delete multiple files or directories.

    Args:
        root_dir: Root directory for operations
        paths: List of paths to delete

    Returns:
        Result with deletion status
    """
    deleted = []
    errors = []

    for path in paths:
        try:
            validated_path = FileUtils.validate_file_path(path, root_dir)

            if not validated_path.exists():
                errors.append({"path": path, "error": "Path does not exist"})
                continue

            if validated_path.is_dir():
                shutil.rmtree(validated_path)
            else:
                validated_path.unlink()

            deleted.append(path)

        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Failed to delete {path}: {e}")
            errors.append({"path": path, "error": str(e)})

    return {
        "result": {
            "deleted": deleted,
            "errors": errors,
            "total_deleted": len(deleted),
            "total_errors": len(errors),
        }
    }


async def modify_file(
    root_dir: Path,
    path: str,
    start_offset_inclusive: int,
    end_offset_inclusive: int,
    new_content: str,
    offset_type: str = "line",
    input_format: str = "raw_utf8",
    file_encoding: str = "utf-8",
    mode: str = "text",
    validate_with_precommit: bool = True,
) -> dict[str, Any]:
    """Modify a file by replacing a range with new content.

    Args:
        root_dir: Root directory for operations
        path: File path to modify
        start_offset_inclusive: Start offset for replacement
        end_offset_inclusive: End offset for replacement
        new_content: New content to insert
        offset_type: Type of offset
        input_format: Input format
        file_encoding: File encoding
        mode: File mode
        validate_with_precommit: Run pre-commit hooks before writing

    Returns:
        Result with modification status
    """
    try:
        validated_path = FileUtils.validate_file_path(path, root_dir)

        if not validated_path.exists():
            return {"error": f"File does not exist: {path}"}

        if not validated_path.is_file():
            return {"error": f"Path is not a file: {path}"}

        # Parse enum values
        offset_enum = OffsetType[offset_type.upper()]
        input_enum = InputFormat[input_format.replace("-", "_").upper()]

        # Read existing content
        if mode == "binary":
            original_content = validated_path.read_bytes()
            if input_enum != InputFormat.RAW_UTF8:
                new_bytes = FileUtils.decode_content(new_content, input_enum)
            else:
                new_bytes = new_content.encode("utf-8")

            # Replace range
            modified = (
                original_content[:start_offset_inclusive]
                + new_bytes
                + original_content[end_offset_inclusive + 1 :]
            )
            # Validate with pre-commit if enabled
            if validate_with_precommit:
                validator = PreCommitValidator()
                validation_result = await validator.validate_content(
                    validated_path,
                    modified,
                    encoding=file_encoding,
                )

                if not validation_result["valid"]:
                    return {
                        "error": "Pre-commit validation failed",
                        "validation_errors": validation_result["errors"],
                    }

                # Use the potentially modified content
                modified = validation_result["modified_content"]

            validated_path.write_bytes(modified)
        else:
            original_text = validated_path.read_text(encoding=file_encoding)

            if input_enum != InputFormat.RAW_UTF8:
                decoded = FileUtils.decode_content(new_content, input_enum)
                new_text = decoded.decode(file_encoding)
            else:
                new_text = new_content

            if offset_enum == OffsetType.LINE:
                lines = original_text.splitlines(keepends=True)
                modified_lines = (
                    lines[:start_offset_inclusive]
                    + [new_text]
                    + lines[end_offset_inclusive + 1 :]
                )
                modified_str = "".join(modified_lines)
            elif offset_enum == OffsetType.CHAR:
                modified_str = (
                    original_text[:start_offset_inclusive]
                    + new_text
                    + original_text[end_offset_inclusive + 1 :]
                )
            else:  # BYTE
                original_bytes = original_text.encode(file_encoding)
                new_bytes = new_text.encode(file_encoding)
                modified_bytes = (
                    original_bytes[:start_offset_inclusive]
                    + new_bytes
                    + original_bytes[end_offset_inclusive + 1 :]
                )
                modified_str = modified_bytes.decode(file_encoding)

            # Validate with pre-commit if enabled
            if validate_with_precommit:
                validator = PreCommitValidator()
                validation_result = await validator.validate_content(
                    validated_path,
                    modified_str,
                    encoding=file_encoding,
                )

                if not validation_result["valid"]:
                    return {
                        "error": "Pre-commit validation failed",
                        "validation_errors": validation_result["errors"],
                    }

                # Use the potentially modified content
                modified_str = validation_result["modified_content"]

            validated_path.write_text(modified_str, encoding=file_encoding)

        return {
            "result": {"message": f"Successfully modified {path}", "path": str(path)}
        }

    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"Failed to modify file {path}: {e}")
        return {"error": str(e)}


async def replace_in_file(
    root_dir: Path,
    path: str,
    old_content: str,
    new_content: str,
    number_of_occurrences: int = -1,
    is_regex: bool = False,
    mode: str = "text",
    input_format: str = "raw_utf8",
    file_encoding: str = "utf-8",
) -> dict[str, Any]:
    """Replace occurrences in a file.

    Args:
        root_dir: Root directory for operations
        path: File path
        old_content: Content to find
        new_content: Content to replace with
        number_of_occurrences: Number to replace (-1 for all)
        is_regex: Whether old_content is regex
        mode: File mode
        input_format: Input format
        file_encoding: File encoding

    Returns:
        Result with replacement status
    """
    try:
        validated_path = FileUtils.validate_file_path(path, root_dir)

        if not validated_path.exists():
            return {"error": f"File does not exist: {path}"}

        if not validated_path.is_file():
            return {"error": f"Path is not a file: {path}"}

        # Parse input format
        input_enum = InputFormat[input_format.replace("-", "_").upper()]

        # Initialize variables based on mode to satisfy type checker
        old_content_str: str = ""
        new_content_str: str = ""
        old_content_bytes: bytes = b""
        new_content_bytes: bytes = b""

        # Decode content if needed
        if input_enum != InputFormat.RAW_UTF8:
            old_decoded = FileUtils.decode_content(old_content, input_enum)
            new_decoded = FileUtils.decode_content(new_content, input_enum)
            if mode == "text":
                old_content_str = old_decoded.decode(file_encoding)
                new_content_str = new_decoded.decode(file_encoding)
            else:
                old_content_bytes = old_decoded
                new_content_bytes = new_decoded
        else:
            if mode == "text":
                old_content_str = old_content
                new_content_str = new_content
            else:
                old_content_bytes = (
                    old_content.encode("utf-8")
                    if isinstance(old_content, str)
                    else old_content
                )
                new_content_bytes = (
                    new_content.encode("utf-8")
                    if isinstance(new_content, str)
                    else new_content
                )

        # Perform replacement
        if mode == "binary":
            original = validated_path.read_bytes()
            if is_regex:
                return {"error": "Regex replacement not supported for binary mode"}
            if number_of_occurrences == -1:
                modified = original.replace(old_content_bytes, new_content_bytes)
            else:
                modified = original.replace(
                    old_content_bytes, new_content_bytes, number_of_occurrences
                )
            validated_path.write_bytes(modified)
            replacements = original.count(old_content_bytes)
        else:
            original_text = validated_path.read_text(encoding=file_encoding)
            if is_regex:
                if number_of_occurrences == -1:
                    modified_text = re.sub(
                        old_content_str, new_content_str, original_text
                    )
                else:
                    modified_text = re.sub(
                        old_content_str,
                        new_content_str,
                        original_text,
                        count=number_of_occurrences,
                    )
                replacements = len(re.findall(old_content_str, original_text))
            else:
                if number_of_occurrences == -1:
                    modified_text = original_text.replace(
                        old_content_str, new_content_str
                    )
                else:
                    modified_text = original_text.replace(
                        old_content_str, new_content_str, number_of_occurrences
                    )
                replacements = original_text.count(old_content_str)
            validated_path.write_text(modified_text, encoding=file_encoding)

        return {
            "result": {
                "message": f"Replaced {replacements} occurrences in {path}",
                "path": str(path),
                "replacements": replacements,
            }
        }

    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"Failed to replace in file {path}: {e}")
        return {"error": str(e)}
