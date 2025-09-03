"""File utilities for filesystem MCP server."""

import base64
import difflib
import json
import platform
import re
from enum import Enum
from pathlib import Path
from quopri import decodestring, encodestring
from typing import Any

from files.backend.config import files_config
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

    _source_extensions: set[str] | None = None  # Cache for source code extensions

    @classmethod
    def get_max_file_size(cls) -> int:
        """Get maximum file size from configuration."""
        return files_config.get_max_file_size_bytes()

    @classmethod
    def _load_source_extensions(cls) -> set[str]:
        """Load source code file extensions from config file.

        Returns:
            Set of source code file extensions
        """
        # Return cached extensions if available
        if cls._source_extensions is not None:
            return cls._source_extensions

        # Try to load from config file
        extensions: set[str] = set()
        try:
            config_path = (
                Path(__file__).parent.parent.parent.parent.parent
                / "res"
                / "file_extensions.json"
            )
            with config_path.open() as f:
                data = json.load(f)

            # Add programming language extensions
            for lang_exts in data.get("text_files", {}).get("programming", {}).values():
                extensions.update(lang_exts)
            # Add web-related extensions (HTML, CSS, JS, etc.)
            for lang_exts in data.get("text_files", {}).get("web", {}).values():
                extensions.update(lang_exts)

        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load source extensions config: {e}")
            # Fall back to common extensions
            extensions = {
                ".py",
                ".js",
                ".ts",
                ".jsx",
                ".tsx",
                ".java",
                ".cpp",
                ".c",
                ".h",
                ".cs",
                ".go",
                ".rs",
                ".rb",
                ".php",
                ".swift",
                ".kt",
                ".scala",
                ".html",
                ".css",
                ".scss",
                ".sass",
                ".vue",
                ".yaml",
                ".yml",
                ".json",
                ".xml",
                ".md",
                ".sh",
                ".bash",
                ".zsh",
                ".fish",
            }

        # Cache and return extensions
        cls._source_extensions = extensions
        return cls._source_extensions

    @classmethod
    def is_source_code_file(cls, file_path: Path) -> bool:
        """Check if a file is a source code file based on its extension.

        Args:
            file_path: Path to the file

        Returns:
            True if file is a source code file
        """
        extensions = cls._load_source_extensions()
        return file_path.suffix.lower() in extensions

    @classmethod
    def get_source_extensions(cls) -> set[str]:
        """Get the set of source code file extensions.

        Returns:
            Set of source code file extensions
        """
        return cls._load_source_extensions()

    @classmethod
    def clear_extensions_cache(cls) -> None:
        """Clear the cached source extensions to force reload."""
        cls._source_extensions = None

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
        except OSError as e:
            logger.warning(f"Error checking if file is text: {e}")
            return True  # Default to text if unsure

    @staticmethod
    def validate_file_path(file_path: str, root_dir: Path) -> Path:
        """Validate and resolve a file path, handling both absolute and relative paths.

        This method intelligently handles:
        - Relative paths: Resolved relative to root_dir
        - Absolute paths within root_dir: Accepted as-is
        - Absolute paths that match root_dir structure: Converted to relative

        Args:
            file_path: File path to validate (absolute or relative)
            root_dir: Root directory

        Returns:
            Resolved path within root directory

        Raises:
            ValueError: If path is invalid or escapes root directory
        """
        try:
            # Resolve the root directory to an absolute path
            root_path = root_dir.resolve()

            # Normalize Windows-style separators to forward slashes on Unix systems

            if platform.system() != "Windows":
                # On Unix systems, replace backslashes with forward slashes
                file_path = file_path.replace("\\", "/")

            # Try to interpret the path
            path_obj = Path(file_path)

            # Check if it looks like an absolute path (even on Windows where / paths aren't absolute)
            # A path starting with / or having a drive letter is considered "absolute-like"
            is_absolute_like = path_obj.is_absolute() or file_path.startswith(
                ("/", "\\")
            )

            # If it's an absolute or absolute-like path
            if is_absolute_like:
                # First, try to resolve it (but it might not exist)
                try:
                    resolved_path = path_obj.resolve()

                    # Check if this absolute path is already within our root
                    if resolved_path.is_relative_to(root_path):
                        return resolved_path
                except (OSError, RuntimeError):
                    # Path doesn't exist yet, that's OK, we'll handle it below
                    pass

                # Try to find if this path has the same structure as root
                # For example, if root is C:/projects/myapp and user provides
                # C:/other/path/myapp/src/file.py, we try to match from 'myapp' onwards
                root_parts = root_path.parts
                path_parts = path_obj.parts  # Use original path_obj, not resolved

                # Find if the root's last directory name appears in the given path
                if root_parts:
                    root_name = root_parts[-1]
                    if root_name in path_parts:
                        # Find the index and take everything after it
                        idx = path_parts.index(root_name)
                        relative_parts = path_parts[idx + 1 :]
                        if relative_parts:
                            # Convert to relative path and continue processing
                            path_obj = Path(*relative_parts)
                            # Now treat it as a relative path - it's no longer absolute
                        else:
                            # Points to root itself
                            return root_path
                    else:
                        # Can't map this absolute path to our root
                        raise ValueError(
                            f"Absolute path '{file_path}' cannot be mapped to root directory '{root_path}'"
                        )

            # Handle as relative path
            # Don't use resolve() yet as the path might not exist
            combined_path = root_path / path_obj

            # Normalize the path (remove .., ., etc) without requiring it to exist
            try:
                # Try resolve first (if path exists)
                resolved_path = combined_path.resolve()
            except (OSError, RuntimeError):
                # Path doesn't exist, use alternative normalization
                # This handles .. and . in the path
                parts = list(combined_path.parts)
                normalized_parts: list[str] = []
                for part in parts:
                    if part == "..":
                        if normalized_parts and normalized_parts[-1] != "..":
                            normalized_parts.pop()
                    elif part != ".":
                        normalized_parts.append(part)
                resolved_path = (
                    Path(*normalized_parts) if normalized_parts else root_path
                )

            # Security check: ensure the resolved path is within root
            # For non-existent paths, check by string comparison
            try:
                # Convert both to strings with consistent separators for comparison
                root_str = str(root_path.resolve()).replace("\\", "/")
                resolved_str = str(resolved_path).replace("\\", "/")

                # Ensure the resolved path starts with the root path
                if not resolved_str.startswith(root_str):
                    # Check if path exists first
                    if resolved_path.exists():
                        # For existing paths, use is_relative_to
                        if not resolved_path.is_relative_to(root_path):
                            raise ValueError(
                                f"Path '{file_path}' is outside the allowed root directory"
                            )
                    else:
                        # For non-existing paths, check parent directories
                        check_path = resolved_path
                        found_existing = False
                        while check_path != check_path.parent:
                            if check_path.exists():
                                found_existing = True
                                if not check_path.is_relative_to(root_path):
                                    raise ValueError(
                                        f"Path '{file_path}' is outside the allowed root directory"
                                    )
                                break
                            check_path = check_path.parent

                        # If no existing parent found, the path is invalid
                        if not found_existing and not resolved_str.startswith(root_str):
                            raise ValueError(
                                f"Path '{file_path}' is outside the allowed root directory"
                            )
            except (OSError, ValueError) as e:
                if "outside the allowed root directory" in str(e):
                    raise
                # Some other error, path is probably invalid
                raise ValueError(f"Invalid path '{file_path}': {e}") from e

            return resolved_path
        except (OSError, TypeError) as e:
            raise ValueError(f"Invalid file path '{file_path}': {e}") from e

    @staticmethod
    def validate_path(path: str, root_dir: Path, must_exist: bool = False) -> Path:
        """Validate and resolve any path (file or directory).

        This is a more general version of validate_file_path that works for
        both files and directories.

        Args:
            path: Path to validate (absolute or relative)
            root_dir: Root directory
            must_exist: If True, the path must already exist

        Returns:
            Resolved path within root directory

        Raises:
            ValueError: If path is invalid, escapes root, or doesn't exist when required
        """
        # Use the same logic as validate_file_path
        resolved = FileUtils.validate_file_path(path, root_dir)

        if must_exist and not resolved.exists():
            raise ValueError(f"Path does not exist: {path}")

        return resolved

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
            max_size = FileUtils.get_max_file_size()
            if size > max_size:
                raise ValueError(
                    f"File too large: {size} bytes (max: {max_size} bytes)"
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
                    except (OSError, UnicodeDecodeError) as e:
                        logger.warning(f"Error reading file {file_path}: {e}")

            # Add to results if matched
            if (path_keywords and path_match) or (content_keywords and content_match):
                results.append(str(file_path))

        return results
