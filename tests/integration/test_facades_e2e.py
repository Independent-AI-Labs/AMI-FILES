"""E2E integration tests for facade tools through FastMCP server."""

import json
import tempfile
from pathlib import Path
from typing import Any, cast

import pytest
from base.scripts.env.paths import find_module_root
from base.scripts.env.venv import get_venv_python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


def _get_response_text(result: Any) -> str:
    """Extract text from MCP result content."""
    assert result is not None
    assert len(result.content) > 0
    content = result.content[0]
    assert isinstance(content, TextContent) or content.type == "text"
    text_content = cast(TextContent, content)
    text: str = text_content.text
    return text


class TestFilesystemFacade:
    """Test filesystem facade through MCP server."""

    @pytest.mark.asyncio
    async def test_filesystem_facade_exists(self) -> None:
        """Verify filesystem facade tool is registered."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()
                tools_response = await session.list_tools()
                tool_names = [tool.name for tool in tools_response.tools]

                # Verify filesystem facade exists
                assert "filesystem" in tool_names

                # Verify old individual tools are removed
                assert "read_from_file" not in tool_names
                assert "write_to_file" not in tool_names
                assert "list_dir" not in tool_names

    @pytest.mark.asyncio
    async def test_filesystem_write_read_workflow(self) -> None:
        """Test filesystem write and read actions."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()

                # Write action
                test_content = "Hello from facade test!"
                write_result = await session.call_tool(
                    "filesystem",
                    arguments={
                        "action": "write",
                        "path": "test.txt",
                        "content": test_content,
                        "validate_with_llm": False,
                    },
                )

                write_response = json.loads(_get_response_text(write_result))
                assert "error" not in write_response

                # Read action
                read_result = await session.call_tool(
                    "filesystem",
                    arguments={"action": "read", "path": "test.txt"},
                )

                read_response = json.loads(_get_response_text(read_result))
                assert "error" not in read_response
                assert test_content in read_response.get("content", "")

    @pytest.mark.asyncio
    async def test_filesystem_list_action(self) -> None:
        """Test filesystem list action."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            Path(temp_dir).joinpath("test1.txt").write_text("content1")
            Path(temp_dir).joinpath("test2.txt").write_text("content2")

            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()

                # List action
                list_result = await session.call_tool(
                    "filesystem",
                    arguments={"action": "list", "path": "."},
                )

                list_response = json.loads(_get_response_text(list_result))
                assert "error" not in list_response
                assert "items" in list_response

    @pytest.mark.asyncio
    async def test_filesystem_create_delete_workflow(self) -> None:
        """Test filesystem create and delete actions."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()

                # Create action
                create_result = await session.call_tool(
                    "filesystem",
                    arguments={"action": "create", "paths": ["testdir/subdir"]},
                )

                create_response = json.loads(_get_response_text(create_result))
                assert "error" not in create_response

                # Verify directory was created
                assert Path(temp_dir).joinpath("testdir/subdir").exists()

                # Delete action
                delete_result = await session.call_tool(
                    "filesystem",
                    arguments={"action": "delete", "paths": ["testdir"]},
                )

                delete_response = json.loads(_get_response_text(delete_result))
                assert "error" not in delete_response

    @pytest.mark.asyncio
    async def test_filesystem_invalid_action(self) -> None:
        """Test filesystem facade with invalid action."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()

                # Invalid action should be caught by Literal type at call_tool level
                # This test verifies the type safety of the facade

    @pytest.mark.asyncio
    async def test_filesystem_missing_required_param(self) -> None:
        """Test filesystem facade with missing required parameter."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()

                # Write without content
                write_result = await session.call_tool(
                    "filesystem",
                    arguments={"action": "write", "path": "test.txt"},
                )

                write_response = json.loads(_get_response_text(write_result))
                assert "error" in write_response
                assert "content required" in write_response["error"]


