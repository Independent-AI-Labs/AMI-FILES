"""Unit tests for git tools in filesystem MCP server."""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from files.backend.mcp.filesys.tools.git_tools import (
    git_commit_tool as git_commit,
)
from files.backend.mcp.filesys.tools.git_tools import (
    git_diff_tool as git_diff,
)
from files.backend.mcp.filesys.tools.git_tools import (
    git_fetch_tool as git_fetch,
)
from files.backend.mcp.filesys.tools.git_tools import (
    git_history_tool as git_history,
)
from files.backend.mcp.filesys.tools.git_tools import (
    git_merge_abort_tool as git_merge_abort,
)
from files.backend.mcp.filesys.tools.git_tools import (
    git_pull_tool as git_pull,
)
from files.backend.mcp.filesys.tools.git_tools import (
    git_push_tool as git_push,
)
from files.backend.mcp.filesys.tools.git_tools import (
    git_restore_tool as git_restore,
)
from files.backend.mcp.filesys.tools.git_tools import (
    git_stage_tool as git_stage,
)
from files.backend.mcp.filesys.tools.git_tools import (
    git_status_tool as git_status,
)
from files.backend.mcp.filesys.tools.git_tools import (
    git_unstage_tool as git_unstage,
)

_SANITIZED_GIT_ENV_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_NAMESPACE",
    "GIT_COMMON_DIR",
)


def _assert_git_call(mock_run: MagicMock, expected_cmd: list[str], cwd: Path) -> None:
    """Assert git subprocess invocation includes sanitized environment."""
    assert mock_run.call_args is not None
    args = mock_run.call_args.args
    command = args[0]
    kwargs = mock_run.call_args.kwargs
    assert command[0] == "git"
    assert command == expected_cmd
    assert kwargs["cwd"] == cwd
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["check"] is False
    env = kwargs.get("env")
    assert env is not None
    for var in _SANITIZED_GIT_ENV_VARS:
        assert var not in env


@pytest.fixture
def mock_root_dir(tmp_path: Path) -> Path:
    """Create a mock root directory with orchestrator structure."""
    # Create base and scripts directories to satisfy orchestrator root detection
    (tmp_path / "base").mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    # Create dummy git wrapper scripts that accept module_path argument
    # git_commit.sh expects: <module-path> <message> or <module-path> --amend [message]
    (scripts_dir / "git_commit.sh").write_text("#!/bin/bash\nshift  # Remove module_path argument\nexit 0\n")
    # git_push.sh expects: <module-path> [remote] [branch] [options]
    (scripts_dir / "git_push.sh").write_text("#!/bin/bash\nshift  # Remove module_path argument\nexit 0\n")
    (scripts_dir / "git_commit.sh").chmod(0o755)
    (scripts_dir / "git_push.sh").chmod(0o755)

    # Also need .git directory for orchestrator root detection
    (tmp_path / ".git").mkdir()

    return tmp_path


@pytest.fixture(autouse=True)
def mock_git_executable() -> Iterator[None]:
    """Mock shutil.which to return 'git' for all tests."""
    with patch("shutil.which", return_value="git"):
        yield


@pytest.fixture(autouse=True)
def mock_async_subprocess() -> Iterator[MagicMock]:
    """Mock asyncio.create_subprocess_exec for git wrapper scripts."""

    async def mock_communicate(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0) -> MagicMock:
        proc = MagicMock()
        proc.communicate = AsyncMock(return_value=(stdout, stderr))
        proc.returncode = returncode
        return proc

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        # Default: simulate successful execution
        mock_exec.return_value = AsyncMock()
        mock_exec.return_value.communicate = AsyncMock(return_value=(b"", b""))
        mock_exec.return_value.returncode = 0
        yield mock_exec


class TestGitStatus:
    """Test git_status handler."""

    @pytest.mark.asyncio
    async def test_git_status_basic(self, mock_root_dir: Path) -> None:
        """Test basic git status functionality."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="On branch main\nYour branch is up to date\n\nnothing to commit",
                stderr="",
            )

            result = await git_status(mock_root_dir)

            assert "success" in result
            assert result["success"] is True
            assert "output" in result
            assert "main" in result["output"]

    @pytest.mark.asyncio
    async def test_git_status_short_format(self, mock_root_dir: Path) -> None:
        """Test git status with short format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="## main...origin/main [ahead 1]\nM  file1.txt\n?? file2.txt",
                stderr="",
            )

            result = await git_status(mock_root_dir, short=True)

            assert "success" in result
            assert result["success"] is True
            assert "output" in result
            # The output is just raw text, not parsed
            assert "main" in result["output"]
            assert "file1.txt" in result["output"]
            assert "file2.txt" in result["output"]

    @pytest.mark.asyncio
    async def test_git_status_with_repo_path(self, mock_root_dir: Path) -> None:
        """Test git status with repo_path parameter."""
        # Create a subdirectory to act as repo
        repo_dir = mock_root_dir / "my_repo"
        repo_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="On branch main", stderr="")

            result = await git_status(mock_root_dir, repo_path="my_repo")

            assert "success" in result
            assert result["success"] is True
            # Verify subprocess was called with correct cwd
            mock_run.assert_called_once()
            assert mock_run.call_args[1]["cwd"] == repo_dir


