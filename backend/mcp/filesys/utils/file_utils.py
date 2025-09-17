"""File utilities for filesystem MCP server."""

import base64
import contextlib
import difflib
import json
import platform
import re
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from quopri import decodestring, encodestring

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
            config_path = Path(__file__).parent.parent.parent.parent.parent / "res" / "file_extensions.json"
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
    def _normalize_input_path(file_path: str) -> str:
        """Normalize raw file path strings for consistent downstream handling."""

        if platform.system() != "Windows":
            return file_path.replace("\\", "/")
        return file_path

    @staticmethod
    def _is_absolute_like(path_obj: Path, original: str) -> bool:
        """Detect paths that should be interpreted as absolute."""

        return path_obj.is_absolute() or original.startswith(("/", "\\"))

    @staticmethod
    def _resolve_if_exists(path_obj: Path) -> Path | None:
        """Resolve the provided path if it already exists on disk."""

        if not path_obj.exists():
            return None
        with contextlib.suppress(OSError):
            return path_obj.resolve()
        return None

    @staticmethod
    def _map_absolute_to_root(path_obj: Path, root_path: Path) -> Path | None:
        """Attempt to map an absolute path onto the configured root directory."""

        root_parts = root_path.parts
        if not root_parts:
            return None

        root_name = root_parts[-1]
        path_parts = path_obj.parts
        if root_name not in path_parts:
            return None

        idx = path_parts.index(root_name)
        relative_parts = path_parts[idx + 1 :]
        return Path(*relative_parts) if relative_parts else Path()

    @staticmethod
    def _combine_with_root(candidate: Path, root_path: Path) -> Path:
        """Combine the candidate path with the root and normalise it."""

        combined = root_path / candidate
        with contextlib.suppress(OSError, RuntimeError):
            return combined.resolve(strict=False)
        return combined

    @staticmethod
    def _ensure_within_root(resolved_path: Path, root_path: Path) -> None:
        """Ensure a resolved path stays within the permitted root."""

        try:
            if resolved_path.is_relative_to(root_path):
                return
        except AttributeError:
            # Python < 3.9 compatibility (should not happen but guard regardless)
            resolved_str = str(resolved_path).replace("\\", "/")
            root_str = str(root_path).replace("\\", "/")
            if resolved_str.startswith(root_str):
                return

        raise ValueError("Path is outside the allowed root directory")

    @staticmethod
    def validate_file_path(file_path: str, root_dir: Path) -> Path:
        """Validate and resolve a file path, handling both absolute and relative paths."""

        try:
            root_path = root_dir.resolve()
            normalized_input = FileUtils._normalize_input_path(file_path)
            path_obj = Path(normalized_input)

            if FileUtils._is_absolute_like(path_obj, normalized_input):
                resolved = FileUtils._resolve_if_exists(path_obj)
                if resolved and resolved.is_relative_to(root_path):
                    return resolved

                mapped = FileUtils._map_absolute_to_root(path_obj, root_path)
                if mapped is None:
                    raise ValueError(f"Absolute path '{file_path}' cannot be mapped to root directory '{root_path}'")
                path_obj = mapped

            resolved_path = FileUtils._combine_with_root(path_obj, root_path)
            FileUtils._ensure_within_root(resolved_path, root_path)
            return resolved_path
        except (OSError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid file path '{file_path}': {error}") from error

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
                raise ValueError(f"File too large: {size} bytes (max: {max_size} bytes)")

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
    def _compile_patterns(keywords: list[str]) -> list[re.Pattern[str]]:
        """Compile keywords into regular expressions."""

        return [re.compile(keyword) for keyword in keywords]

    @staticmethod
    def _make_path_matcher(
        keywords: list[str],
        regex_mode: bool,
    ) -> Callable[[Path], bool] | None:
        """Create a callable that evaluates path-based keyword matches."""

        if not keywords:
            return None

        if regex_mode:
            patterns = FileUtils._compile_patterns(keywords)

            def regex_matcher(file_path: Path) -> bool:
                path_str = str(file_path)
                return any(pattern.search(path_str) for pattern in patterns)

            return regex_matcher

        def substring_matcher(file_path: Path) -> bool:
            path_str = str(file_path)
            return any(keyword in path_str for keyword in keywords)

        return substring_matcher

    @staticmethod
    def _make_content_matcher(
        keywords: list[str],
        regex_mode: bool,
    ) -> Callable[[Path], bool] | None:
        """Create a callable that evaluates content-based keyword matches."""

        if not keywords:
            return None

        if regex_mode:
            patterns = FileUtils._compile_patterns(keywords)

            def regex_matcher(file_path: Path) -> bool:
                if not FileUtils.is_text_file(file_path):
                    return False
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except (OSError, UnicodeDecodeError) as error:
                    logger.warning(f"Error reading file {file_path}: {error}")
                    return False
                return any(pattern.search(content) for pattern in patterns)

            return regex_matcher

        def substring_matcher(file_path: Path) -> bool:
            if not FileUtils.is_text_file(file_path):
                return False
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError) as error:
                logger.warning(f"Error reading file {file_path}: {error}")
                return False
            return any(keyword in content for keyword in keywords)

        return substring_matcher

    @staticmethod
    def find_files(
        directory_path: Path,
        path_keywords: list[str] | None = None,
        content_keywords: list[str] | None = None,
        regex_mode: bool = False,
        max_results: int = 1000,
    ) -> list[str]:
        """Find files matching keywords in path or content."""

        path_keywords = path_keywords or []
        content_keywords = content_keywords or []
        path_matcher = FileUtils._make_path_matcher(path_keywords, regex_mode)
        content_matcher = FileUtils._make_content_matcher(content_keywords, regex_mode)

        results: list[str] = []
        for file_path in directory_path.rglob("*"):
            if len(results) >= max_results:
                break
            if not file_path.is_file():
                continue

            path_match = path_matcher(file_path) if path_matcher else False
            content_match = False
            if content_matcher and (not path_matcher or path_match):
                content_match = content_matcher(file_path)

            if (path_matcher and path_match) or (content_matcher and content_match):
                results.append(str(file_path))

        return results
