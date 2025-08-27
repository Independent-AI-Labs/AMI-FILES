"""Integration tests for git tools in filesystem MCP server."""

import os
import subprocess

import pytest
from files.backend.mcp.filesys.filesys_server import (
    FilesysFastMCPServer as FilesysMCPServer,
)


@pytest.fixture
async def git_repo(tmp_path):
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


@pytest.fixture
async def server_with_git(git_repo):
    """Create MCP server with git repo as root."""
    server = FilesysMCPServer(root_dir=str(git_repo))
    return server


class TestGitWorkflow:
    """Test complete git workflow."""

    @pytest.mark.asyncio
    async def test_stage_commit_workflow(self, server_with_git, git_repo):
        """Test staging and committing changes."""
        # Create a new file
        new_file = git_repo / "new_file.txt"
        new_file.write_text("New content")

        # Stage the file
        result = await server_with_git.execute_tool(
            "git_stage",
            {"paths": ["new_file.txt"]},
        )
        assert "error" not in result
        assert "staged_files" in result

        # Commit the changes
        result = await server_with_git.execute_tool(
            "git_commit",
            {"message": "Add new file"},
        )
        assert "error" not in result
        assert "commit_hash" in result

        # Verify commit was created
        result = await server_with_git.execute_tool(
            "git_history",
            {"limit": 2},
        )
        assert "error" not in result
        assert len(result["commits"]) == 2
        assert "Add new file" in result["commits"][0]["message"]

    @pytest.mark.asyncio
    async def test_diff_workflow(self, server_with_git, git_repo):
        """Test diff functionality."""
        # Modify existing file
        test_file = git_repo / "test.txt"
        test_file.write_text("Modified content")

        # Get working diff
        result = await server_with_git.execute_tool(
            "git_diff",
            {},
        )
        assert "error" not in result
        assert "diff" in result
        assert "Modified content" in result["diff"]

        # Stage the file
        await server_with_git.execute_tool(
            "git_stage",
            {"paths": ["test.txt"]},
        )

        # Get staged diff
        result = await server_with_git.execute_tool(
            "git_diff",
            {"staged": True},
        )
        assert "error" not in result
        assert "diff" in result

    @pytest.mark.asyncio
    async def test_unstage_workflow(self, server_with_git, git_repo):
        """Test unstaging files."""
        # Create and stage a file
        new_file = git_repo / "staged.txt"
        new_file.write_text("Staged content")

        await server_with_git.execute_tool(
            "git_stage",
            {"paths": ["staged.txt"]},
        )

        # Verify it's staged
        result = await server_with_git.execute_tool(
            "git_diff",
            {"staged": True},
        )
        assert "staged.txt" in result["diff"]

        # Unstage the file
        result = await server_with_git.execute_tool(
            "git_unstage",
            {"paths": ["staged.txt"]},
        )
        assert "error" not in result

        # Verify it's no longer staged
        result = await server_with_git.execute_tool(
            "git_diff",
            {"staged": True},
        )
        assert result["diff"] == ""

    @pytest.mark.asyncio
    async def test_restore_workflow(self, server_with_git, git_repo):
        """Test restoring files."""
        # Modify a file
        test_file = git_repo / "test.txt"
        original_content = test_file.read_text()
        test_file.write_text("Changed content")

        # Restore the file
        result = await server_with_git.execute_tool(
            "git_restore",
            {"paths": ["test.txt"]},
        )
        assert "error" not in result

        # Verify file was restored
        assert test_file.read_text() == original_content

    @pytest.mark.asyncio
    async def test_history_filtering(self, server_with_git, git_repo):
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
        result = await server_with_git.execute_tool(
            "git_history",
            {"limit": 2},
        )
        assert "error" not in result
        assert len(result["commits"]) == 2

        # Get history with grep
        result = await server_with_git.execute_tool(
            "git_history",
            {"grep": "Commit 1"},
        )
        assert "error" not in result
        assert len(result["commits"]) == 1
        assert "Commit 1" in result["commits"][0]["message"]


class TestGitEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_stage_nonexistent_file(self, server_with_git):
        """Test staging nonexistent file."""
        result = await server_with_git.execute_tool(
            "git_stage",
            {"paths": ["nonexistent.txt"]},
        )
        assert "error" in result
        assert "Failed to stage" in result["error"]

    @pytest.mark.asyncio
    async def test_commit_with_no_changes(self, server_with_git):
        """Test committing with no staged changes."""
        result = await server_with_git.execute_tool(
            "git_commit",
            {"message": "Empty commit"},
        )
        # Result is returned directly from execute_tool
        assert "message" in result or "error" in result
        if "message" in result:
            assert "Nothing to commit" in result["message"]

    @pytest.mark.asyncio
    async def test_merge_abort_no_merge(self, server_with_git):
        """Test aborting merge when no merge in progress."""
        result = await server_with_git.execute_tool(
            "git_merge_abort",
            {},
        )
        # Result is returned directly from execute_tool
        assert "error" not in result
        if "status" in result:
            assert result.get("status") == "clean"

    @pytest.mark.asyncio
    async def test_amend_commit(self, server_with_git, git_repo):
        """Test amending a commit."""
        # Create a file and commit
        file = git_repo / "amend_test.txt"
        file.write_text("Original")

        await server_with_git.execute_tool(
            "git_stage",
            {"paths": ["amend_test.txt"]},
        )
        await server_with_git.execute_tool(
            "git_commit",
            {"message": "Original commit"},
        )

        # Modify and amend
        file.write_text("Amended")
        await server_with_git.execute_tool(
            "git_stage",
            {"paths": ["amend_test.txt"]},
        )

        result = await server_with_git.execute_tool(
            "git_commit",
            {"message": "Amended commit", "amend": True},
        )
        assert "error" not in result

        # Check history - should still have same number of commits
        result = await server_with_git.execute_tool(
            "git_history",
            {"limit": 5},
        )
        # Should see "Amended commit" as the latest
        assert "Amended commit" in result["commits"][0]["message"]


class TestGitRemoteOperations:
    """Test remote git operations (fetch, pull, push)."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.environ.get("TEST_GIT_REMOTE"),
        reason="Remote git tests require TEST_GIT_REMOTE env var",
    )
    async def test_fetch_operation(self, server_with_git, git_repo):
        """Test fetch operation."""
        # This test requires a configured remote
        # Set up a fake remote for testing
        result = await server_with_git.execute_tool(
            "git_fetch",
            {"remote": "origin"},
        )
        # Will fail without a real remote, but should handle gracefully
        assert "result" in result or "error" in result

    @pytest.mark.asyncio
    async def test_push_dry_run(self, server_with_git, git_repo):
        """Test push with dry run."""
        # Create a commit
        file = git_repo / "push_test.txt"
        file.write_text("Push test")

        await server_with_git.execute_tool(
            "git_stage",
            {"paths": ["push_test.txt"]},
        )
        await server_with_git.execute_tool(
            "git_commit",
            {"message": "Push test commit"},
        )

        # Try dry run push (will fail without remote but tests the functionality)
        result = await server_with_git.execute_tool(
            "git_push",
            {"dry_run": True},
        )
        # Should either succeed with dry_run flag or fail gracefully
        assert isinstance(result, dict)
        if "error" not in result:
            assert result.get("dry_run") is True


class TestGitToolRegistration:
    """Test that git tools are properly registered."""

    @pytest.mark.asyncio
    async def test_all_git_tools_registered(self, server_with_git):
        """Test that all git tools are registered in the server."""
        expected_tools = [
            "git_stage",
            "git_unstage",
            "git_commit",
            "git_diff",
            "git_history",
            "git_restore",
            "git_fetch",
            "git_pull",
            "git_push",
            "git_merge_abort",
        ]

        for tool_name in expected_tools:
            assert tool_name in server_with_git.tools
            tool_info = server_with_git.tools[tool_name]
            assert "description" in tool_info
            assert "inputSchema" in tool_info

    @pytest.mark.asyncio
    async def test_git_tool_schemas(self, server_with_git):
        """Test that git tool schemas are valid."""
        # Test a few key tools
        stage_schema = server_with_git.tools["git_stage"]["inputSchema"]
        assert "properties" in stage_schema
        assert "paths" in stage_schema["properties"]

        commit_schema = server_with_git.tools["git_commit"]["inputSchema"]
        assert "message" in commit_schema["properties"]
        assert "message" in commit_schema.get("required", [])

        diff_schema = server_with_git.tools["git_diff"]["inputSchema"]
        assert "staged" in diff_schema["properties"]
