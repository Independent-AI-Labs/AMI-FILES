"""Path utilities for filesystem operations."""

from pathlib import Path

from loguru import logger


def validate_path(root_dir: Path, path: str) -> Path:
    """Validate and resolve a path within the root directory.

    Args:
        root_dir: Root directory for operations
        path: Path to validate (relative or absolute)

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path is outside root directory
    """
    try:
        # Convert to Path object
        target_path = Path(path)

        # If absolute, ensure it's under root_dir
        if target_path.is_absolute():
            resolved = target_path.resolve()
        else:
            # If relative, resolve relative to root_dir
            resolved = (root_dir / target_path).resolve()

        # Ensure the resolved path is under root_dir
        resolved_root = root_dir.resolve()
        resolved.relative_to(resolved_root)

        return resolved
    except (ValueError, OSError) as e:
        logger.error(f"Path validation failed for {path}: {e}")
        raise ValueError(f"Path '{path}' is not allowed or invalid") from e
