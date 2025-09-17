"""Simple integration tests for git tools without subprocess complexity."""

import subprocess
from pathlib import Path

import pytest
from files.backend.mcp.filesys.tools.git_tools import (
    git_commit_tool,
    git_diff_tool,
    git_history_tool,
    git_restore_tool,
    git_stage_tool,
    git_unstage_tool,
)


@pytest.fixture
async def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository."""
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
    )

    # Create initial file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Initial content")

    # Make initial commit
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
    )

    return tmp_path


class TestGitWorkflowDirect:
    """Test git workflow by calling tools directly."""

    @pytest.mark.asyncio
    async def test_stage_commit_workflow(self, git_repo: Path) -> None:
        """Test staging and committing changes."""
        # Create a new file
        new_file = git_repo / "new_file.txt"
        new_file.write_text("New content")

        # Stage the file
        result = await git_stage_tool(
            root_dir=git_repo,
            files=["new_file.txt"],
        )
        assert "error" not in result
        assert result.get("success") is True

        # Commit the changes
        result = await git_commit_tool(
            root_dir=git_repo,
            message="Add new file",
        )
        assert "error" not in result
        assert result.get("success") is True

        # Verify commit was created
        result = await git_history_tool(
            root_dir=git_repo,
            limit=2,
        )
        assert "error" not in result
        assert "history" in result
        # Check that history contains the expected commits

    @pytest.mark.asyncio
    async def test_diff_workflow(self, git_repo: Path) -> None:
        """Test diff functionality."""
        # Modify existing file
        test_file = git_repo / "test.txt"
        test_file.write_text("Modified content")

        # Get working diff
        result = await git_diff_tool(root_dir=git_repo)
        assert "error" not in result
        assert "diff" in result
        assert "Modified content" in result["diff"]

        # Stage the file
        result = await git_stage_tool(
            root_dir=git_repo,
            files=["test.txt"],
        )
        assert "error" not in result

        # Get staged diff
        result = await git_diff_tool(root_dir=git_repo, staged=True)
        assert "error" not in result
        assert "diff" in result

    @pytest.mark.asyncio
    async def test_unstage_workflow(self, git_repo: Path) -> None:
        """Test unstaging files."""
        # Create and stage a file
        new_file = git_repo / "staged.txt"
        new_file.write_text("Staged content")

        result = await git_stage_tool(
            root_dir=git_repo,
            files=["staged.txt"],
        )
        assert "error" not in result

        # Verify it's staged
        result = await git_diff_tool(root_dir=git_repo, staged=True)
        assert "staged.txt" in result["diff"]

        # Unstage the file
        result = await git_unstage_tool(
            root_dir=git_repo,
            files=["staged.txt"],
        )
        assert "error" not in result

        # Verify it's no longer staged
        result = await git_diff_tool(root_dir=git_repo, staged=True)
        assert result["diff"] == ""

    @pytest.mark.asyncio
    async def test_restore_workflow(self, git_repo: Path) -> None:
        """Test restoring files."""
        # Modify a file
        test_file = git_repo / "test.txt"
        original_content = test_file.read_text()
        test_file.write_text("Changed content")

        # Restore the file
        result = await git_restore_tool(
            root_dir=git_repo,
            files=["test.txt"],
        )
        assert "error" not in result

        # Verify file was restored
        assert test_file.read_text() == original_content

    @pytest.mark.asyncio
    async def test_history_filtering(self, git_repo: Path) -> None:
        """Test history with filters."""
        # Create multiple commits
        for i in range(3):
            file = git_repo / f"file{i}.txt"
            file.write_text(f"Content {i}")
            subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Commit {i}"],
                cwd=git_repo,
                check=True,
            )

        # Get limited history
        result = await git_history_tool(root_dir=git_repo, limit=2)
        assert "error" not in result
        assert "history" in result

        # Get history with grep
        result = await git_history_tool(root_dir=git_repo, grep="Commit 1")
        assert "error" not in result
        assert "history" in result
        assert "Commit 1" in result["history"]


class TestGitEdgeCasesDirect:
    """Test edge cases by calling tools directly."""

    @pytest.mark.asyncio
    async def test_stage_nonexistent_file(self, git_repo: Path) -> None:
        """Test staging nonexistent file."""
        result = await git_stage_tool(
            root_dir=git_repo,
            files=["nonexistent.txt"],
        )
        assert "error" in result
        # Git will return an error about pathspec not matching any files
        assert "pathspec" in result["error"] or "did not match" in result["error"]

    @pytest.mark.asyncio
    async def test_commit_with_no_changes(self, git_repo: Path) -> None:
        """Test committing with no staged changes."""
        result = await git_commit_tool(
            root_dir=git_repo,
            message="Empty commit",
        )
        assert "message" in result or "error" in result
        if "message" in result:
            assert "Nothing to commit" in result["message"]

    @pytest.mark.asyncio
    async def test_amend_commit(self, git_repo: Path) -> None:
        """Test amending a commit."""
        # Create a file and commit
        file = git_repo / "amend_test.txt"
        file.write_text("Original")

        await git_stage_tool(root_dir=git_repo, files=["amend_test.txt"])
        await git_commit_tool(root_dir=git_repo, message="Original commit")

        # Modify and amend
        file.write_text("Amended")
        await git_stage_tool(root_dir=git_repo, files=["amend_test.txt"])

        result = await git_commit_tool(
            root_dir=git_repo,
            message="Amended commit",
            amend=True,
        )
        assert "error" not in result

        # Check history
        result = await git_history_tool(root_dir=git_repo, limit=5)
        assert "history" in result
        assert "Amended commit" in result["history"]
