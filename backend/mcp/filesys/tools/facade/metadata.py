"""Metadata operations facade tool."""

from typing import Any, Literal

from files.backend.mcp.filesys.tools.metadata_tools import (
    metadata_delete_tool,
    metadata_git_tool,
    metadata_list_tool,
    metadata_read_tool,
    metadata_write_tool,
)
from loguru import logger


async def metadata_tool(
    action: Literal["list", "read", "write", "delete", "git"],
    module: str | None = None,
    artifact_type: str | None = None,
    artifact_path: str | None = None,
    content: str | None = None,
    git_action: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """Metadata management facade.

    Args:
        action: Action to perform
        module: Module name
        artifact_type: Artifact type (progress, feedback, meta)
        artifact_path: Relative path to artifact
        content: Content to write
        git_action: Git action (status, commit)
        message: Commit message

    Returns:
        Dict with action-specific results
    """
    logger.debug(f"metadata_tool: action={action}, module={module}")

    action_handlers = {
        "list": lambda: metadata_list_tool(module),
        "read": lambda: _handle_read(module, artifact_type, artifact_path),
        "write": lambda: _handle_write(module, artifact_type, artifact_path, content),
        "delete": lambda: _handle_delete(module, artifact_type, artifact_path),
        "git": lambda: _handle_git(module, git_action, message),
    }

    handler = action_handlers.get(action)
    if handler:
        return await handler()
    return {"error": f"Unknown action: {action}"}


async def _handle_read(module: str | None, artifact_type: str | None, artifact_path: str | None) -> dict[str, Any]:
    """Handle read action."""
    if not module or not artifact_type or not artifact_path:
        return {"error": "module, artifact_type, and artifact_path required for read action"}
    return await metadata_read_tool(module, artifact_type, artifact_path)


async def _handle_write(module: str | None, artifact_type: str | None, artifact_path: str | None, content: str | None) -> dict[str, Any]:
    """Handle write action."""
    if not module or not artifact_type or not artifact_path or content is None:
        return {"error": "module, artifact_type, artifact_path, and content required for write action"}
    return await metadata_write_tool(module, artifact_type, artifact_path, content)


async def _handle_delete(module: str | None, artifact_type: str | None, artifact_path: str | None) -> dict[str, Any]:
    """Handle delete action."""
    if not module or not artifact_type or not artifact_path:
        return {"error": "module, artifact_type, and artifact_path required for delete action"}
    return await metadata_delete_tool(module, artifact_type, artifact_path)


async def _handle_git(module: str | None, git_action: str | None, message: str | None) -> dict[str, Any]:
    """Handle git action."""
    if not module or not git_action:
        return {"error": "module and git_action required for git action"}
    return await metadata_git_tool(module, git_action, message)
