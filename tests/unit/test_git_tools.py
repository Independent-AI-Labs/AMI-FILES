"""Unit tests for git tools in filesystem MCP server."""

from unittest.mock import MagicMock, patch

import pytest
from files.backend.mcp.filesys.tools.git_handlers import (
    git_commit,
    git_diff,
    git_fetch,
    git_history,
    git_merge_abort,
    git_pull,
    git_push,
    git_restore,
    git_stage,
    git_status,
    git_unstage,
)


@pytest.fixture
def mock_root_dir(tmp_path):
    """Create a mock root directory."""
    return tmp_path


class TestGitStatus:
    """Test git_status handler."""

    @pytest.mark.asyncio
    async def test_git_status_basic(self, mock_root_dir):
        """Test basic git status functionality."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="On branch main\nYour branch is up to date\n\nnothing to commit",
                stderr="",
            )

            result = await git_status(mock_root_dir)

            assert "result" in result
            assert "output" in result["result"]
            assert "main" in result["result"]["output"]

    @pytest.mark.asyncio
    async def test_git_status_short_format(self, mock_root_dir):
        """Test git status with short format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="## main...origin/main [ahead 1]\nM  file1.txt\n?? file2.txt",
                stderr="",
            )

            result = await git_status(mock_root_dir, short=True)

            assert "result" in result
            assert "status" in result["result"]
            status = result["result"]["status"]
            assert status["branch"] == "main"
            assert status["ahead"] == 1
            assert "file1.txt" in status["modified"]
            assert "file2.txt" in status["untracked"]

    @pytest.mark.asyncio
    async def test_git_status_with_repo_path(self, mock_root_dir):
        """Test git status with repo_path parameter."""
        # Create a subdirectory to act as repo
        repo_dir = mock_root_dir / "my_repo"
        repo_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="On branch main", stderr=""
            )

            result = await git_status(mock_root_dir, repo_path="my_repo")

            assert "result" in result
            assert result["result"]["repo_path"] == "my_repo"
            # Verify subprocess was called with correct cwd
            mock_run.assert_called_once()
            assert mock_run.call_args[1]["cwd"] == repo_dir


class TestGitStage:
    """Test git_stage handler."""

    @pytest.mark.asyncio
    async def test_stage_files_success(self, mock_root_dir):
        """Test successful file staging."""
        with patch("subprocess.run") as mock_run:
            # Mock successful git add
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),
                MagicMock(returncode=0, stdout="A  file1.txt\nM  file2.txt", stderr=""),
            ]

            result = await git_stage(mock_root_dir, ["file1.txt", "file2.txt"])

            assert "result" in result
            assert result["result"]["staged_files"] == ["file1.txt", "file2.txt"]
            assert "Successfully staged 2 file(s)" in result["result"]["message"]

    @pytest.mark.asyncio
    async def test_stage_with_repo_path(self, mock_root_dir):
        """Test staging with repo_path parameter."""
        # Create a subdirectory to act as repo
        repo_dir = mock_root_dir / "submodule"
        repo_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),
                MagicMock(returncode=0, stdout="A  file.txt", stderr=""),
            ]

            result = await git_stage(mock_root_dir, ["file.txt"], repo_path="submodule")

            assert "result" in result
            assert result["result"]["repo_path"] == "submodule"
            # First call should be to the correct directory
            assert mock_run.call_args_list[0][1]["cwd"] == repo_dir

    @pytest.mark.asyncio
    async def test_stage_with_force(self, mock_root_dir):
        """Test staging with force option."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),
                MagicMock(returncode=0, stdout="", stderr=""),
            ]

            await git_stage(mock_root_dir, [".gitignore"], force=True)

            # Check that -f flag was used
            mock_run.assert_any_call(
                ["git", "add", "-f", ".gitignore"],
                cwd=mock_root_dir,
                capture_output=True,
                text=True,
                check=False,
            )

    @pytest.mark.asyncio
    async def test_stage_failure(self, mock_root_dir):
        """Test failed staging."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="fatal: pathspec 'nonexistent' did not match any files",
            )

            result = await git_stage(mock_root_dir, ["nonexistent"])

            assert "error" in result
            assert "Failed to stage files" in result["error"]


class TestGitUnstage:
    """Test git_unstage handler."""

    @pytest.mark.asyncio
    async def test_unstage_files_success(self, mock_root_dir):
        """Test successful file unstaging."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Unstaged changes after reset:\nM\tfile1.txt",
                stderr="",
            )

            result = await git_unstage(mock_root_dir, ["file1.txt"])

            assert "result" in result
            assert "Successfully unstaged files" in result["result"]["message"]

    @pytest.mark.asyncio
    async def test_unstage_all(self, mock_root_dir):
        """Test unstaging all files."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_unstage(mock_root_dir, [])

            assert "result" in result
            assert result["result"]["paths"] == ["all"]


