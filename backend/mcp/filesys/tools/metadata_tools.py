"""Metadata tool functions for Filesys MCP server."""

import shutil
from typing import Any

from files.backend.mcp.filesys.tools.git_tools import git_commit_tool, git_status_tool
from files.backend.mcp.filesys.utils.metadata_config import (
    get_metadata_mappings,
    get_metadata_path,
    resolve_artifact_path,
)
from loguru import logger


async def metadata_list_tool(module: str | None = None) -> dict[str, Any]:
    """List metadata artifacts or mappings.

    Args:
        module: Module name to list artifacts for, or None to list all mappings

    Returns:
        Dict with mappings or artifacts
    """
    if module:
        # List artifacts for specific module
        meta_path = get_metadata_path(module)

        if not meta_path.exists():
            return {"module": module, "path": str(meta_path), "exists": False, "artifacts": {}}

        artifacts = {
            "progress": [str(p.relative_to(meta_path)) for p in (meta_path / "progress").rglob("*.md")] if (meta_path / "progress").exists() else [],
            "feedback": [str(p.relative_to(meta_path)) for p in (meta_path / "feedback").rglob("*.md")] if (meta_path / "feedback").exists() else [],
            "meta": [str(p.relative_to(meta_path)) for p in (meta_path / "meta").rglob("*") if p.is_dir()] if (meta_path / "meta").exists() else [],
        }

        total = sum(len(v) for v in artifacts.values())

        return {"module": module, "path": str(meta_path), "exists": True, "total": total, "artifacts": artifacts}

    # List all mappings
    mappings = get_metadata_mappings()
    return {"mappings": [{"module": m["module"], "path": m["metadataPath"], "active": m.get("isActive", True)} for m in mappings]}


async def metadata_read_tool(
    module: str,
    artifact_type: str,
    artifact_path: str,
) -> dict[str, Any]:
    """Read metadata artifact content.

    Args:
        module: Module name
        artifact_type: Artifact type (progress, feedback, meta)
        artifact_path: Relative path to artifact

    Returns:
        Dict with path and content
    """
    logger.debug(f"Reading metadata: module={module}, type={artifact_type}, path={artifact_path}")

    full_path = resolve_artifact_path(module, artifact_type, artifact_path)

    if not full_path.exists():
        return {"error": f"Artifact not found: {full_path}"}

    try:
        if full_path.is_dir():
            # List directory contents
            contents = [str(p.relative_to(full_path)) for p in full_path.iterdir()]
            return {"path": str(full_path), "is_dir": True, "contents": contents}

        # Read file
        content = full_path.read_text()
        return {"path": str(full_path), "is_dir": False, "content": content, "size": len(content)}

    except Exception as e:
        logger.error(f"Error reading {full_path}: {e}")
        return {"error": str(e)}


async def metadata_write_tool(
    module: str,
    artifact_type: str,
    artifact_path: str,
    content: str,
) -> dict[str, Any]:
    """Write metadata artifact.

    Args:
        module: Module name
        artifact_type: Artifact type (progress, feedback, meta)
        artifact_path: Relative path to artifact
        content: Content to write

    Returns:
        Dict with path and bytes written
    """
    logger.debug(f"Writing metadata: module={module}, type={artifact_type}, path={artifact_path}")

    full_path = resolve_artifact_path(module, artifact_type, artifact_path)

    try:
        # Ensure parent directories exist
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        full_path.write_text(content)

        return {"path": str(full_path), "written": len(content)}

    except Exception as e:
        logger.error(f"Error writing {full_path}: {e}")
        return {"error": str(e)}


async def metadata_delete_tool(
    module: str,
    artifact_type: str,
    artifact_path: str,
) -> dict[str, Any]:
    """Delete metadata artifact.

    Args:
        module: Module name
        artifact_type: Artifact type (progress, feedback, meta)
        artifact_path: Relative path to artifact

    Returns:
        Dict with path and deletion status
    """
    logger.debug(f"Deleting metadata: module={module}, type={artifact_type}, path={artifact_path}")

    full_path = resolve_artifact_path(module, artifact_type, artifact_path)

    if not full_path.exists():
        return {"error": f"Artifact not found: {full_path}"}

    try:
        if full_path.is_dir():
            shutil.rmtree(full_path)
        else:
            full_path.unlink()

        return {"path": str(full_path), "deleted": True}

    except Exception as e:
        logger.error(f"Error deleting {full_path}: {e}")
        return {"error": str(e)}


async def metadata_git_tool(
    module: str,
    git_action: str,
    message: str | None = None,
) -> dict[str, Any]:
    """Git operations on metadata directory.

    Args:
        module: Module name
        git_action: Git action (status, commit)
        message: Commit message (required for commit action)

    Returns:
        Dict with git operation result
    """
    logger.debug(f"Git operation: module={module}, action={git_action}")

    meta_path = get_metadata_path(module)

    if not meta_path.exists():
        return {"error": f"Metadata path does not exist: {meta_path}"}

    if not (meta_path / ".git").exists():
        return {"error": f"Not a git repository: {meta_path}"}

    if git_action == "status":
        return await git_status_tool(meta_path, repo_path=".")

    if git_action == "commit":
        if not message:
            return {"error": "Commit message required"}
        return await git_commit_tool(meta_path, message, repo_path=".")

    return {"error": f"Unknown git action: {git_action}"}
