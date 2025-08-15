"""File utilities for filesystem MCP server."""

import base64
import difflib
import re
from enum import Enum
from pathlib import Path
from quopri import decodestring, encodestring
from typing import Any

from loguru import logger


class OffsetType(Enum):
    """Offset type for file operations."""

    BYTE = "BYTE"
    CHAR = "CHAR"
    LINE = "LINE"


class InputFormat(Enum):
    """Input format for content."""

    QUOTED_PRINTABLE = "QUOTED-PRINTABLE"
    BASE64 = "BASE64"
    RAW_UTF8 = "RAW_UTF8"


class OutputFormat(Enum):
    """Output format for content."""

    QUOTED_PRINTABLE = "QUOTED-PRINTABLE"
    BASE64 = "BASE64"
    RAW_UTF8 = "RAW_UTF8"


class FileUtils:
    """Provides file manipulation utilities."""

    max_file_size = 100 * 1024 * 1024  # 100MB limit

    @staticmethod
    def is_text_file(file_path: Path) -> bool:
        """Check if a file is a text file based on its content.

        Args:
            file_path: Path to the file

        Returns:
            True if file appears to be text, False if binary
        """
        if not file_path.exists():
            return True  # Assume new files are text

        try:
            # Read first 8192 bytes to check if it's text
            with Path(file_path).open("rb") as f:
                chunk = f.read(8192)
                if not chunk:
                    return True

                # Check for null bytes (common in binary files)
                if b"\x00" in chunk:
                    return False

                # Try to decode as UTF-8
                try:
                    chunk.decode("utf-8")
                    return True
                except UnicodeDecodeError:
                    return False
        except Exception as e:
            logger.warning(f"Error checking if file is text: {e}")
            return True  # Default to text if unsure

    @staticmethod
    def validate_file_path(file_path: str, root_dir: Path) -> Path:
        """Validate that a file path is within the allowed root directory.

        Args:
            file_path: File path to validate
            root_dir: Root directory

        Returns:
            Resolved path within root directory

        Raises:
            ValueError: If path is outside root directory
        """
        try:
            # Resolve the root directory to an absolute path
            root_path = root_dir.resolve()

            # Resolve the provided file path
            resolved_path = (
                Path(file_path).resolve()
                if Path(file_path).is_absolute()
                else (root_path / file_path).resolve()
            )

            # Check if the resolved path is within the root directory
            if not resolved_path.is_relative_to(root_path):
                raise ValueError(
                    f"Path '{file_path}' is outside the allowed root directory"
                )

            return resolved_path
        except Exception as e:
            raise ValueError(f"Invalid file path '{file_path}': {e}") from e

    @staticmethod
    def check_file_size(file_path: Path) -> None:
        """Check if file size is within limits.

        Args:
            file_path: Path to check

        Raises:
            ValueError: If file is too large
        """
        if file_path.exists():
            size = file_path.stat().st_size
            if size > FileUtils.max_file_size:
                raise ValueError(
                    f"File too large: {size} bytes (max: {FileUtils.max_file_size} bytes)"
                )

    @staticmethod
    def encode_content(data: bytes, output_format: OutputFormat) -> str | bytes:
        """Encode bytes to the specified output format.

        Args:
            data: Data to encode
            output_format: Output format

        Returns:
            Encoded content
        """
        if output_format == OutputFormat.QUOTED_PRINTABLE:
            return encodestring(data).decode("ascii")
        if output_format == OutputFormat.BASE64:
            return base64.b64encode(data).decode("ascii")
        if output_format == OutputFormat.RAW_UTF8:
            return data.decode("utf-8", errors="replace")
        raise ValueError(f"Unsupported output format: {output_format}")

    @staticmethod
    def decode_content(data: str, input_format: InputFormat) -> bytes:
        """Decode a string from the specified input format to bytes.

        Args:
            data: Data to decode
            input_format: Input format

        Returns:
            Decoded bytes
        """
        if input_format == InputFormat.QUOTED_PRINTABLE:
            return decodestring(data.encode("ascii"))
        if input_format == InputFormat.BASE64:
            return base64.b64decode(data.encode("ascii"))
        if input_format == InputFormat.RAW_UTF8:
            return data.encode("utf-8")
        raise ValueError(f"Unsupported input format: {input_format}")

    @staticmethod
    def generate_diff(original: str, new: str, file_path: str) -> str:
        """Generate a unified diff between original and new content.

        Args:
            original: Original content
            new: New content
            file_path: File path for diff header

        Returns:
            Unified diff string
        """
        original_lines = original.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"{file_path} (original)",
            tofile=f"{file_path} (new)",
            lineterm="",
        )

        return "".join(diff)

    @staticmethod
    def find_files(
        directory_path: Path,
        path_keywords: list[str] | None = None,
        content_keywords: list[str] | None = None,
        regex_mode: bool = False,
        max_results: int = 1000,
    ) -> list[str]:
        """Find files matching keywords in path or content.

        Args:
            directory_path: Directory to search in
            path_keywords: Keywords to match in file paths
            content_keywords: Keywords to match in file content
            regex_mode: Whether to treat keywords as regular expressions
            max_results: Maximum number of results to return

        Returns:
            List of matching file paths
        """
        results: list[str] = []
        path_keywords = path_keywords or []
        content_keywords = content_keywords or []

        # Compile regex patterns if needed
        path_patterns: Any
        content_patterns: Any
        if regex_mode:
            path_patterns = [re.compile(kw) for kw in path_keywords]
            content_patterns = [re.compile(kw) for kw in content_keywords]
        else:
            path_patterns = path_keywords
            content_patterns = content_keywords

        # Search files
        for file_path in directory_path.rglob("*"):
            if len(results) >= max_results:
                break

            if not file_path.is_file():
                continue

            # Check path keywords
            path_match = False
            if path_keywords:
                path_str = str(file_path)
                if regex_mode:
                    path_match = any(p.search(path_str) for p in path_patterns)
                else:
                    path_match = any(kw in path_str for kw in path_patterns)

            # Check content keywords if needed
            content_match = False
            if content_keywords and (not path_keywords or path_match):
                if FileUtils.is_text_file(file_path):
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        if regex_mode:
                            content_match = any(
                                p.search(content) for p in content_patterns
                            )
                        else:
                            content_match = any(
                                kw in content for kw in content_patterns
                            )
                    except Exception as e:
                        logger.warning(f"Error reading file {file_path}: {e}")

            # Add to results if matched
            if (path_keywords and path_match) or (content_keywords and content_match):
                results.append(str(file_path))

        return results
