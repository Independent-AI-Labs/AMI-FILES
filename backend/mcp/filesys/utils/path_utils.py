"""Path utilities for filesystem operations."""

from pathlib import Path

from loguru import logger


def validate_path(root_dir: Path, path: str, allow_write: bool = True) -> Path:
    """Validate and resolve a path within the root directory.

    Args:
        root_dir: Root directory for operations
        path: Path to validate (relative or absolute)
        allow_write: If False, blocks write operations to protected folders

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path is outside root directory or in protected folder
    """
    try:
        # Convert to Path object
        target_path = Path(path)

        # Resolve relative to root, regardless of original form
        resolved = target_path.resolve() if target_path.is_absolute() else (root_dir / target_path).resolve()

        # Ensure the resolved path is under root_dir
        resolved_root = root_dir.resolve()
        resolved.relative_to(resolved_root)

        # Check for protected directories if write operation
        if not allow_write:
            # Get relative path for checking
            rel_path = resolved.relative_to(resolved_root)
            path_parts = rel_path.parts

            # Protected directories
            protected_dirs = {
                ".git",
                ".venv",
                "build",
                "__pycache__",
                "node_modules",
                ".pytest_cache",
            }

            # Check if any part of the path contains protected directories
            for part in path_parts:
                if part in protected_dirs:
                    raise ValueError(f"Cannot modify files in protected directory '{part}'")

        return resolved
    except (ValueError, OSError) as e:
        logger.error(f"Path validation failed for {path}: {e}")
        raise ValueError(f"Path '{path}' is not allowed or invalid: {e!s}") from e
