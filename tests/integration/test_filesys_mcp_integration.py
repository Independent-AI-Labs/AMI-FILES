"""Integration tests for Filesystem MCP Server."""

import asyncio
import tempfile
from pathlib import Path

import pytest
from files.backend.mcp.filesys.server import FilesysMCPServer


class TestFilesysMCPIntegration:
    """Integration tests for Filesystem MCP Server."""

    @pytest.fixture
    async def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    async def server(self, temp_dir):
        """Create a test server instance."""
        return FilesysMCPServer(root_dir=str(temp_dir))

    @pytest.mark.asyncio
    async def test_complete_file_workflow(self, server, temp_dir):
        """Test a complete file operation workflow."""
        # 1. Create directory structure
        result = await server.execute_tool("create_dirs", {"path": "project/src"})
        assert "message" in result

        result = await server.execute_tool("create_dirs", {"path": "project/tests"})
        assert "message" in result

        result = await server.execute_tool("create_dirs", {"path": "project/docs"})
        assert "message" in result

        # 2. Write some files
        files_to_create = [
            ("project/src/main.py", 'def main():\n    print("Hello, World!")'),
            ("project/src/utils.py", 'def helper():\n    return "Helper function"'),
            ("project/tests/test_main.py", "def test_main():\n    assert True"),
            (
                "project/docs/README.md",
                "# Project Documentation\n\nThis is the main documentation.",
            ),
            ("project/.gitignore", "*.pyc\n__pycache__/\n.env"),
        ]

        for file_path, content in files_to_create:
            result = await server.execute_tool(
                "write_to_file",
                {
                    "path": file_path,
                    "content": content,
                },
            )
            assert "message" in result

        # 3. List directory structure
        result = await server.execute_tool(
            "list_dir",
            {
                "path": "project",
                "recursive": True,
            },
        )
        assert "items" in result
        assert len(result["items"]) >= 8  # 3 dirs + 5 files

        # 4. Find Python files
        result = await server.execute_tool(
            "find_paths",
            {
                "path": "project",
                "keywords_path_name": [".py"],
            },
        )
        assert "matches" in result
        assert len(result["matches"]) == 3

        # 5. Modify a file
        result = await server.execute_tool(
            "modify_file",
            {
                "path": "project/src/main.py",
                "start_offset_inclusive": 1,
                "end_offset_inclusive": 1,
                "new_content": '    print("Modified Hello!")',
                "offset_type": "line",
            },
        )
        assert "message" in result

        # 6. Read modified file
        result = await server.execute_tool(
            "read_from_file", {"path": "project/src/main.py"}
        )
        assert "content" in result
        assert "Modified Hello!" in result["content"]

        # 7. Replace in all Python files
        for py_file in [
            "project/src/main.py",
            "project/src/utils.py",
            "project/tests/test_main.py",
        ]:
            result = await server.execute_tool(
                "replace_in_file",
                {
                    "path": py_file,
                    "old_content": "def ",
                    "new_content": "async def ",
                },
            )
            assert "replacements" in result

        # 8. Verify replacements
        result = await server.execute_tool(
            "read_from_file", {"path": "project/src/utils.py"}
        )
        assert "async def helper" in result["content"]

        # 9. Clean up specific files
        result = await server.execute_tool(
            "delete_paths", {"paths": ["project/.gitignore"]}
        )
        assert "deleted" in result
        assert len(result["deleted"]) == 1

        # 10. Final directory listing
        result = await server.execute_tool("list_dir", {"path": "project"})
        assert "items" in result
        # .gitignore should be gone
        names = {item["path"] for item in result["items"]}
        assert ".gitignore" not in names

    @pytest.mark.asyncio
    async def test_large_file_handling(self, server, temp_dir):
        """Test handling of large files."""
        # Create a large text file (1MB)
        large_content = "x" * 1024 * 1024  # 1MB of 'x'

        result = await server.execute_tool(
            "write_to_file",
            {
                "path": "large.txt",
                "content": large_content,
            },
        )
        assert "message" in result

        # Read with offsets
        result = await server.execute_tool(
            "read_from_file",
            {
                "path": "large.txt",
                "start_offset_inclusive": 0,
                "end_offset_inclusive": 1023,
                "offset_type": "byte",
            },
        )
        assert "content" in result
        assert len(result["content"]) == 1024

        # Find in large file
        # Add marker in the middle
        middle = len(large_content) // 2
        marked_content = large_content[:middle] + "MARKER" + large_content[middle + 6 :]

        result = await server.execute_tool(
            "write_to_file",
            {
                "path": "large_marked.txt",
                "content": marked_content,
            },
        )

        result = await server.execute_tool(
            "find_paths",
            {
                "path": ".",
                "keywords_file_content": ["MARKER"],
            },
        )
        assert "matches" in result
        assert any("large_marked.txt" in match for match in result["matches"])

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, server, temp_dir):
        """Test concurrent file operations."""
        # Create multiple files concurrently
        tasks = []
        for i in range(10):
            task = server.execute_tool(
                "write_to_file",
                {
                    "path": f"concurrent_{i}.txt",
                    "content": f"Content {i}",
                },
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        assert all("message" in r for r in results)

        # Read multiple files concurrently
        tasks = []
        for i in range(10):
            task = server.execute_tool(
                "read_from_file", {"path": f"concurrent_{i}.txt"}
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            assert "content" in result
            assert f"Content {i}" in result["content"]

        # Delete all concurrently created files
        paths = [f"concurrent_{i}.txt" for i in range(10)]
        result = await server.execute_tool("delete_paths", {"paths": paths})
        assert len(result["deleted"]) == 10

    @pytest.mark.asyncio
    async def test_encoding_formats(self, server, temp_dir):
        """Test different encoding formats."""
        # Test quoted-printable
        content_with_special = "Hello=World!\nLine 2 with spaces    \nTab\there"

        import quopri

        qp_encoded = quopri.encodestring(content_with_special.encode()).decode()

        result = await server.execute_tool(
            "write_to_file",
            {
                "path": "quoted.txt",
                "content": qp_encoded,
                "input_format": "quoted-printable",
            },
        )
        assert "message" in result

        result = await server.execute_tool(
            "read_from_file",
            {
                "path": "quoted.txt",
                "output_format": "quoted-printable",
            },
        )
        assert "content" in result

        # Test base64
        import base64

        b64_content = "Binary\x00Data\xFF"
        b64_encoded = base64.b64encode(b64_content.encode()).decode()

        result = await server.execute_tool(
            "write_to_file",
            {
                "path": "base64.txt",
                "content": b64_encoded,
                "input_format": "base64",
                "mode": "binary",
            },
        )
        assert "message" in result

        result = await server.execute_tool(
            "read_from_file",
            {
                "path": "base64.txt",
                "output_format": "base64",
            },
        )
        assert "content" in result
        decoded = base64.b64decode(result["content"]).decode("utf-8", errors="replace")
        assert "Binary" in decoded
        assert "Data" in decoded

    @pytest.mark.asyncio
    async def test_error_handling(self, server, temp_dir):
        """Test error handling in various scenarios."""
        # Read non-existent file
        result = await server.execute_tool(
            "read_from_file", {"path": "nonexistent.txt"}
        )
        assert "error" in result
        assert "does not exist" in result["error"]

        # List non-existent directory
        result = await server.execute_tool("list_dir", {"path": "nonexistent_dir"})
        assert "error" in result

        # Write to path outside root
        result = await server.execute_tool(
            "write_to_file",
            {
                "path": "../../outside.txt",
                "content": "Should fail",
            },
        )
        assert "error" in result
        assert "outside" in result["error"].lower()

        # Delete non-existent files
        result = await server.execute_tool(
            "delete_paths", {"paths": ["nonexistent1.txt", "nonexistent2.txt"]}
        )
        assert "errors" in result
        assert len(result["errors"]) == 2

        # Modify non-existent file
        result = await server.execute_tool(
            "modify_file",
            {
                "path": "nonexistent.txt",
                "start_offset_inclusive": 0,
                "end_offset_inclusive": 0,
                "new_content": "Should fail",
            },
        )
        assert "error" in result

        # Replace in non-existent file
        result = await server.execute_tool(
            "replace_in_file",
            {
                "path": "nonexistent.txt",
                "old_content": "old",
                "new_content": "new",
            },
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_protocol_compliance(self, server, temp_dir):
        """Test MCP protocol compliance."""
        # Server should have tools registered
        assert len(server.tools) > 0

        # Each tool should have proper schema
        for tool_name, tool_info in server.tools.items():
            assert tool_name  # Verify tool name exists
            assert "description" in tool_info
            assert isinstance(tool_info["description"], str)
            assert "inputSchema" in tool_info
            assert tool_info["inputSchema"]["type"] == "object"
            assert "properties" in tool_info["inputSchema"]
            assert isinstance(tool_info["inputSchema"]["properties"], dict)

            if "required" in tool_info["inputSchema"]:
                assert isinstance(tool_info["inputSchema"]["required"], list)

        # Test tool execution returns proper format
        result = await server.execute_tool("list_dir", {"path": "."})
        assert isinstance(result, dict)

        # Error responses should have error key
        result = await server.execute_tool("unknown_tool", {})
        assert "error" in result
