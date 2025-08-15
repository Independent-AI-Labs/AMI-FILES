"""Git tool handler implementations."""

import subprocess
from pathlib import Path
from typing import Any

from loguru import logger


async def git_stage(
    root_dir: Path,
    paths: list[str],
    force: bool = False,
    update: bool = False,
) -> dict[str, Any]:
    """Stage files for commit.

    Args:
        root_dir: Root directory for operations
        paths: File paths to stage
        force: Force add ignored files
        update: Only update tracked files

    Returns:
        Result with staging status
    """
    try:
        # Build git add command
        cmd = ["git", "add"]

        if force:
            cmd.append("-f")
        if update:
            cmd.append("-u")

        # Add paths
        if paths:
            cmd.extend(paths)
        else:
            return {"error": "No paths specified to stage"}

        # Execute command
        result = subprocess.run(
            cmd,
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return {"error": f"Failed to stage files: {result.stderr}"}

        # Get status to show what was staged
        status_result = subprocess.run(
            ["git", "status", "--short"],
            cwd=root_dir,
            capture_output=True,
            text=True,
        )

        staged_files = []
        for line in status_result.stdout.splitlines():
            if line and line[0] in "AM":
                staged_files.append(line[3:].strip())

        return {
            "result": {
                "message": f"Successfully staged {len(staged_files)} file(s)",
                "staged_files": staged_files,
                "paths": paths,
            }
        }

    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        logger.error(f"Failed to stage files: {e}")
        return {"error": str(e)}


async def git_unstage(root_dir: Path, paths: list[str]) -> dict[str, Any]:
    """Unstage files from staging area.

    Args:
        root_dir: Root directory for operations
        paths: File paths to unstage (empty for all)

    Returns:
        Result with unstaging status
    """
    try:
        # Build git reset command
        cmd = ["git", "reset", "HEAD"]

        if paths:
            cmd.extend(paths)

        # Execute command
        result = subprocess.run(
            cmd,
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0 and "fatal" in result.stderr:
            return {"error": f"Failed to unstage files: {result.stderr}"}

        return {
            "result": {
                "message": "Successfully unstaged files",
                "paths": paths if paths else ["all"],
                "output": result.stdout,
            }
        }

    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        logger.error(f"Failed to unstage files: {e}")
        return {"error": str(e)}


async def git_commit(
    root_dir: Path,
    message: str,
    amend: bool = False,
    allow_empty: bool = False,
    author: str | None = None,
) -> dict[str, Any]:
    """Create a commit with staged changes.

    Args:
        root_dir: Root directory for operations
        message: Commit message
        amend: Amend the last commit
        allow_empty: Allow empty commits
        author: Override author

    Returns:
        Result with commit status
    """
    try:
        # Build git commit command
        cmd = ["git", "commit", "-m", message]

        if amend:
            cmd.append("--amend")
        if allow_empty:
            cmd.append("--allow-empty")
        if author:
            cmd.extend(["--author", author])

        # Execute command
        result = subprocess.run(
            cmd,
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            if "nothing to commit" in result.stdout:
                return {
                    "result": {
                        "message": "Nothing to commit, working tree clean",
                        "output": result.stdout,
                    }
                }
            return {"error": f"Failed to commit: {result.stderr or result.stdout}"}

        # Extract commit hash from output
        commit_hash = None
        for line in result.stdout.splitlines():
            if line.startswith("[") and "]" in line:
                parts = line.split("]")[0].split()
                if len(parts) >= 2:
                    commit_hash = parts[1]
                    break

        return {
            "result": {
                "message": "Successfully created commit",
                "commit_hash": commit_hash,
                "output": result.stdout,
            }
        }

    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        logger.error(f"Failed to create commit: {e}")
        return {"error": str(e)}


async def git_diff(
    root_dir: Path,
    paths: list[str] | None = None,
    staged: bool = False,
    name_only: bool = False,
    stat: bool = False,
    commit: str | None = None,
) -> dict[str, Any]:
    """Show differences between files.

    Args:
        root_dir: Root directory for operations
        paths: Specific paths to diff
        staged: Show staged changes
        name_only: Show only file names
        stat: Show diffstat
        commit: Show diff for specific commit

    Returns:
        Result with diff output
    """
    try:
        # Build git diff command
        cmd = ["git", "diff"]

        if staged:
            cmd.append("--cached")
        if name_only:
            cmd.append("--name-only")
        if stat:
            cmd.append("--stat")
        if commit:
            cmd.append(commit)

        if paths:
            cmd.append("--")
            cmd.extend(paths)

        # Execute command
        result = subprocess.run(
            cmd,
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return {"error": f"Failed to get diff: {result.stderr}"}

        if not result.stdout:
            return {
                "result": {
                    "message": "No differences found",
                    "diff": "",
                }
            }

        return {
            "result": {
                "message": "Diff generated successfully",
                "diff": result.stdout,
                "type": "staged" if staged else "working",
            }
        }

    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        logger.error(f"Failed to get diff: {e}")
        return {"error": str(e)}


async def git_history(
    root_dir: Path,
    limit: int = 20,
    oneline: bool = True,
    paths: list[str] | None = None,
    author: str | None = None,
    since: str | None = None,
    until: str | None = None,
    grep: str | None = None,
) -> dict[str, Any]:
    """Show commit history.

    Args:
        root_dir: Root directory for operations
        limit: Maximum number of commits
        oneline: Show in compact format
        paths: Show history for specific paths
        author: Filter by author
        since: Show commits since date
        until: Show commits until date
        grep: Filter by message pattern

    Returns:
        Result with commit history
    """
    try:
        # Build git log command
        cmd = ["git", "log", f"-{limit}"]

        if oneline:
            cmd.append("--oneline")
        else:
            cmd.append("--pretty=format:%H|%an|%ae|%ad|%s")
            cmd.append("--date=iso")

        if author:
            cmd.extend(["--author", author])
        if since:
            cmd.extend(["--since", since])
        if until:
            cmd.extend(["--until", until])
        if grep:
            cmd.extend(["--grep", grep])

        if paths:
            cmd.append("--")
            cmd.extend(paths)

        # Execute command
        result = subprocess.run(
            cmd,
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            if "does not have any commits" in result.stderr:
                return {
                    "result": {
                        "message": "No commits found",
                        "commits": [],
                    }
                }
            return {"error": f"Failed to get history: {result.stderr}"}

        # Parse output
        commits = []
        if oneline:
            for line in result.stdout.splitlines():
                if line:
                    parts = line.split(None, 1)
                    commits.append(
                        {
                            "hash": parts[0] if parts else "",
                            "message": parts[1] if len(parts) > 1 else "",
                        }
                    )
        else:
            for line in result.stdout.splitlines():
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 5:
                        commits.append(
                            {
                                "hash": parts[0],
                                "author": parts[1],
                                "email": parts[2],
                                "date": parts[3],
                                "message": parts[4],
                            }
                        )

        return {
            "result": {
                "message": f"Found {len(commits)} commit(s)",
                "commits": commits,
                "limit": limit,
            }
        }

    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        logger.error(f"Failed to get history: {e}")
        return {"error": str(e)}


async def git_restore(
    root_dir: Path,
    paths: list[str],
    staged: bool = False,
    source: str | None = None,
) -> dict[str, Any]:
    """Restore working tree files.

    Args:
        root_dir: Root directory for operations
        paths: File paths to restore
        staged: Restore from staging area
        source: Restore from specific commit/branch

    Returns:
        Result with restore status
    """
    try:
        if not paths:
            return {"error": "No paths specified to restore"}

        # Build git restore command (or checkout for older git)
        # First try git restore (newer git)
        cmd = ["git", "restore"]

        if staged:
            cmd.append("--staged")
        if source:
            cmd.extend(["--source", source])

        cmd.extend(paths)

        # Execute command
        result = subprocess.run(
            cmd,
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        # If restore doesn't exist, fall back to checkout
        if "restore" in result.stderr and "is not a git command" in result.stderr:
            cmd = ["git", "checkout"]
            if source:
                cmd.append(source)
            cmd.append("--")
            cmd.extend(paths)

            result = subprocess.run(
                cmd,
                cwd=root_dir,
                capture_output=True,
                text=True,
                check=False,
            )

        if result.returncode != 0:
            return {"error": f"Failed to restore files: {result.stderr}"}

        return {
            "result": {
                "message": f"Successfully restored {len(paths)} file(s)",
                "paths": paths,
                "source": source or "HEAD",
            }
        }

    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        logger.error(f"Failed to restore files: {e}")
        return {"error": str(e)}


async def git_fetch(
    root_dir: Path,
    remote: str = "origin",
    branch: str | None = None,
    all: bool = False,
    prune: bool = False,
    tags: bool = True,
) -> dict[str, Any]:
    """Fetch updates from remote repository.

    Args:
        root_dir: Root directory for operations
        remote: Remote name
        branch: Specific branch to fetch
        all: Fetch all remotes
        prune: Prune deleted remote branches
        tags: Fetch tags

    Returns:
        Result with fetch status
    """
    try:
        # Build git fetch command
        cmd = ["git", "fetch"]

        if all:
            cmd.append("--all")
        else:
            cmd.append(remote)
            if branch:
                cmd.append(branch)

        if prune:
            cmd.append("--prune")
        if tags:
            cmd.append("--tags")
        else:
            cmd.append("--no-tags")

        # Execute command
        result = subprocess.run(
            cmd,
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return {"error": f"Failed to fetch: {result.stderr}"}

        # Parse output for updates
        updates = []
        for line in result.stderr.splitlines():
            if "->" in line or "new tag" in line or "new branch" in line:
                updates.append(line.strip())

        return {
            "result": {
                "message": "Fetch completed successfully",
                "remote": "all" if all else remote,
                "updates": updates,
                "output": result.stderr or "Already up to date",
            }
        }

    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        logger.error(f"Failed to fetch: {e}")
        return {"error": str(e)}


async def git_pull(
    root_dir: Path,
    remote: str = "origin",
    branch: str | None = None,
    rebase: bool = False,
    ff_only: bool = False,
    strategy: str | None = None,
) -> dict[str, Any]:
    """Pull changes from remote repository.

    Args:
        root_dir: Root directory for operations
        remote: Remote name
        branch: Branch to pull from
        rebase: Use rebase instead of merge
        ff_only: Only fast-forward merge
        strategy: Merge strategy

    Returns:
        Result with pull status
    """
    try:
        # Build git pull command
        cmd = ["git", "pull"]

        if rebase:
            cmd.append("--rebase")
        if ff_only:
            cmd.append("--ff-only")
        if strategy:
            cmd.extend(["--strategy", strategy])

        cmd.append(remote)
        if branch:
            cmd.append(branch)

        # Execute command
        result = subprocess.run(
            cmd,
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            if (
                "conflict" in result.stdout.lower()
                or "conflict" in result.stderr.lower()
            ):
                return {
                    "error": "Pull failed due to conflicts. Resolve conflicts and commit.",
                    "details": result.stdout + result.stderr,
                }
            return {"error": f"Failed to pull: {result.stderr}"}

        # Parse output for changes
        files_changed = 0
        insertions = 0
        deletions = 0

        for line in result.stdout.splitlines():
            if "files changed" in line or "file changed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if "file" in part:
                        files_changed = int(parts[i - 1])
                    elif "insertion" in part:
                        insertions = int(parts[i - 1])
                    elif "deletion" in part:
                        deletions = int(parts[i - 1])

        return {
            "result": {
                "message": "Pull completed successfully",
                "remote": remote,
                "branch": branch or "current",
                "files_changed": files_changed,
                "insertions": insertions,
                "deletions": deletions,
                "output": result.stdout,
            }
        }

    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        logger.error(f"Failed to pull: {e}")
        return {"error": str(e)}


async def git_merge_abort(root_dir: Path) -> dict[str, Any]:
    """Abort an ongoing merge operation.

    Args:
        root_dir: Root directory for operations

    Returns:
        Result with abort status
    """
    try:
        # Execute git merge --abort
        result = subprocess.run(
            ["git", "merge", "--abort"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            if "There is no merge to abort" in result.stderr:
                return {
                    "result": {
                        "message": "No merge in progress",
                        "status": "clean",
                    }
                }
            return {"error": f"Failed to abort merge: {result.stderr}"}

        return {
            "result": {
                "message": "Successfully aborted merge",
                "status": "aborted",
                "output": result.stdout or "Merge aborted",
            }
        }

    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        logger.error(f"Failed to abort merge: {e}")
        return {"error": str(e)}


async def git_push(
    root_dir: Path,
    remote: str = "origin",
    branch: str | None = None,
    force: bool = False,
    set_upstream: bool = False,
    tags: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Push commits to remote repository.

    Args:
        root_dir: Root directory for operations
        remote: Remote name
        branch: Branch to push
        force: Force push
        set_upstream: Set upstream tracking branch
        tags: Push tags
        dry_run: Dry run

    Returns:
        Result with push status
    """
    try:
        # Build git push command
        cmd = ["git", "push"]

        if force:
            cmd.append("--force")
        if set_upstream:
            cmd.append("--set-upstream")
        if tags:
            cmd.append("--tags")
        if dry_run:
            cmd.append("--dry-run")

        cmd.append(remote)
        if branch:
            cmd.append(branch)

        # Execute command
        result = subprocess.run(
            cmd,
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return {"error": f"Failed to push: {result.stderr}"}

        # Check if up-to-date
        if "Everything up-to-date" in result.stderr:
            return {
                "result": {
                    "message": "Everything up-to-date",
                    "remote": remote,
                    "branch": branch or "current",
                    "status": "up-to-date",
                }
            }

        # Parse output for push info
        pushed_refs = []
        for line in result.stderr.splitlines():
            if "->" in line or "new branch" in line or "new tag" in line:
                pushed_refs.append(line.strip())

        return {
            "result": {
                "message": "Push completed successfully",
                "remote": remote,
                "branch": branch or "current",
                "pushed_refs": pushed_refs,
                "dry_run": dry_run,
                "output": result.stderr or result.stdout,
            }
        }

    except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
        logger.error(f"Failed to push: {e}")
        return {"error": str(e)}