class TestGitStage:
    """Test git_stage handler."""

    @pytest.mark.asyncio
    async def test_stage_files_success(self, mock_root_dir: Path) -> None:
        """Test successful file staging."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_stage(mock_root_dir, files=["file1.txt", "file2.txt"])

            assert "success" in result
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_stage_with_repo_path(self, mock_root_dir: Path) -> None:
        """Test staging with repo_path parameter."""
        # Create a subdirectory to act as repo
        repo_dir = mock_root_dir / "submodule"
        repo_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_stage(mock_root_dir, files=["file.txt"], repo_path="submodule")

            assert "success" in result
            assert result["success"] is True
            # First call should be to the correct directory
            assert mock_run.call_args[1]["cwd"] == repo_dir

    @pytest.mark.asyncio
    async def test_stage_with_force(self, mock_root_dir: Path) -> None:
        """Test staging with force option - note: force param doesn't exist in implementation."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            # The actual implementation doesn't have a force parameter
            result = await git_stage(mock_root_dir, files=[".gitignore"])

            assert "success" in result
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_stage_failure(self, mock_root_dir: Path) -> None:
        """Test failed staging."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="fatal: pathspec 'nonexistent' did not match any files",
            )

            result = await git_stage(mock_root_dir, files=["nonexistent"])

            assert "error" in result


class TestGitUnstage:
    """Test git_unstage handler."""

    @pytest.mark.asyncio
    async def test_unstage_files_success(self, mock_root_dir: Path) -> None:
        """Test successful file unstaging."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Unstaged changes after reset:\nM\tfile1.txt",
                stderr="",
            )

            result = await git_unstage(mock_root_dir, files=["file1.txt"])

            assert "success" in result
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_unstage_all(self, mock_root_dir: Path) -> None:
        """Test unstaging all files."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_unstage(mock_root_dir, files=None, unstage_all=True)

            assert "success" in result
            assert result["success"] is True


class TestGitCommit:
    """Test git_commit handler."""

    @pytest.mark.asyncio
    async def test_commit_success(self, mock_root_dir: Path) -> None:
        """Test successful commit."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="[main abc1234] Test commit\n 1 file changed, 1 insertion(+)",
                stderr="",
            )

            result = await git_commit(mock_root_dir, message="Test commit")

            assert "success" in result
            assert result["success"] is True
            assert "output" in result

    @pytest.mark.asyncio
    async def test_commit_nothing_to_commit(self, mock_root_dir: Path) -> None:
        """Test commit with nothing staged - wrapper returns success."""
        # git_commit.sh wrapper returns success even with nothing to commit
        result = await git_commit(mock_root_dir, message="Test commit")

        assert "success" in result
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_commit_with_amend(self, mock_root_dir: Path, mock_async_subprocess: AsyncMock) -> None:
        """Test amending a commit."""
        result = await git_commit(mock_root_dir, message="Amended commit", amend=True)

        assert "success" in result
        assert result["success"] is True
        # Check that --amend flag was passed to script
        mock_async_subprocess.assert_called_once()
        args = mock_async_subprocess.call_args[0]
        assert "--amend" in args


class TestGitDiff:
    """Test git_diff handler."""

    @pytest.mark.asyncio
    async def test_diff_working_changes(self, mock_root_dir: Path) -> None:
        """Test diff of working changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="diff --git a/file.txt b/file.txt\n+added line",
                stderr="",
            )

            result = await git_diff(mock_root_dir)

            assert "success" in result
            assert result["success"] is True
            assert "diff" in result
            assert "+added line" in result["diff"]

    @pytest.mark.asyncio
    async def test_diff_staged_changes(self, mock_root_dir: Path) -> None:
        """Test diff of staged changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="diff --git a/file.txt b/file.txt",
                stderr="",
            )

            result = await git_diff(mock_root_dir, staged=True)

            assert "success" in result
            assert result["success"] is True

            assert "diff" in result

            # Check that --staged flag was used
            _assert_git_call(
                mock_run,
                ["git", "diff", "--staged"],
                mock_root_dir,
            )

    @pytest.mark.asyncio
    async def test_diff_no_changes(self, mock_root_dir: Path) -> None:
        """Test diff with no changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_diff(mock_root_dir)

            assert "success" in result
            assert result["success"] is True
            assert result["diff"] == ""


class TestGitHistory:
    """Test git_history handler."""

    @pytest.mark.asyncio
    async def test_history_oneline(self, mock_root_dir: Path) -> None:
        """Test history in oneline format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="abc1234 Initial commit\ndef5678 Add feature",
                stderr="",
            )

            result = await git_history(mock_root_dir, limit=2, oneline=True)

            assert "success" in result
            assert result["success"] is True
            assert "history" in result
            assert "abc1234" in result["history"]
            assert "Initial commit" in result["history"]

    @pytest.mark.asyncio
    async def test_history_detailed(self, mock_root_dir: Path) -> None:
        """Test history with detailed format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="abc1234|John Doe|john@example.com|2024-01-01 10:00:00|Initial commit",
                stderr="",
            )

            result = await git_history(mock_root_dir, limit=1, oneline=False)

            assert "success" in result
            assert result["success"] is True
            assert "history" in result
            assert "abc1234" in result["history"]
            assert "John Doe" in result["history"]

    @pytest.mark.asyncio
    async def test_history_no_commits(self, mock_root_dir: Path) -> None:
        """Test history with no commits."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=128,
                stdout="",
                stderr="fatal: your current branch 'main' does not have any commits yet",
            )

            result = await git_history(mock_root_dir)

            assert "error" in result


