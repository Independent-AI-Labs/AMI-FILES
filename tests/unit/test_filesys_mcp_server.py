"""Unit tests for Filesystem MCP Server."""

import tempfile
from pathlib import Path

import pytest
from files.backend.mcp.filesys.server import FilesysMCPServer


class TestFilesysMCPServer:
    """Test Filesystem MCP Server."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def server(self, temp_dir):
        """Create a test server instance."""
        return FilesysMCPServer(root_dir=str(temp_dir))

    def test_server_initialization(self, temp_dir):
        """Test server initializes correctly."""
        server = FilesysMCPServer(root_dir=str(temp_dir))
        # Compare resolved paths to handle symlinks properly
        assert server.root_dir.resolve() == temp_dir.resolve()
        assert len(server.tools) > 0
        assert server.registry is not None
        assert server.executor is not None
        # Response format is now handled in base class
        assert hasattr(server, "response_format")  # Should inherit from base
        assert server.response_format == "yaml"  # Default should be YAML

    def test_server_initialization_invalid_root(self):
        """Test server initialization with invalid root directory."""
        with pytest.raises(ValueError, match="Root directory does not exist"):
            FilesysMCPServer(
                root_dir="/definitely/nonexistent/path/that/should/not/exist/anywhere"
            )

    def test_server_initialization_file_as_root(self, temp_dir):
        """Test server initialization with file as root directory."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test")

        with pytest.raises(ValueError, match="Root path is not a directory"):
            FilesysMCPServer(root_dir=str(test_file))

    def test_register_tools(self, server):
        """Test that all tools are registered."""
        expected_tools = [
            "list_dir",
            "create_dirs",
            "find_paths",
            "read_from_file",
            "write_to_file",
            "delete_paths",
            "modify_file",
            "replace_in_file",
        ]

        for tool_name in expected_tools:
            assert tool_name in server.tools
            tool_info = server.tools[tool_name]
            assert "description" in tool_info
            assert "inputSchema" in tool_info
            assert tool_info["inputSchema"]["type"] == "object"
            assert "properties" in tool_info["inputSchema"]

    @pytest.mark.asyncio
    async def test_execute_tool_list_dir(self, server, temp_dir):
        """Test executing list_dir tool."""
        # Create test structure
        (temp_dir / "dir1").mkdir()
        (temp_dir / "dir2").mkdir()
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")

        result = await server.execute_tool("list_dir", {"path": "."})

        assert "items" in result
        assert len(result["items"]) == 4

        names = {item["path"] for item in result["items"]}
        assert "dir1" in names
        assert "dir2" in names
        assert "file1.txt" in names
        assert "file2.txt" in names

    @pytest.mark.asyncio
    async def test_execute_tool_create_dirs(self, server, temp_dir):
        """Test executing create_dirs tool."""
        new_path = "nested/deep/directory"

        result = await server.execute_tool("create_dirs", {"path": new_path})

        assert "message" in result
        assert "created" in result["message"].lower()
        assert (temp_dir / new_path).exists()
        assert (temp_dir / new_path).is_dir()

    @pytest.mark.asyncio
    async def test_execute_tool_write_and_read(self, server, temp_dir):
        """Test writing and reading a file."""
        # Write file
        write_result = await server.execute_tool(
            "write_to_file",
            {
                "path": "test.txt",
                "content": "Hello, World!",
            },
        )

        assert "message" in write_result
        assert (temp_dir / "test.txt").exists()

        # Read file
        read_result = await server.execute_tool("read_from_file", {"path": "test.txt"})

        assert "content" in read_result
        assert read_result["content"] == "Hello, World!"

    @pytest.mark.asyncio
    async def test_execute_tool_delete_paths(self, server, temp_dir):
        """Test deleting files and directories."""
        # Create test files and directories
        (temp_dir / "file1.txt").write_text("content")
        (temp_dir / "file2.txt").write_text("content")
        (temp_dir / "dir1").mkdir()
        (temp_dir / "dir1" / "nested.txt").write_text("nested")

        result = await server.execute_tool(
            "delete_paths", {"paths": ["file1.txt", "dir1"]}
        )

        assert "deleted" in result
        assert len(result["deleted"]) == 2
        assert not (temp_dir / "file1.txt").exists()
        assert not (temp_dir / "dir1").exists()
        assert (temp_dir / "file2.txt").exists()

    @pytest.mark.asyncio
    async def test_execute_tool_find_paths(self, server, temp_dir):
        """Test finding files by keywords."""
        # Create test structure
        (temp_dir / "docs").mkdir()
        (temp_dir / "docs" / "readme.md").write_text("This is documentation")
        (temp_dir / "docs" / "guide.md").write_text("User guide content")
        (temp_dir / "src").mkdir()
        (temp_dir / "src" / "main.py").write_text("print('Hello')")
        (temp_dir / "test.txt").write_text("Test documentation")

        # Find by path keyword
        result = await server.execute_tool(
            "find_paths",
            {
                "path": ".",
                "keywords_path_name": [".md"],
            },
        )

        assert "matches" in result
        assert len(result["matches"]) == 2

        # Find by content keyword
        result = await server.execute_tool(
            "find_paths",
            {
                "path": ".",
                "keywords_file_content": ["documentation"],
            },
        )

        assert "matches" in result
        assert len(result["matches"]) == 2

    @pytest.mark.asyncio
    async def test_read_file_with_line_numbers(self, server, temp_dir):
        """Test reading source code files with automatic line numbers."""
        # Create a Python file (should get line numbers automatically)
        python_content = "def hello():\n    print('Hello')\n\nhello()"
        (temp_dir / "test.py").write_text(python_content)

        # Read Python file - should have line numbers
        result = await server.execute_tool("read_from_file", {"path": "test.py"})
        assert "content" in result
        # Check for line numbers format (no spaces around pipe)
        assert "1|" in result["content"]

        # Create a text file (should not get line numbers by default)
        (temp_dir / "notes.txt").write_text("Just some notes")

        # Read text file - no line numbers
        result = await server.execute_tool("read_from_file", {"path": "notes.txt"})
        assert "content" in result
        assert "1|" not in result["content"]

        # Explicitly request line numbers for text file
        result = await server.execute_tool(
            "read_from_file", {"path": "notes.txt", "add_line_numbers": True}
        )
        assert "content" in result
        assert "1|" in result["content"]

    @pytest.mark.asyncio
    async def test_yaml_response_format(self):
        """Test server with YAML response format configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            # Create server with YAML format
            yaml_server = FilesysMCPServer(
                root_dir=str(temp_dir), config={"response_format": "yaml"}
            )

            # Write a test file
            (temp_dir / "test.py").write_text("print('test')")

            # Read file and check response format
            result = await yaml_server.execute_tool(
                "read_from_file", {"path": "test.py"}
            )

            # Should still be a dict but formatted for YAML output
            assert isinstance(result, dict)
            assert "content" in result
            assert "path" in result

    @pytest.mark.asyncio
    async def test_execute_tool_modify_file(self, server, temp_dir):
        """Test modifying a file."""
        # Create initial file
        (temp_dir / "test.txt").write_text("Line 1\nLine 2\nLine 3\n")

        # Modify file
        result = await server.execute_tool(
            "modify_file",
            {
                "path": "test.txt",
                "start_offset_inclusive": 1,
                "end_offset_inclusive": 1,
                "new_content": "Modified Line 2\n",
                "offset_type": "line",
            },
        )

        assert "message" in result

        # Verify modification
        content = (temp_dir / "test.txt").read_text()
        lines = content.splitlines()
        assert lines[0] == "Line 1"
        assert lines[1] == "Modified Line 2"
        assert lines[2] == "Line 3"

    @pytest.mark.asyncio
    async def test_execute_tool_replace_in_file(self, server, temp_dir):
        """Test replacing content in a file."""
        # Create initial file
        (temp_dir / "test.txt").write_text("Hello World! Hello Universe!")

        # Replace content
        result = await server.execute_tool(
            "replace_in_file",
            {
                "path": "test.txt",
                "old_content": "Hello",
                "new_content": "Hi",
            },
        )

        assert "replacements" in result
        assert result["replacements"] == 2

        # Verify replacement
        content = (temp_dir / "test.txt").read_text()
        assert content == "Hi World! Hi Universe!"

    @pytest.mark.asyncio
    async def test_execute_tool_with_invalid_path(self, server):
        """Test executing tools with paths outside root directory."""
        result = await server.execute_tool(
            "read_from_file", {"path": "../../../etc/passwd"}
        )

        assert "error" in result
        assert "outside" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, server):
        """Test executing an unknown tool."""
        result = await server.execute_tool("unknown_tool", {"arg": "value"})

        assert "error" in result
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    async def test_binary_file_operations(self, server, temp_dir):
        """Test binary file read/write operations."""
        # Write binary file
        binary_content = b"\x00\x01\x02\x03\xFF"
        import base64

        encoded = base64.b64encode(binary_content).decode("ascii")

        write_result = await server.execute_tool(
            "write_to_file",
            {
                "path": "test.bin",
                "content": encoded,
                "mode": "binary",
                "input_format": "base64",
            },
        )

        assert "message" in write_result
        assert (temp_dir / "test.bin").exists()

        # Read binary file
        read_result = await server.execute_tool(
            "read_from_file",
            {
                "path": "test.bin",
                "output_format": "base64",
            },
        )

        assert "content" in read_result
        # Binary files are automatically base64 encoded
        decoded = base64.b64decode(read_result["content"])
        assert decoded == binary_content

    @pytest.mark.asyncio
    async def test_recursive_directory_listing(self, server, temp_dir):
        """Test recursive directory listing."""
        # Create nested structure
        (temp_dir / "a").mkdir()
        (temp_dir / "a" / "b").mkdir()
        (temp_dir / "a" / "b" / "c").mkdir()
        (temp_dir / "a" / "file1.txt").write_text("content")
        (temp_dir / "a" / "b" / "file2.txt").write_text("content")
        (temp_dir / "a" / "b" / "c" / "file3.txt").write_text("content")

        # Non-recursive listing
        result = await server.execute_tool(
            "list_dir", {"path": "a", "recursive": False}
        )
        assert len(result["items"]) == 2  # b directory and file1.txt

        # Recursive listing
        result = await server.execute_tool("list_dir", {"path": "a", "recursive": True})
        assert (
            len(result["items"]) >= 5
        )  # All directories and files (at least the files and subdirs)

    @pytest.mark.asyncio
    async def test_regex_find_and_replace(self, server, temp_dir):
        """Test regex-based find and replace."""
        # Create test file
        (temp_dir / "test.txt").write_text("foo123 bar456 baz789")

        # Find with regex
        result = await server.execute_tool(
            "find_paths",
            {
                "path": ".",
                "keywords_file_content": [r"\d{3}"],
                "regex_keywords": True,
            },
        )
        assert len(result["matches"]) == 1

        # Replace with regex
        result = await server.execute_tool(
            "replace_in_file",
            {
                "path": "test.txt",
                "old_content": r"\d+",
                "new_content": "XXX",
                "is_regex": True,
            },
        )
        assert result["replacements"] == 3

        content = (temp_dir / "test.txt").read_text()
        assert content == "fooXXX barXXX bazXXX"
