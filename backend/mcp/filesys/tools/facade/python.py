"""Python execution facade tool."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from files.backend.mcp.filesys.tools.python_tools import (
    python_list_tasks_tool,
    python_run_background_tool,
    python_run_tool,
    python_task_cancel_tool,
    python_task_status_tool,
)
from loguru import logger


async def _handle_run(
    root_dir: Path,
    script: str | None,
    args: list[str] | None,
    timeout: int,
    cwd: str | None,
    python: str,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle run action."""
    if not script:
        return {"error": "script required for run action"}
    return await python_run_tool(root_dir, script, args, timeout, cwd, python)


async def _handle_run_background(
    root_dir: Path,
    script: str | None,
    args: list[str] | None,
    cwd: str | None,
    python: str,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle run_background action."""
    if not script:
        return {"error": "script required for run_background action"}
    return await python_run_background_tool(root_dir, script, args, cwd, python)


async def _handle_task_status(
    task_id: str | None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle task_status action."""
    if not task_id:
        return {"error": "task_id required for task_status action"}
    return await python_task_status_tool(task_id)


async def _handle_task_cancel(
    task_id: str | None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle task_cancel action."""
    if not task_id:
        return {"error": "task_id required for task_cancel action"}
    return await python_task_cancel_tool(task_id)


async def _handle_list_tasks(**_kwargs: Any) -> dict[str, Any]:
    """Handle list_tasks action."""
    return await python_list_tasks_tool()


_ACTION_HANDLERS: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
    "run": _handle_run,
    "run_background": _handle_run_background,
    "task_status": _handle_task_status,
    "task_cancel": _handle_task_cancel,
    "list_tasks": _handle_list_tasks,
}


async def python_tool(
    root_dir: Path,
    action: Literal["run", "run_background", "task_status", "task_cancel", "list_tasks"],
    script: str | None = None,
    args: list[str] | None = None,
    timeout: int = 300,
    cwd: str | None = None,
    python: str = "venv",
    task_id: str | None = None,
) -> dict[str, Any]:
    """Python execution facade.

    Args:
        root_dir: Root directory for operations
        action: Action to perform
        script: Script path or code to execute
        args: Script arguments
        timeout: Execution timeout
        cwd: Working directory
        python: Python executable
        task_id: Background task ID

    Returns:
        Dict with action-specific results
    """
    logger.debug(f"python_tool: action={action}, script={script}, task_id={task_id}")

    handler = _ACTION_HANDLERS.get(action)
    if not handler:
        return {"error": f"Unknown action: {action}"}

    return await handler(
        root_dir=root_dir,
        script=script,
        args=args,
        timeout=timeout,
        cwd=cwd,
        python=python,
        task_id=task_id,
    )
