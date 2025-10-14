"""Integration tests for Filesys FastMCP server using official MCP client."""

# TODO[tests]: Add coverage for document and image tools once persistence and
#              Gemini workflows stabilize.

import json
import tempfile
from pathlib import Path

import pytest
from base.scripts.env.paths import find_module_root
from base.scripts.env.venv import get_venv_python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# sys.path already configured by conftest.py


class TestFilesysFastMCPServer:
    """Test Filesys FastMCP server using official MCP client."""

    @pytest.mark.asyncio
    async def test_filesys_server_with_client(self) -> None:
        """Test Filesys FastMCP server using official MCP client."""
        # Get the server script path
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"

        # Use the module's venv python
        module_root = find_module_root(Path(__file__))
        venv_python = get_venv_python(module_root)

        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create stdio server parameters with temp directory as root
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            # Use the stdio client to connect
            async with (
                stdio_client(server_params) as (
                    read_stream,
                    write_stream,
                ),
                ClientSession(read_stream, write_stream) as session,
            ):
                # Initialize the connection
                result = await session.initialize()

                # Check server info
                assert result.serverInfo.name == "FilesysMCPServer"
                assert result.protocolVersion in ["2024-11-05", "2025-06-18"]

                # List available tools
                tools_response = await session.list_tools()
                tool_names = [tool.name for tool in tools_response.tools]

                # Verify expected filesystem tools exist
                assert "read_from_file" in tool_names
                assert "write_to_file" in tool_names
                assert "list_dir" in tool_names
                assert "delete_paths" in tool_names
                assert "create_dirs" in tool_names

    @pytest.mark.asyncio
    async def test_file_operations(self) -> None:
        """Test file read and write operations."""
        module_root = find_module_root(Path(__file__))
        server_script = module_root / "scripts" / "run_filesys_fastmcp.py"

        module_root = find_module_root(Path(__file__))
        venv_python = get_venv_python(module_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            server_params = StdioServerParameters(
                command=str(venv_python),
                args=["-u", str(server_script), "--root-dir", temp_dir],
                env=None,
            )

            async with (
                stdio_client(server_params) as (
                    read_stream,
                    write_stream,
                ),
                ClientSession(read_stream, write_stream) as session,
            ):
                # Initialize
                await session.initialize()

                # Write a file
                test_content = "Hello from FastMCP test!"
                write_result = await session.call_tool(
                    "write_to_file",
                    arguments={"path": "test.txt", "content": test_content},
                )

                assert write_result is not None
                assert len(write_result.content) > 0

                # Read the file back
                read_result = await session.call_tool(
                    "read_from_file",
                    arguments={"path": "test.txt"},
                )

                assert read_result is not None
                if read_result.content[0].type == "text":
                    # Parse the response
                    response_text = read_result.content[0].text
                    # The response might be JSON or direct text
                    try:
                        response = json.loads(response_text)
                        content = response.get("content", "")
                    except json.JSONDecodeError:
                        content = response_text

                    assert test_content in content