class TestGitRestore:
    """Test git_restore handler."""

    @pytest.mark.asyncio
    async def test_restore_files(self, mock_root_dir: Path) -> None:
        """Test restoring files."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_restore(mock_root_dir, files=["file1.txt", "file2.txt"])

            assert "success" in result
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_restore_from_source(self, mock_root_dir: Path) -> None:
        """Test restoring from staged."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_restore(mock_root_dir, files=["file.txt"], staged=True)

            assert "success" in result
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_restore_reports_checkout_failure(self, mock_root_dir: Path) -> None:
        """Test restore failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="error: pathspec 'file.txt' did not match",
            )

            result = await git_restore(mock_root_dir, files=["file.txt"])

            assert "error" in result
            assert "pathspec" in result["error"]


class TestGitFetch:
    """Test git_fetch handler."""

    @pytest.mark.asyncio
    async def test_fetch_origin(self, mock_root_dir: Path) -> None:
        """Test fetching from origin."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="From github.com:user/repo\n   abc1234..def5678  main -> origin/main",
            )

            result = await git_fetch(mock_root_dir)

            assert "success" in result
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_fetch_all_remotes(self, mock_root_dir: Path) -> None:
        """Test fetching all remotes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_fetch(mock_root_dir, fetch_all=True)

            assert "success" in result
            assert result["success"] is True

            # Check that --all flag was used
            _assert_git_call(
                mock_run,
                ["git", "fetch", "--all"],
                mock_root_dir,
            )


class TestGitPull:
    """Test git_pull handler."""

    @pytest.mark.asyncio
    async def test_pull_success(self, mock_root_dir: Path) -> None:
        """Test successful pull."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Updating abc1234..def5678\nFast-forward\n file.txt | 2 +-\n 1 file changed, 1 insertion(+), 1 deletion(-)",
                stderr="",
            )

            result = await git_pull(mock_root_dir)

            assert "success" in result
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_pull_with_conflicts(self, mock_root_dir: Path) -> None:
        """Test pull with conflicts."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="CONFLICT (content): Merge conflict in file.txt",
                stderr="",
            )

            result = await git_pull(mock_root_dir)

            assert "error" in result

    @pytest.mark.asyncio
    async def test_pull_with_rebase(self, mock_root_dir: Path) -> None:
        """Test pull with rebase."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_pull(mock_root_dir, rebase=True)

            assert "success" in result
            assert result["success"] is True

            # Check that --rebase flag and origin was used
            _assert_git_call(
                mock_run,
                ["git", "pull", "--rebase", "origin"],
                mock_root_dir,
            )


class TestGitPush:
    """Test git_push handler."""

    @pytest.mark.asyncio
    async def test_push_success(self, mock_root_dir: Path) -> None:
        """Test successful push."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="To github.com:user/repo.git\n   abc1234..def5678  main -> main",
            )

            result = await git_push(mock_root_dir)

            assert "success" in result
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_push_up_to_date(self, mock_root_dir: Path) -> None:
        """Test push when already up to date."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="Everything up-to-date",
            )

            result = await git_push(mock_root_dir)

            assert "success" in result
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_push_with_force(self, mock_root_dir: Path, mock_async_subprocess: AsyncMock) -> None:
        """Test force push."""
        result = await git_push(mock_root_dir, force=True)

        assert "success" in result
        assert result["success"] is True
        # git_push.sh wrapper called via asyncio subprocess
        mock_async_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_dry_run(self, mock_root_dir: Path) -> None:
        """Test push dry run - note: dry_run param doesn't exist in implementation."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            # The actual implementation doesn't have a dry_run parameter
            result = await git_push(mock_root_dir)

            assert "success" in result
            assert result["success"] is True


class TestGitMergeAbort:
    """Test git_merge_abort handler."""

    @pytest.mark.asyncio
    async def test_merge_abort_success(self, mock_root_dir: Path) -> None:
        """Test successful merge abort."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_merge_abort(mock_root_dir)

            assert "success" in result
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_merge_abort_no_merge(self, mock_root_dir: Path) -> None:
        """Test abort when no merge in progress."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=128,
                stdout="",
                stderr="fatal: There is no merge to abort",
            )

            result = await git_merge_abort(mock_root_dir)

            assert "error" in result
