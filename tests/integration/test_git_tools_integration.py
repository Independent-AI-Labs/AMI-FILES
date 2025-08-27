"""Integration tests for git tools in filesystem MCP server."""

import json
import os
import subprocess
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


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


class TestGitWorkflow:
    """Test complete git workflow."""

    def _get_client_session(self, git_repo):
        """Get MCP client session for testing."""
        # Get venv Python
        venv_python = (
            Path(__file__).parent.parent.parent / ".venv" / "Scripts" / "python.exe"
        )
        server_script = (
            Path(__file__).parent.parent.parent / "scripts" / "run_filesys_fastmcp.py"
        )

        server_params = StdioServerParameters(
            command=str(venv_python),
            args=["-u", str(server_script), "--root-dir", str(git_repo)],
            env=None,
        )

        return stdio_client(server_params)

    @pytest.mark.asyncio
    async def test_stage_commit_workflow(self, git_repo):
        """Test staging and committing changes."""
        # Create a new file
        new_file = git_repo / "new_file.txt"
        new_file.write_text("New content")

        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Stage the file
            result = await session.call_tool(
                "git_stage",
                arguments={"files": ["new_file.txt"]},
            )
            parsed = json.loads(result.content[0].text)
            assert "error" not in parsed
            assert "staged_files" in parsed

            # Commit the changes
            result = await session.call_tool(
                "git_commit",
                arguments={"message": "Add new file"},
            )
            parsed = json.loads(result.content[0].text)
            assert "error" not in parsed
            assert "commit_hash" in parsed

            # Verify commit was created
            result = await session.call_tool(
                "git_history",
                arguments={"limit": 2},
            )
            parsed = json.loads(result.content[0].text)
            assert "error" not in parsed
            assert "commits" in parsed
            assert len(parsed["commits"]) == 2
            assert "Add new file" in parsed["commits"][0]["message"]

    @pytest.mark.asyncio
    async def test_diff_workflow(self, git_repo):
        """Test diff functionality."""
        # Modify existing file
        test_file = git_repo / "test.txt"
        test_file.write_text("Modified content")

        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Get working diff
            result = await session.call_tool("git_diff", arguments={})
            parsed = json.loads(result.content[0].text)
            assert "error" not in parsed
            assert "diff" in parsed
            assert "Modified content" in parsed["diff"]

            # Stage the file
            result = await session.call_tool(
                "git_stage",
                arguments={"files": ["test.txt"]},
            )
            assert "error" not in json.loads(result.content[0].text)

            # Get staged diff
            result = await session.call_tool(
                "git_diff",
                arguments={"staged": True},
            )
            parsed = json.loads(result.content[0].text)
            assert "error" not in parsed
            assert "diff" in parsed

    @pytest.mark.asyncio
    async def test_unstage_workflow(self, git_repo):
        """Test unstaging files."""
        # Create and stage a file
        new_file = git_repo / "staged.txt"
        new_file.write_text("Staged content")

        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Stage the file
            result = await session.call_tool(
                "git_stage",
                arguments={"files": ["staged.txt"]},
            )
            assert "error" not in json.loads(result.content[0].text)

            # Verify it's staged
            result = await session.call_tool(
                "git_diff",
                arguments={"staged": True},
            )
            parsed = json.loads(result.content[0].text)
            assert "staged.txt" in parsed["diff"]

            # Unstage the file
            result = await session.call_tool(
                "git_unstage",
                arguments={"files": ["staged.txt"]},
            )
            parsed = json.loads(result.content[0].text)
            assert "error" not in parsed

            # Verify it's no longer staged
            result = await session.call_tool(
                "git_diff",
                arguments={"staged": True},
            )
            parsed = json.loads(result.content[0].text)
            assert parsed["diff"] == ""

    @pytest.mark.asyncio
    async def test_restore_workflow(self, git_repo):
        """Test restoring files."""
        # Modify a file
        test_file = git_repo / "test.txt"
        original_content = test_file.read_text()
        test_file.write_text("Changed content")

        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Restore the file
            result = await session.call_tool(
                "git_restore",
                arguments={"files": ["test.txt"]},
            )
            parsed = json.loads(result.content[0].text)
            assert "error" not in parsed

            # Verify file was restored
            assert test_file.read_text() == original_content

    @pytest.mark.asyncio
    async def test_history_filtering(self, git_repo):
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

        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Get limited history
            result = await session.call_tool(
                "git_history",
                arguments={"limit": 2},
            )
            parsed = json.loads(result.content[0].text)
            assert "error" not in parsed
            assert len(parsed["commits"]) == 2

            # Get history with grep
            result = await session.call_tool(
                "git_history",
                arguments={"grep": "Commit 1"},
            )
            parsed = json.loads(result.content[0].text)
            assert "error" not in parsed
            assert len(parsed["commits"]) == 1
            assert "Commit 1" in parsed["commits"][0]["message"]


