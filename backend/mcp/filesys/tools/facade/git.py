"""Git operations facade tool."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from files.backend.mcp.filesys.tools.git_tools import (
    git_commit_tool,
    git_diff_tool,
    git_fetch_tool,
    git_history_tool,
    git_merge_abort_tool,
    git_pull_tool,
    git_push_tool,
    git_restore_tool,
    git_stage_tool,
    git_status_tool,
    git_unstage_tool,
)
from loguru import logger


async def _handle_status(
    root_dir: Path,
    repo_path: str | None,
    short: bool,
    branch: bool,
    untracked: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle status action."""
    return await git_status_tool(root_dir, repo_path, short, branch, untracked)


async def _handle_stage(
    root_dir: Path,
    repo_path: str | None,
    files: list[str] | None,
    stage_all: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle stage action."""
    return await git_stage_tool(root_dir, repo_path, files, stage_all)


async def _handle_unstage(
    root_dir: Path,
    repo_path: str | None,
    files: list[str] | None,
    unstage_all: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle unstage action."""
    return await git_unstage_tool(root_dir, repo_path, files, unstage_all)


async def _handle_commit(
    root_dir: Path,
    message: str | None,
    repo_path: str | None,
    amend: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle commit action."""
    if not message and not amend:
        return {"error": "message required for commit action (unless amending)"}
    return await git_commit_tool(root_dir, message or "", repo_path, amend)


async def _handle_diff(
    root_dir: Path,
    repo_path: str | None,
    staged: bool,
    files: list[str] | None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle diff action."""
    return await git_diff_tool(root_dir, repo_path, staged, files)


async def _handle_history(
    root_dir: Path,
    repo_path: str | None,
    limit: int,
    oneline: bool,
    grep: str | None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle history action."""
    return await git_history_tool(root_dir, repo_path, limit, oneline, grep)


async def _handle_restore(
    root_dir: Path,
    repo_path: str | None,
    files: list[str] | None,
    staged: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle restore action."""
    return await git_restore_tool(root_dir, repo_path, files, staged)


async def _handle_fetch(
    root_dir: Path,
    repo_path: str | None,
    remote: str,
    fetch_all: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle fetch action."""
    return await git_fetch_tool(root_dir, repo_path, remote, fetch_all)


async def _handle_pull(
    root_dir: Path,
    repo_path: str | None,
    remote: str,
    branch: str | None,
    rebase: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle pull action."""
    return await git_pull_tool(root_dir, repo_path, remote, branch, rebase)


async def _handle_push(
    root_dir: Path,
    repo_path: str | None,
    remote: str,
    branch: str | None,
    force: bool,
    set_upstream: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle push action."""
    return await git_push_tool(root_dir, repo_path, remote, branch, force, set_upstream)


async def _handle_merge_abort(
    root_dir: Path,
    repo_path: str | None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle merge_abort action."""
    return await git_merge_abort_tool(root_dir, repo_path)


_ACTION_HANDLERS: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
    "status": _handle_status,
    "stage": _handle_stage,
    "unstage": _handle_unstage,
    "commit": _handle_commit,
    "diff": _handle_diff,
    "history": _handle_history,
    "restore": _handle_restore,
    "fetch": _handle_fetch,
    "pull": _handle_pull,
    "push": _handle_push,
    "merge_abort": _handle_merge_abort,
}


async def git_tool(
    root_dir: Path,
    action: Literal[
        "status",
        "stage",
        "unstage",
        "commit",
        "diff",
        "history",
        "restore",
        "fetch",
        "pull",
        "push",
        "merge_abort",
    ],
    repo_path: str | None = None,
    message: str | None = None,
    files: list[str] | None = None,
    stage_all: bool = False,
    unstage_all: bool = False,
    amend: bool = False,
    staged: bool = False,
    limit: int = 10,
    oneline: bool = False,
    grep: str | None = None,
    remote: str = "origin",
    branch: str | None = None,
    fetch_all: bool = False,
    rebase: bool = False,
    force: bool = False,
    set_upstream: bool = False,
    short: bool = False,
    show_branch: bool = True,
    untracked: bool = True,
) -> dict[str, Any]:
    """Git operations facade.

    Args:
        root_dir: Root directory for operations
        action: Action to perform
        repo_path: Path to repository
        message: Commit message
        files: List of files
        stage_all: Stage all changes
        unstage_all: Unstage all changes
        amend: Amend previous commit
        staged: Show staged changes
        limit: History limit
        oneline: Oneline history format
        grep: History grep filter
        remote: Remote name
        branch: Branch name
        fetch_all: Fetch all remotes
        rebase: Rebase when pulling
        force: Force push
        set_upstream: Set upstream tracking
        short: Short status format
        show_branch: Show branch in status
        untracked: Show untracked files

    Returns:
        Dict with action-specific results
    """
    logger.debug(f"git_tool: action={action}, repo_path={repo_path}")

    handler = _ACTION_HANDLERS.get(action)
    if not handler:
        return {"error": f"Unknown action: {action}"}

    return await handler(
        root_dir=root_dir,
        repo_path=repo_path,
        message=message,
        files=files,
        stage_all=stage_all,
        unstage_all=unstage_all,
        amend=amend,
        staged=staged,
        limit=limit,
        oneline=oneline,
        grep=grep,
        remote=remote,
        branch=branch,
        fetch_all=fetch_all,
        rebase=rebase,
        force=force,
        set_upstream=set_upstream,
        short=short,
        show_branch=show_branch,
        untracked=untracked,
    )