class TestGitCommit:
    """Test git_commit handler."""

    @pytest.mark.asyncio
    async def test_commit_success(self, mock_root_dir):
        """Test successful commit."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="[main abc1234] Test commit\n 1 file changed, 1 insertion(+)",
                stderr="",
            )

            result = await git_commit(mock_root_dir, "Test commit")

            assert "result" in result
            assert result["result"]["commit_hash"] == "abc1234"
            assert "Successfully created commit" in result["result"]["message"]

    @pytest.mark.asyncio
    async def test_commit_nothing_to_commit(self, mock_root_dir):
        """Test commit with nothing staged."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="On branch main\nnothing to commit, working tree clean",
                stderr="",
            )

            result = await git_commit(mock_root_dir, "Test commit")

            assert "result" in result
            assert "Nothing to commit" in result["result"]["message"]

    @pytest.mark.asyncio
    async def test_commit_with_amend(self, mock_root_dir):
        """Test amending a commit."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="[main def5678] Amended commit",
                stderr="",
            )

            await git_commit(mock_root_dir, "Amended commit", amend=True)

            # Check that --amend flag was used
            mock_run.assert_called_with(
                ["git", "commit", "-m", "Amended commit", "--amend"],
                cwd=mock_root_dir,
                capture_output=True,
                text=True,
                check=False,
            )


class TestGitDiff:
    """Test git_diff handler."""

    @pytest.mark.asyncio
    async def test_diff_working_changes(self, mock_root_dir):
        """Test diff of working changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="diff --git a/file.txt b/file.txt\n+added line",
                stderr="",
            )

            result = await git_diff(mock_root_dir)

            assert "result" in result
            assert "+added line" in result["result"]["diff"]
            assert result["result"]["type"] == "working"

    @pytest.mark.asyncio
    async def test_diff_staged_changes(self, mock_root_dir):
        """Test diff of staged changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="diff --git a/file.txt b/file.txt",
                stderr="",
            )

            result = await git_diff(mock_root_dir, staged=True)

            assert "result" in result
            assert result["result"]["type"] == "staged"

            # Check that --cached flag was used
            mock_run.assert_called_with(
                ["git", "diff", "--cached"],
                cwd=mock_root_dir,
                capture_output=True,
                text=True,
                check=False,
            )

    @pytest.mark.asyncio
    async def test_diff_no_changes(self, mock_root_dir):
        """Test diff with no changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_diff(mock_root_dir)

            assert "result" in result
            assert "No differences found" in result["result"]["message"]


class TestGitHistory:
    """Test git_history handler."""

    @pytest.mark.asyncio
    async def test_history_oneline(self, mock_root_dir):
        """Test history in oneline format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="abc1234 Initial commit\ndef5678 Add feature",
                stderr="",
            )

            result = await git_history(mock_root_dir, limit=2, oneline=True)

            assert "result" in result
            assert len(result["result"]["commits"]) == 2
            assert result["result"]["commits"][0]["hash"] == "abc1234"
            assert result["result"]["commits"][0]["message"] == "Initial commit"

    @pytest.mark.asyncio
    async def test_history_detailed(self, mock_root_dir):
        """Test history with detailed format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="abc1234|John Doe|john@example.com|2024-01-01 10:00:00|Initial commit",
                stderr="",
            )

            result = await git_history(mock_root_dir, limit=1, oneline=False)

            assert "result" in result
            assert len(result["result"]["commits"]) == 1
            commit = result["result"]["commits"][0]
            assert commit["hash"] == "abc1234"
            assert commit["author"] == "John Doe"
            assert commit["email"] == "john@example.com"

    @pytest.mark.asyncio
    async def test_history_no_commits(self, mock_root_dir):
        """Test history with no commits."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=128,
                stdout="",
                stderr="fatal: your current branch 'main' does not have any commits yet",
            )

            result = await git_history(mock_root_dir)

            assert "result" in result
            assert "No commits found" in result["result"]["message"]


class TestGitRestore:
    """Test git_restore handler."""

    @pytest.mark.asyncio
    async def test_restore_files(self, mock_root_dir):
        """Test restoring files."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_restore(mock_root_dir, ["file1.txt", "file2.txt"])

            assert "result" in result
            assert "Successfully restored 2 file(s)" in result["result"]["message"]

    @pytest.mark.asyncio
    async def test_restore_from_source(self, mock_root_dir):
        """Test restoring from specific source."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_restore(mock_root_dir, ["file.txt"], source="HEAD~1")

            assert "result" in result
            assert result["result"]["source"] == "HEAD~1"

    @pytest.mark.asyncio
    async def test_restore_fallback_to_checkout(self, mock_root_dir):
        """Test fallback to checkout for older git."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(
                    returncode=1,
                    stdout="",
                    stderr="git: 'restore' is not a git command",
                ),
                MagicMock(returncode=0, stdout="", stderr=""),
            ]

            result = await git_restore(mock_root_dir, ["file.txt"])

            assert "result" in result
            # Second call should be git checkout
            assert mock_run.call_count == 2


