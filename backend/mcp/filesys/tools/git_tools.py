"""Git tool functions for Filesys MCP server."""

import os
import subprocess
from pathlib import Path
from typing import Any

from files.backend.mcp.filesys.utils.path_utils import validate_path
from loguru import logger

_SANITIZED_GIT_ENV_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_NAMESPACE",
    "GIT_COMMON_DIR",
)


def _git_environment() -> dict[str, str]:
    """Return environment without git variables that break nested repos."""
    env = dict(os.environ)
    for var in _SANITIZED_GIT_ENV_VARS:
        env.pop(var, None)
    return env


def _run_git_command(work_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Execute git command with sanitized environment."""
    return subprocess.run(
        ["git", *args],
        cwd=work_dir,
        capture_output=True,
        text=True,
        check=False,
        env=_git_environment(),
    )


async def git_status_tool(
    root_dir: Path,
    repo_path: str | None = None,
    short: bool = False,
    branch: bool = True,
    untracked: bool = True,
) -> dict[str, Any]:
    """Get git repository status."""
    logger.debug(f"Getting git status: repo_path={repo_path}, short={short}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        cmd = ["status"]
        if short:
            cmd.append("--short")
        if branch:
            cmd.append("--branch")
        if not untracked:
            cmd.append("--untracked-files=no")

        result = _run_git_command(work_dir, *cmd)

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"success": True, "output": result.stdout}
    except Exception as e:
        logger.error(f"Failed to get git status: {e}")
        return {"error": str(e)}


async def git_stage_tool(
    root_dir: Path,
    repo_path: str | None = None,
    files: list[str] | None = None,
    stage_all: bool = False,
) -> dict[str, Any]:
    """Stage files for commit."""
    logger.debug(f"Staging files: repo_path={repo_path}, files={files}, stage_all={stage_all}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        if stage_all:
            cmd = ["add", "-A"]
        elif files:
            cmd = ["add", *files]
        else:
            return {"error": "Must specify files or use stage_all=True"}

        result = _run_git_command(work_dir, *cmd)

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"success": True, "message": "Files staged successfully"}
    except Exception as e:
        logger.error(f"Failed to stage files: {e}")
        return {"error": str(e)}


async def git_unstage_tool(
    root_dir: Path,
    repo_path: str | None = None,
    files: list[str] | None = None,
    unstage_all: bool = False,
) -> dict[str, Any]:
    """Unstage files."""
    logger.debug(f"Unstaging files: repo_path={repo_path}, files={files}, unstage_all={unstage_all}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        if unstage_all:
            cmd = ["reset", "HEAD"]
        elif files:
            cmd = ["reset", "HEAD", *files]
        else:
            return {"error": "Must specify files or use unstage_all=True"}

        result = _run_git_command(work_dir, *cmd)

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"success": True, "message": "Files unstaged successfully"}
    except Exception as e:
        logger.error(f"Failed to unstage files: {e}")
        return {"error": str(e)}


async def git_commit_tool(
    root_dir: Path,
    message: str,
    repo_path: str | None = None,
    amend: bool = False,
    include_tracked: bool = False,
) -> dict[str, Any]:
    """Commit changes."""
    logger.debug(f"Committing: message={message}, repo_path={repo_path}, amend={amend}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        cmd = ["commit", "-m", message]
        if amend:
            cmd.append("--amend")
        if include_tracked:
            cmd.append("-a")

        result = _run_git_command(work_dir, *cmd)

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"success": True, "output": result.stdout}
    except Exception as e:
        logger.error(f"Failed to commit: {e}")
        return {"error": str(e)}


async def git_diff_tool(
    root_dir: Path,
    repo_path: str | None = None,
    staged: bool = False,
    files: list[str] | None = None,
) -> dict[str, Any]:
    """Show differences."""
    logger.debug(f"Getting diff: repo_path={repo_path}, staged={staged}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        cmd = ["diff"]
        if staged:
            cmd.append("--staged")
        if files:
            cmd.extend(files)

        result = _run_git_command(work_dir, *cmd)

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"success": True, "diff": result.stdout}
    except Exception as e:
        logger.error(f"Failed to get diff: {e}")
        return {"error": str(e)}


async def git_history_tool(
    root_dir: Path,
    repo_path: str | None = None,
    limit: int = 10,
    oneline: bool = False,
    grep: str | None = None,
) -> dict[str, Any]:
    """Show commit history with optional grep filtering."""
    logger.debug(f"Getting history: repo_path={repo_path}, limit={limit}, grep={grep}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        cmd = ["log", f"-{limit}"]
        if grep:
            cmd.extend(["--grep", grep])
        if oneline:
            cmd.append("--oneline")

        result = _run_git_command(work_dir, *cmd)

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"success": True, "history": result.stdout}
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        return {"error": str(e)}


async def git_restore_tool(
    root_dir: Path,
    repo_path: str | None = None,
    files: list[str] | None = None,
    staged: bool = False,
) -> dict[str, Any]:
    """Restore files."""
    logger.debug(f"Restoring files: repo_path={repo_path}, files={files}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        if not files:
            return {"error": "Must specify files to restore"}

        cmd = ["restore"]
        if staged:
            cmd.append("--staged")
        cmd.extend(files)

        result = _run_git_command(work_dir, *cmd)

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"success": True, "message": "Files restored successfully"}
    except Exception as e:
        logger.error(f"Failed to restore files: {e}")
        return {"error": str(e)}


async def git_fetch_tool(
    root_dir: Path,
    repo_path: str | None = None,
    remote: str = "origin",
    fetch_all: bool = False,
) -> dict[str, Any]:
    """Fetch from remote."""
    logger.debug(f"Fetching: repo_path={repo_path}, remote={remote}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        cmd = ["fetch"]
        if fetch_all:
            cmd.append("--all")
        else:
            cmd.append(remote)

        result = _run_git_command(work_dir, *cmd)

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"success": True, "output": result.stdout or "Fetch completed"}
    except Exception as e:
        logger.error(f"Failed to fetch: {e}")
        return {"error": str(e)}


async def git_pull_tool(
    root_dir: Path,
    repo_path: str | None = None,
    remote: str = "origin",
    branch: str | None = None,
    rebase: bool = False,
) -> dict[str, Any]:
    """Pull from remote."""
    logger.debug(f"Pulling: repo_path={repo_path}, remote={remote}, branch={branch}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        cmd = ["pull"]
        if rebase:
            cmd.append("--rebase")
        cmd.append(remote)
        if branch:
            cmd.append(branch)

        result = _run_git_command(work_dir, *cmd)

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"success": True, "output": result.stdout}
    except Exception as e:
        logger.error(f"Failed to pull: {e}")
        return {"error": str(e)}


async def git_push_tool(
    root_dir: Path,
    repo_path: str | None = None,
    remote: str = "origin",
    branch: str | None = None,
    force: bool = False,
    set_upstream: bool = False,
) -> dict[str, Any]:
    """Push to remote."""
    logger.debug(f"Pushing: repo_path={repo_path}, remote={remote}, branch={branch}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        cmd = ["push"]
        if force:
            cmd.append("--force")
        if set_upstream:
            cmd.append("--set-upstream")
        cmd.append(remote)
        if branch:
            cmd.append(branch)

        result = _run_git_command(work_dir, *cmd)

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"success": True, "output": result.stdout}
    except Exception as e:
        logger.error(f"Failed to push: {e}")
        return {"error": str(e)}


async def git_merge_abort_tool(root_dir: Path, repo_path: str | None = None) -> dict[str, Any]:
    """Abort merge."""
    logger.debug(f"Aborting merge: repo_path={repo_path}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        cmd = ["merge", "--abort"]

        result = _run_git_command(work_dir, *cmd)

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"success": True, "message": "Merge aborted successfully"}
    except Exception as e:
        logger.error(f"Failed to abort merge: {e}")
        return {"error": str(e)}
