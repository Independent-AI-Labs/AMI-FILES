"""Git tool functions for Filesys MCP server."""

import asyncio
import os
import shutil
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


def _get_git_executable() -> str:
    """Get absolute path to git executable.

    Returns:
        Absolute path to git command

    Raises:
        RuntimeError: If git is not found in PATH
    """
    git_path = shutil.which("git")
    if git_path is None:
        raise RuntimeError("git is not installed or not in PATH")
    return git_path


def _git_environment() -> dict[str, str]:
    """Return environment without git variables that break nested repos."""
    env = dict(os.environ)
    for var in _SANITIZED_GIT_ENV_VARS:
        env.pop(var, None)
    return env


def _run_git_command(work_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Execute git command with sanitized environment."""
    git_exe = _get_git_executable()
    return subprocess.run(
        [git_exe, *args],
        cwd=work_dir,
        capture_output=True,
        text=True,
        check=False,
        env=_git_environment(),
    )


def _find_orchestrator_root(start_path: Path) -> Path:
    """Find orchestrator root (has /base and /scripts directories).

    Args:
        start_path: Starting path for search (typically repo root)

    Returns:
        Path to orchestrator root

    Raises:
        RuntimeError: If orchestrator root not found
    """
    current = start_path.resolve()
    while current != current.parent:
        if (current / "base").exists() and (current / "scripts").exists():
            return current
        current = current.parent
    raise RuntimeError(f"Cannot find orchestrator root from {start_path}")


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
) -> dict[str, Any]:
    """Commit changes using scripts/git_commit.sh (auto-stages all changes).

    Args:
        root_dir: Root directory for operations
        message: Commit message
        repo_path: Path to repository (relative to root_dir)
        amend: Whether to amend previous commit

    Returns:
        Dict with success status and output, or error details
    """
    logger.debug(f"Committing: message={message}, repo_path={repo_path}, amend={amend}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        # Find orchestrator root and git_commit.sh script
        orchestrator_root = _find_orchestrator_root(work_dir)
        git_commit_script = orchestrator_root / "scripts" / "git_commit.sh"

        if not git_commit_script.exists():
            raise FileNotFoundError(f"git_commit.sh not found: {git_commit_script}")

        # Build command - script auto-stages all changes (git add -A)
        cmd = [str(git_commit_script), "--amend"] if amend else [str(git_commit_script), message]

        # Call script directly via subprocess
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        success = proc.returncode == 0
        output = stdout.decode() if success else stderr.decode()

        if not success:
            return {"error": output}

        return {
            "success": True,
            "output": output,
            "auto_staged": True,  # Script always runs git add -A
        }

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
    """Push to remote using scripts/git_push.sh (runs tests first).

    Args:
        root_dir: Root directory for operations
        repo_path: Path to repository (relative to root_dir)
        remote: Remote name
        branch: Branch name
        force: Force push (will be rejected by script)
        set_upstream: Set upstream tracking

    Returns:
        Dict with success status and output, or error details
    """
    logger.debug(f"Pushing: repo_path={repo_path}, remote={remote}, branch={branch}")

    try:
        work_dir = validate_path(root_dir, repo_path or ".")

        # Find orchestrator root and git_push.sh script
        orchestrator_root = _find_orchestrator_root(work_dir)
        git_push_script = orchestrator_root / "scripts" / "git_push.sh"

        if not git_push_script.exists():
            raise FileNotFoundError(f"git_push.sh not found: {git_push_script}")

        # Build command - script runs tests before push
        cmd = [str(git_push_script), remote]
        if branch:
            cmd.append(branch)
        if force:
            cmd.append("--force")  # Script will reject this
        if set_upstream:
            cmd.extend(["--set-upstream", remote, branch or ""])

        # Call script directly via subprocess
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        success = proc.returncode == 0
        output = stdout.decode() if success else stderr.decode()

        if not success:
            return {"error": output}

        return {
            "success": True,
            "output": output,
            "tests_run": True,  # Script always runs tests
        }

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