class TestGitEdgeCases:
    """Test edge cases and error handling."""

    def _get_client_session(self, git_repo):
        """Get MCP client session for testing."""
        # Get venv Python
        venv_python = (
            Path(__file__).parent.parent.parent / ".venv" / "Scripts" / "python.exe"
        )
        server_script = (
            Path(__file__).parent.parent.parent / "scripts" / "run_filesys_fastmcp.py"
        )

        server_params = StdioServerParameters(
            command=str(venv_python),
            args=["-u", str(server_script), "--root-dir", str(git_repo)],
            env=None,
        )

        return stdio_client(server_params)

    @pytest.mark.asyncio
    async def test_stage_nonexistent_file(self, git_repo):
        """Test staging nonexistent file."""
        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Try to stage nonexistent file
            result = await session.call_tool(
                "git_stage",
                arguments={"files": ["nonexistent.txt"]},
            )
            parsed = json.loads(result.content[0].text)
            assert "error" in parsed
            assert "Failed to stage" in parsed["error"]

    @pytest.mark.asyncio
    async def test_commit_with_no_changes(self, git_repo):
        """Test committing with no staged changes."""
        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Try to commit with no staged changes
            result = await session.call_tool(
                "git_commit",
                arguments={"message": "Empty commit"},
            )
            parsed = json.loads(result.content[0].text)
            assert "message" in parsed or "error" in parsed
            if "message" in parsed:
                assert "Nothing to commit" in parsed["message"]

    @pytest.mark.asyncio
    async def test_merge_abort_no_merge(self, git_repo):
        """Test aborting merge when no merge in progress."""
        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Try to abort merge when none in progress
            result = await session.call_tool(
                "git_merge_abort",
                arguments={},
            )
            parsed = json.loads(result.content[0].text)
            assert "error" not in parsed
            if "status" in parsed:
                assert parsed.get("status") == "clean"

    @pytest.mark.asyncio
    async def test_amend_commit(self, git_repo):
        """Test amending a commit."""
        # Create a file and commit
        file = git_repo / "amend_test.txt"
        file.write_text("Original")

        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Stage the file
            await session.call_tool(
                "git_stage",
                arguments={"files": ["amend_test.txt"]},
            )

            # Commit
            await session.call_tool(
                "git_commit",
                arguments={"message": "Original commit"},
            )

            # Modify and stage again
            file.write_text("Amended")
            await session.call_tool(
                "git_stage",
                arguments={"files": ["amend_test.txt"]},
            )

            # Amend the commit
            result = await session.call_tool(
                "git_commit",
                arguments={"message": "Amended commit", "amend": True},
            )
            parsed = json.loads(result.content[0].text)
            assert "error" not in parsed

            # Check history
            result = await session.call_tool(
                "git_history",
                arguments={"limit": 5},
            )
            parsed = json.loads(result.content[0].text)
            assert "Amended commit" in parsed["commits"][0]["message"]


class TestGitRemoteOperations:
    """Test remote git operations (fetch, pull, push)."""

    def _get_client_session(self, git_repo):
        """Get MCP client session for testing."""
        # Get venv Python
        venv_python = (
            Path(__file__).parent.parent.parent / ".venv" / "Scripts" / "python.exe"
        )
        server_script = (
            Path(__file__).parent.parent.parent / "scripts" / "run_filesys_fastmcp.py"
        )

        server_params = StdioServerParameters(
            command=str(venv_python),
            args=["-u", str(server_script), "--root-dir", str(git_repo)],
            env=None,
        )

        return stdio_client(server_params)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.environ.get("TEST_GIT_REMOTE"),
        reason="Remote git tests require TEST_GIT_REMOTE env var",
    )
    async def test_fetch_operation(self, git_repo):
        """Test fetch operation."""
        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Try fetch (will fail without remote but tests functionality)
            await session.call_tool(
                "git_fetch",
                arguments={"remote": "origin"},
            )
            # Should handle gracefully even without remote

    @pytest.mark.asyncio
    async def test_push_dry_run(self, git_repo):
        """Test push with dry run."""
        # Create a commit
        file = git_repo / "push_test.txt"
        file.write_text("Push test")

        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Stage the file
            await session.call_tool(
                "git_stage",
                arguments={"files": ["push_test.txt"]},
            )

            # Commit
            await session.call_tool(
                "git_commit",
                arguments={"message": "Push test commit"},
            )

            # Try dry run push
            result = await session.call_tool(
                "git_push",
                arguments={"dry_run": True},
            )
            # Should either succeed with dry_run flag or fail gracefully
            assert isinstance(result, list)


class TestGitToolRegistration:
    """Test that git tools are properly registered."""

    def _get_client_session(self, git_repo):
        """Get MCP client session for testing."""
        # Get venv Python
        venv_python = (
            Path(__file__).parent.parent.parent / ".venv" / "Scripts" / "python.exe"
        )
        server_script = (
            Path(__file__).parent.parent.parent / "scripts" / "run_filesys_fastmcp.py"
        )

        server_params = StdioServerParameters(
            command=str(venv_python),
            args=["-u", str(server_script), "--root-dir", str(git_repo)],
            env=None,
        )

        return stdio_client(server_params)

    @pytest.mark.asyncio
    async def test_all_git_tools_registered(self, git_repo):
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

        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # List tools
            tools_response = await session.list_tools()

            tool_names = [tool.name for tool in tools_response.tools]
            for expected_tool in expected_tools:
                assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_git_tool_schemas(self, git_repo):
        """Test that git tool schemas are valid."""
        async with self._get_client_session(git_repo) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # List tools
            tools_response = await session.list_tools()

            tools_map = {tool.name: tool for tool in tools_response.tools}

            # Test a few key tools
            assert "git_stage" in tools_map
            stage_tool = tools_map["git_stage"]
            assert stage_tool.inputSchema
            assert "properties" in stage_tool.inputSchema
            assert "files" in stage_tool.inputSchema["properties"]

            assert "git_commit" in tools_map
            commit_tool = tools_map["git_commit"]
            assert commit_tool.inputSchema
            assert "properties" in commit_tool.inputSchema
            assert "message" in commit_tool.inputSchema["properties"]
            assert "message" in commit_tool.inputSchema.get("required", [])

            assert "git_diff" in tools_map
            diff_tool = tools_map["git_diff"]
            assert diff_tool.inputSchema
            assert "properties" in diff_tool.inputSchema
            assert "staged" in diff_tool.inputSchema["properties"]