class TestGitFetch:
    """Test git_fetch handler."""

    @pytest.mark.asyncio
    async def test_fetch_origin(self, mock_root_dir):
        """Test fetching from origin."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="From github.com:user/repo\n   abc1234..def5678  main -> origin/main",
            )

            result = await git_fetch(mock_root_dir)

            assert "result" in result
            assert result["result"]["remote"] == "origin"
            assert len(result["result"]["updates"]) == 1

    @pytest.mark.asyncio
    async def test_fetch_all_remotes(self, mock_root_dir):
        """Test fetching all remotes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_fetch(mock_root_dir, all=True)

            assert "result" in result
            assert result["result"]["remote"] == "all"

            # Check that --all flag was used
            mock_run.assert_called_with(
                ["git", "fetch", "--all", "--tags"],
                cwd=mock_root_dir,
                capture_output=True,
                text=True,
                check=False,
            )


class TestGitPull:
    """Test git_pull handler."""

    @pytest.mark.asyncio
    async def test_pull_success(self, mock_root_dir):
        """Test successful pull."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Updating abc1234..def5678\nFast-forward\n file.txt | 2 +-\n 1 file changed, 1 insertion(+), 1 deletion(-)",
                stderr="",
            )

            result = await git_pull(mock_root_dir)

            assert "result" in result
            assert result["result"]["files_changed"] == 1
            assert result["result"]["insertions"] == 1
            assert result["result"]["deletions"] == 1

    @pytest.mark.asyncio
    async def test_pull_with_conflicts(self, mock_root_dir):
        """Test pull with conflicts."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="CONFLICT (content): Merge conflict in file.txt",
                stderr="",
            )

            result = await git_pull(mock_root_dir)

            assert "error" in result
            assert "conflicts" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_pull_with_rebase(self, mock_root_dir):
        """Test pull with rebase."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            await git_pull(mock_root_dir, rebase=True)

            # Check that --rebase flag was used
            mock_run.assert_called_with(
                ["git", "pull", "--rebase", "origin"],
                cwd=mock_root_dir,
                capture_output=True,
                text=True,
                check=False,
            )


class TestGitPush:
    """Test git_push handler."""

    @pytest.mark.asyncio
    async def test_push_success(self, mock_root_dir):
        """Test successful push."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="To github.com:user/repo.git\n   abc1234..def5678  main -> main",
            )

            result = await git_push(mock_root_dir)

            assert "result" in result
            assert "Push completed successfully" in result["result"]["message"]
            assert len(result["result"]["pushed_refs"]) == 1

    @pytest.mark.asyncio
    async def test_push_up_to_date(self, mock_root_dir):
        """Test push when already up to date."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="Everything up-to-date",
            )

            result = await git_push(mock_root_dir)

            assert "result" in result
            assert result["result"]["status"] == "up-to-date"

    @pytest.mark.asyncio
    async def test_push_with_force(self, mock_root_dir):
        """Test force push."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            await git_push(mock_root_dir, force=True)

            # Check that --force flag was used
            mock_run.assert_called_with(
                ["git", "push", "--force", "origin"],
                cwd=mock_root_dir,
                capture_output=True,
                text=True,
                check=False,
            )

    @pytest.mark.asyncio
    async def test_push_dry_run(self, mock_root_dir):
        """Test push dry run."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_push(mock_root_dir, dry_run=True)

            assert "result" in result
            assert result["result"]["dry_run"] is True


class TestGitMergeAbort:
    """Test git_merge_abort handler."""

    @pytest.mark.asyncio
    async def test_merge_abort_success(self, mock_root_dir):
        """Test successful merge abort."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = await git_merge_abort(mock_root_dir)

            assert "result" in result
            assert "Successfully aborted merge" in result["result"]["message"]
            assert result["result"]["status"] == "aborted"

    @pytest.mark.asyncio
    async def test_merge_abort_no_merge(self, mock_root_dir):
        """Test abort when no merge in progress."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=128,
                stdout="",
                stderr="fatal: There is no merge to abort",
            )

            result = await git_merge_abort(mock_root_dir)

            assert "result" in result
            assert "No merge in progress" in result["result"]["message"]
            assert result["result"]["status"] == "clean"
