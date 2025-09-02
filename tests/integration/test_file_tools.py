#!/usr/bin/env python
"""Integration tests for Filesystem tools using FastMCP server with MCP client."""

import asyncio
import base64
import json
import quopri
import sys
import tempfile
from pathlib import Path
from typing import Any, AsyncContextManager

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

# Add files to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def get_text_content(result: object) -> str:
    """Extract text content from MCP result, handling union types properly."""
    if hasattr(result, "content") and result.content and len(result.content) > 0:
        content_item = result.content[0]
        if isinstance(content_item, TextContent):
            return content_item.text
        raise TypeError(f"Expected TextContent, got {type(content_item)}")
    raise ValueError("No content found in result")


class TestFileTools:
    """Test file system tools through FastMCP server using MCP client."""

    @pytest.fixture
    def server_script(self) -> Path:
        """Get the server script path."""
        return (
            Path(__file__).parent.parent.parent / "scripts" / "run_filesys_fastmcp.py"
        )

    @pytest.fixture
    def venv_python(self) -> Path:
        """Get the venv Python executable."""
        from base.backend.utils.environment_setup import EnvironmentSetup

        return Path(EnvironmentSetup.get_module_venv_python(Path(__file__)))

    async def _get_client_session(
        self, venv_python: Path, server_script: Path, temp_dir: str
    ) -> AsyncContextManager[tuple[Any, Any]]:
        """Helper to get client session."""
        server_params = StdioServerParameters(
            command=str(venv_python),
            args=["-u", str(server_script), "--root-dir", temp_dir],
            env=None,
        )
        return stdio_client(server_params)

    @pytest.mark.asyncio
    async def test_complete_file_workflow(
        self, venv_python: Path, server_script: Path
    ) -> None:
        """Test a complete file operation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with (
                await self._get_client_session(
                    venv_python, server_script, temp_dir
                ) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                # Initialize
                await session.initialize()

                # 1. Create directory structure
                result = await session.call_tool(
                    "create_dirs",
                    arguments={
                        "paths": ["project/src", "project/tests", "project/docs"]
                    },
                )
                assert result is not None

                # 2. Write some files
                files_to_create = [
                    (
                        "project/src/main.py",
                        '"""Main module."""\n\n\ndef main() -> None:\n    """Main function."""\n    print("Hello, World!")\n',
                    ),
                    (
                        "project/src/utils.py",
                        '"""Utilities module."""\n\n\ndef helper() -> str:\n    """Helper function."""\n    return "Helper function"\n',
                    ),
                    (
                        "project/tests/test_main.py",
                        '"""Tests for main module."""\n\n\ndef test_main() -> None:\n    """Test main function."""\n    assert True\n',
                    ),
                    (
                        "project/docs/README.md",
                        "# Project Documentation\n\nThis is the main documentation.",
                    ),
                    ("project/.gitignore", "*.pyc\n__pycache__/\n.env"),
                ]

                for file_path, content in files_to_create:
                    result = await session.call_tool(
                        "write_to_file",
                        arguments={"path": file_path, "content": content},
                    )
                    assert result is not None

                # 3. List directory structure
                result = await session.call_tool(
                    "list_dir", arguments={"path": "project", "recursive": True}
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "items" in response
                assert len(response["items"]) >= 8  # 3 dirs + 5 files

                # 4. Find Python files
                result = await session.call_tool(
                    "find_paths",
                    arguments={"path": "project", "keywords_path_name": [".py"]},
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "paths" in response or "matches" in response
                paths = response.get("paths", response.get("matches", []))
                assert len(paths) == 3

                # 5. Modify a file - replace line 6 (the print statement)
                result = await session.call_tool(
                    "modify_file",
                    arguments={
                        "path": "project/src/main.py",
                        "start_offset_inclusive": 6,
                        "end_offset_inclusive": 6,
                        "new_content": '    print("Modified Hello!")',
                        "offset_type": "line",
                    },
                )
                assert result is not None

                # 6. Read modified file
                result = await session.call_tool(
                    "read_from_file", arguments={"path": "project/src/main.py"}
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "content" in response
                assert "Modified Hello!" in response["content"]

                # 7. Replace in all Python files
                for py_file in [
                    "project/src/main.py",
                    "project/src/utils.py",
                    "project/tests/test_main.py",
                ]:
                    result = await session.call_tool(
                        "replace_in_file",
                        arguments={
                            "path": py_file,
                            "old_content": "def ",
                            "new_content": "async def ",
                        },
                    )
                    assert result is not None

                # 8. Verify replacements
                result = await session.call_tool(
                    "read_from_file", arguments={"path": "project/src/utils.py"}
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "async def helper" in response["content"]

                # 9. Clean up specific files
                result = await session.call_tool(
                    "delete_paths", arguments={"paths": ["project/.gitignore"]}
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "deleted" in response
                assert len(response["deleted"]) == 1

                # 10. Final directory listing
                result = await session.call_tool(
                    "list_dir", arguments={"path": "project"}
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "items" in response
                # .gitignore should be gone
                names = {item["path"] for item in response["items"]}
                assert ".gitignore" not in names

    @pytest.mark.asyncio
    async def test_large_file_handling(
        self, venv_python: Path, server_script: Path
    ) -> None:
        """Test handling of large files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with (
                await self._get_client_session(
                    venv_python, server_script, temp_dir
                ) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                # Initialize
                await session.initialize()

                # Create a large text file (1MB)
                large_content = "x" * 1024 * 1024  # 1MB of 'x'

                result = await session.call_tool(
                    "write_to_file",
                    arguments={"path": "large.txt", "content": large_content},
                )
                assert result is not None

                # Read with offsets
                result = await session.call_tool(
                    "read_from_file",
                    arguments={
                        "path": "large.txt",
                        "start_offset_inclusive": 0,
                        "end_offset_inclusive": 1023,
                        "offset_type": "byte",
                    },
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "content" in response
                assert len(response["content"]) == 1024

                # Find in large file - Add marker in the middle
                middle = len(large_content) // 2
                marked_content = (
                    large_content[:middle] + "MARKER" + large_content[middle + 6 :]
                )

                result = await session.call_tool(
                    "write_to_file",
                    arguments={
                        "path": "large_marked.txt",
                        "content": marked_content,
                    },
                )
                assert result is not None

                result = await session.call_tool(
                    "find_paths",
                    arguments={"path": ".", "keywords_file_content": ["MARKER"]},
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "paths" in response or "matches" in response
                paths = response.get("paths", response.get("matches", []))
                assert any("large_marked.txt" in path for path in paths)

    @pytest.mark.asyncio
    async def test_concurrent_operations(
        self, venv_python: Path, server_script: Path
    ) -> None:
        """Test concurrent file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with (
                await self._get_client_session(
                    venv_python, server_script, temp_dir
                ) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                # Initialize
                await session.initialize()

                # Create multiple files concurrently
                tasks = []
                for i in range(10):
                    task = session.call_tool(
                        "write_to_file",
                        arguments={
                            "path": f"concurrent_{i}.txt",
                            "content": f"Content {i}",
                        },
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks)
                assert all(r is not None for r in results)

                # Read multiple files concurrently
                tasks = []
                for i in range(10):
                    task = session.call_tool(
                        "read_from_file", arguments={"path": f"concurrent_{i}.txt"}
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks)
                for i, result in enumerate(results):
                    assert result is not None
                    response_text = get_text_content(result)
                    response = json.loads(response_text)
                    assert "content" in response
                    assert f"Content {i}" in response["content"]

                # Delete all concurrently created files
                paths = [f"concurrent_{i}.txt" for i in range(10)]
                result = await session.call_tool(
                    "delete_paths", arguments={"paths": paths}
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert len(response["deleted"]) == 10

    @pytest.mark.asyncio
    async def test_encoding_formats(
        self, venv_python: Path, server_script: Path
    ) -> None:
        """Test different encoding formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with (
                await self._get_client_session(
                    venv_python, server_script, temp_dir
                ) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                # Initialize
                await session.initialize()

                # Test quoted-printable
                content_with_special = "Hello=World!\nLine 2 with spaces    \nTab\there"
                qp_encoded = quopri.encodestring(content_with_special.encode()).decode()

                result = await session.call_tool(
                    "write_to_file",
                    arguments={
                        "path": "quoted.txt",
                        "content": qp_encoded,
                        "input_format": "quoted-printable",
                    },
                )
                assert result is not None

                result = await session.call_tool(
                    "read_from_file",
                    arguments={
                        "path": "quoted.txt",
                        "output_format": "quoted-printable",
                    },
                )
                assert result is not None

                # Test base64
                b64_content = "Binary\x00Data\xff"
                b64_encoded = base64.b64encode(b64_content.encode()).decode()

                result = await session.call_tool(
                    "write_to_file",
                    arguments={
                        "path": "base64.txt",
                        "content": b64_encoded,
                        "input_format": "base64",
                        "mode": "binary",
                    },
                )
                assert result is not None

                result = await session.call_tool(
                    "read_from_file",
                    arguments={"path": "base64.txt", "output_format": "base64"},
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "content" in response
                decoded = base64.b64decode(response["content"]).decode(
                    "utf-8", errors="replace"
                )
                assert "Binary" in decoded
                assert "Data" in decoded

    @pytest.mark.asyncio
    async def test_error_handling(self, venv_python: Path, server_script: Path) -> None:
        """Test error handling in various scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with (
                await self._get_client_session(
                    venv_python, server_script, temp_dir
                ) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                # Initialize
                await session.initialize()

                # Read non-existent file
                result = await session.call_tool(
                    "read_from_file", arguments={"path": "nonexistent.txt"}
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "error" in response
                assert "does not exist" in response["error"]

                # List non-existent directory
                result = await session.call_tool(
                    "list_dir", arguments={"path": "nonexistent_dir"}
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "error" in response

                # Write to path outside root
                result = await session.call_tool(
                    "write_to_file",
                    arguments={"path": "../../outside.txt", "content": "Should fail"},
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "error" in response
                assert "outside" in response["error"].lower()

                # Delete non-existent files
                result = await session.call_tool(
                    "delete_paths",
                    arguments={"paths": ["nonexistent1.txt", "nonexistent2.txt"]},
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "errors" in response
                assert len(response["errors"]) == 2

                # Modify non-existent file
                result = await session.call_tool(
                    "modify_file",
                    arguments={
                        "path": "nonexistent.txt",
                        "start_offset_inclusive": 0,
                        "end_offset_inclusive": 0,
                        "new_content": "Should fail",
                    },
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "error" in response

                # Replace in non-existent file
                result = await session.call_tool(
                    "replace_in_file",
                    arguments={
                        "path": "nonexistent.txt",
                        "old_content": "old",
                        "new_content": "new",
                    },
                )
                assert result is not None
                response_text = get_text_content(result)
                response = json.loads(response_text)
                assert "error" in response

    @pytest.mark.asyncio
    async def test_protocol_compliance(
        self, venv_python: Path, server_script: Path
    ) -> None:
        """Test MCP protocol compliance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with (
                await self._get_client_session(
                    venv_python, server_script, temp_dir
                ) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                # Initialize
                result = await session.initialize()
                assert result.serverInfo.name == "FilesysMCPServer"

                # List tools
                tools_response = await session.list_tools()
                assert len(tools_response.tools) > 0

                # Each tool should have proper schema
                for tool in tools_response.tools:
                    assert tool.name  # Verify tool name exists
                    assert tool.description
                    assert isinstance(tool.description, str)
                    assert tool.inputSchema
                    assert tool.inputSchema["type"] == "object"
                    assert "properties" in tool.inputSchema
                    assert isinstance(tool.inputSchema["properties"], dict)

                    if "required" in tool.inputSchema:
                        assert isinstance(tool.inputSchema["required"], list)

                # Test tool execution returns proper format
                call_result = await session.call_tool(
                    "list_dir", arguments={"path": "."}
                )
                assert call_result is not None
                assert isinstance(call_result.content, list)
                assert len(call_result.content) > 0

                # Error responses should have error key in the response
                call_result = await session.call_tool(
                    "read_from_file", arguments={"path": "nonexistent.txt"}
                )
                assert call_result is not None
                response_text = get_text_content(call_result)
                response = json.loads(response_text)
                assert "error" in response
