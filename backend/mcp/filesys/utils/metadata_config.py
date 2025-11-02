"""Metadata configuration utilities."""

import json
import os
from pathlib import Path
from typing import Any, TypedDict, cast


class MetadataMapping(TypedDict):
    """Metadata mapping configuration."""

    module: str
    metadataPath: str
    isActive: bool


def get_metadata_config_path() -> Path:
    """Get path to metadata mappings config file."""
    return Path("data/metadata-mappings.json")


def get_metadata_mappings() -> list[MetadataMapping]:
    """Load metadata mappings from JSON config.

    Returns:
        List of metadata mappings
    """
    config_path = get_metadata_config_path()
    if not config_path.exists():
        return []

    with config_path.open() as f:
        data: dict[str, Any] = json.load(f)

    return cast(list[MetadataMapping], data.get("mappings", []))


def get_default_metadata_root() -> str:
    """Get default metadata root directory.

    Returns:
        Default metadata root path
    """
    # Check environment variable
    env_root = os.getenv("METADATA_DEFAULT_ROOT")
    if env_root:
        return env_root

    # Check config file
    config_path = get_metadata_config_path()
    if config_path.exists():
        with config_path.open() as f:
            data: dict[str, Any] = json.load(f)
            if "defaultRoot" in data:
                return cast(str, data["defaultRoot"])

    # Default
    return ".ami-metadata"


def get_metadata_path(module: str) -> Path:
    """Get metadata path for module.

    Args:
        module: Module name (base, compliance, ux, etc.)

    Returns:
        Path to metadata directory for the module
    """
    mappings = get_metadata_mappings()

    # Find active mapping for module
    for mapping in mappings:
        if mapping["module"] == module and mapping.get("isActive", True):
            return Path(mapping["metadataPath"])

    # No mapping found: use default root
    default_root = get_default_metadata_root()
    return Path(default_root) / module


def resolve_artifact_path(module: str, artifact_type: str, relative_path: str) -> Path:
    """Resolve full path to metadata artifact.

    Args:
        module: Module name
        artifact_type: Artifact type (progress, feedback, meta)
        relative_path: Relative path within artifact type

    Returns:
        Full path to artifact
    """
    meta_path = get_metadata_path(module)
    return meta_path / artifact_type / relative_path


def save_metadata_mappings(mappings: list[MetadataMapping], default_root: str | None = None) -> None:
    """Save metadata mappings to config file.

    Args:
        mappings: List of metadata mappings
        default_root: Default metadata root (optional)
    """
    config_path = get_metadata_config_path()

    # Ensure data directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config: dict[str, Any] = {"mappings": mappings}

    if default_root:
        config["defaultRoot"] = default_root

    with config_path.open("w") as f:
        json.dump(config, f, indent=2)