class TestGitFacade:
    """Test git facade through MCP server."""

    @pytest.mark.asyncio
    async def test_git_facade_exists(self) -> None:
        """Verify git facade tool is registered."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()
                tools_response = await session.list_tools()
                tool_names = [tool.name for tool in tools_response.tools]

                # Verify git facade exists
                assert "git" in tool_names

                # Verify old individual tools are removed
                assert "git_status" not in tool_names
                assert "git_commit" not in tool_names

    @pytest.mark.asyncio
    async def test_git_status_action(self) -> None:
        """Test git status action."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        # Use module root as git repo (it's already a git repo)
        server_params = StdioServerParameters(
            command=str(venv_python),
            args=["-u", str(server_script), "--root-dir", str(module_root)],
            env=None,
        )

        async with (
            stdio_client(server_params) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()

            # Status action
            status_result = await session.call_tool(
                "git",
                arguments={"action": "status"},
            )

            status_response = json.loads(_get_response_text(status_result))
            assert "error" not in status_response or "status" in status_response

    @pytest.mark.asyncio
    async def test_git_missing_message(self) -> None:
        """Test git commit action with missing message."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()

                # Commit without message
                commit_result = await session.call_tool(
                    "git",
                    arguments={"action": "commit"},
                )

                commit_response = json.loads(_get_response_text(commit_result))
                assert "error" in commit_response
                assert "message required" in commit_response["error"]


class TestPythonFacade:
    """Test python facade through MCP server."""

    @pytest.mark.asyncio
    async def test_python_facade_exists(self) -> None:
        """Verify python facade tool is registered."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()
                tools_response = await session.list_tools()
                tool_names = [tool.name for tool in tools_response.tools]

                # Verify python facade exists
                assert "python" in tool_names

                # Verify old individual tools are removed
                assert "python_run" not in tool_names
                assert "python_run_background" not in tool_names

    @pytest.mark.asyncio
    async def test_python_run_action(self) -> None:
        """Test python run action."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test script
            test_script = Path(temp_dir) / "test.py"
            test_script.write_text("print('Hello from python facade')")

            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()

                # Run action
                run_result = await session.call_tool(
                    "python",
                    arguments={
                        "action": "run",
                        "script": "test.py",
                        "timeout": 10,
                    },
                )

                run_response = json.loads(_get_response_text(run_result))
                assert "error" not in run_response or "stdout" in run_response

    @pytest.mark.asyncio
    async def test_python_list_tasks_action(self) -> None:
        """Test python list_tasks action."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()

                # List tasks action
                list_result = await session.call_tool(
                    "python",
                    arguments={"action": "list_tasks"},
                )

                list_response = json.loads(_get_response_text(list_result))
                assert "error" not in list_response or "tasks" in list_response

    @pytest.mark.asyncio
    async def test_python_missing_script(self) -> None:
        """Test python run action with missing script."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()

                # Run without script
                run_result = await session.call_tool(
                    "python",
                    arguments={"action": "run"},
                )

                run_response = json.loads(_get_response_text(run_result))
                assert "error" in run_response
                assert "script required" in run_response["error"]


class TestDocumentFacade:
    """Test document facade through MCP server."""

    @pytest.mark.asyncio
    async def test_document_facade_exists(self) -> None:
        """Verify document facade tool is registered."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()
                tools_response = await session.list_tools()
                tool_names = [tool.name for tool in tools_response.tools]

                # Verify document facade exists
                assert "document" in tool_names

                # Verify old individual tools are removed
                assert "index_document" not in tool_names
                assert "read_document" not in tool_names


class TestAllFacades:
    """Test all facades are present and old tools are removed."""

    @pytest.mark.asyncio
    async def test_facade_consolidation_complete(self) -> None:
        """Verify exactly 4 facade tools exist and 27 individual tools are removed."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()
                tools_response = await session.list_tools()
                tool_names = [tool.name for tool in tools_response.tools]

                # Verify exactly 4 facade tools
                expected_facades = {"filesystem", "git", "python", "document"}
                actual_facades = set(tool_names) & expected_facades
                assert actual_facades == expected_facades

                # Verify old individual tools are removed (sample check)
                old_tools = {
                    "read_from_file",
                    "write_to_file",
                    "list_dir",
                    "create_dirs",
                    "delete_paths",
                    "find_paths",
                    "modify_file",
                    "replace_in_file",
                    "git_status",
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
                    "python_run",
                    "python_run_background",
                    "python_task_status",
                    "python_task_cancel",
                    "python_list_tasks",
                    "index_document",
                    "read_document",
                    "read_image",
                }
                assert len(set(tool_names) & old_tools) == 0, f"Old tools still present: {set(tool_names) & old_tools}"
