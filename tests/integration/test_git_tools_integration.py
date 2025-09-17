"""Simple integration tests for git tools without subprocess complexity."""

import os
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

_SANITIZED_GIT_ENV_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_NAMESPACE",
    "GIT_COMMON_DIR",
)
_MODULE_ROOT = Path(__file__).resolve().parents[2]


def _assert_isolated_repo(cwd: Path) -> None:
    """Make sure we never run git tests inside the real module tree."""
    repo_root = cwd.resolve()
    if repo_root == _MODULE_ROOT or _MODULE_ROOT in repo_root.parents:
        raise RuntimeError(f"Refusing to run git tests inside module tree: {repo_root}")


def _git_env(cwd: Path) -> dict[str, str]:
    """Return a git environment that keeps config local to the temp repo."""
    env = dict(os.environ)
    for var in _SANITIZED_GIT_ENV_VARS:
        env.pop(var, None)

    # Provide a fake HOME so git never touches the developer's config.
    fake_home = cwd / ".git-test-home"
    fake_home.mkdir(parents=True, exist_ok=True)

    env["HOME"] = str(fake_home)
    env["GIT_CONFIG_GLOBAL"] = str(fake_home / "gitconfig")
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def _run_git(args: list[str], cwd: Path) -> None:
    """Run a git subprocess with sanitized environment."""
    _assert_isolated_repo(cwd)
    subprocess.run(["git", *args], cwd=cwd, env=_git_env(cwd), check=True)


@pytest.fixture
def git_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a temporary git repository."""
    repo_root = tmp_path_factory.mktemp("files_git_repo")
    _run_git(["init"], repo_root)
    _run_git(["config", "--local", "user.email", "test@example.com"], repo_root)
    _run_git(["config", "--local", "user.name", "Test User"], repo_root)

    test_file = repo_root / "test.txt"
    test_file.write_text("Initial content")

    _run_git(["add", "."], repo_root)
    _run_git(["commit", "-m", "Initial commit"], repo_root)

    return repo_root


class TestGitWorkflowDirect:
    """Test git workflow by calling tools directly."""

    @pytest.mark.asyncio
    async def test_stage_commit_workflow(self, git_repo: Path) -> None:
        """Test staging and committing changes."""
        new_file = git_repo / "new_file.txt"
        new_file.write_text("New content")

        result = await git_stage_tool(
            root_dir=git_repo,
            files=["new_file.txt"],
        )
        assert "error" not in result
        assert result.get("success") is True

        result = await git_commit_tool(
            root_dir=git_repo,
            message="Add new file",
        )
        assert "error" not in result
        assert result.get("success") is True

        result = await git_history_tool(
            root_dir=git_repo,
            limit=2,
        )
        assert "error" not in result
        assert "history" in result

    @pytest.mark.asyncio
    async def test_diff_workflow(self, git_repo: Path) -> None:
        """Test diff functionality."""
        test_file = git_repo / "test.txt"
        test_file.write_text("Modified content")

        result = await git_diff_tool(root_dir=git_repo)
        assert "error" not in result
        assert "diff" in result
        assert "Modified content" in result["diff"]

        result = await git_stage_tool(
            root_dir=git_repo,
            files=["test.txt"],
        )
        assert "error" not in result

        result = await git_diff_tool(root_dir=git_repo, staged=True)
        assert "error" not in result
        assert "diff" in result

    @pytest.mark.asyncio
    async def test_unstage_workflow(self, git_repo: Path) -> None:
        """Test unstaging files."""
        new_file = git_repo / "staged.txt"
        new_file.write_text("Staged content")

        result = await git_stage_tool(
            root_dir=git_repo,
            files=["staged.txt"],
        )
        assert "error" not in result

        result = await git_diff_tool(root_dir=git_repo, staged=True)
        assert "staged.txt" in result["diff"]

        result = await git_unstage_tool(
            root_dir=git_repo,
            files=["staged.txt"],
        )
        assert "error" not in result

        result = await git_diff_tool(root_dir=git_repo, staged=True)
        assert result["diff"] == ""

    @pytest.mark.asyncio
    async def test_restore_workflow(self, git_repo: Path) -> None:
        """Test restoring files."""
        test_file = git_repo / "test.txt"
        original_content = test_file.read_text()
        test_file.write_text("Changed content")

        result = await git_restore_tool(
            root_dir=git_repo,
            files=["test.txt"],
        )
        assert "error" not in result
        assert test_file.read_text() == original_content

    @pytest.mark.asyncio
    async def test_history_filtering(self, git_repo: Path) -> None:
        """Test history with filters."""
        for i in range(3):
            file = git_repo / f"file{i}.txt"
            file.write_text(f"Content {i}")
            _run_git(["add", "."], git_repo)
            _run_git(["commit", "-m", f"Commit {i}"], git_repo)

        result = await git_history_tool(root_dir=git_repo, limit=2)
        assert "error" not in result
        assert "history" in result

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
        file = git_repo / "amend_test.txt"
        file.write_text("Original")

        await git_stage_tool(root_dir=git_repo, files=["amend_test.txt"])
        await git_commit_tool(root_dir=git_repo, message="Original commit")

        file.write_text("Amended")
        await git_stage_tool(root_dir=git_repo, files=["amend_test.txt"])

        result = await git_commit_tool(
            root_dir=git_repo,
            message="Amended commit",
            amend=True,
        )
        assert "error" not in result

        result = await git_history_tool(root_dir=git_repo, limit=5)
        assert "history" in result
        assert "Amended commit" in result["history"]
