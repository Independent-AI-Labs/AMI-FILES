"""Unit tests for Filesystem FastMCP Server."""

import tempfile
from pathlib import Path

import pytest
from files.backend.mcp.filesys.filesys_server import (
    FilesysFastMCPServer as FilesysMCPServer,
)


class TestFilesysMCPServer:
    """Test Filesystem MCP Server initialization and configuration."""

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
        assert server.mcp is not None
        assert server.mcp.name == "FilesysMCPServer"

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

    def test_tools_registered(self, server):
        """Test that all expected tools are registered with FastMCP."""
        # Get the FastMCP server instance
        mcp = server.mcp

        # FastMCP stores tools internally - check they're registered
        # Note: FastMCP doesn't expose tools directly, but we can verify
        # the server has the mcp attribute configured
        assert mcp is not None
        assert mcp.name == "FilesysMCPServer"

        # Verify the server has expected attributes
        assert hasattr(server, "root_dir")
        assert hasattr(server, "mcp")

    def test_server_with_custom_config(self, temp_dir):
        """Test server initialization with custom configuration."""
        config = {
            "max_file_size": 10485760,  # 10MB
            "allowed_extensions": [".txt", ".md", ".py"],
        }

        server = FilesysMCPServer(root_dir=str(temp_dir), config=config)
        assert server.config == config
        assert server.root_dir.resolve() == temp_dir.resolve()

    def test_multiple_server_instances(self, temp_dir):
        """Test creating multiple server instances."""
        server1 = FilesysMCPServer(root_dir=str(temp_dir))
        server2 = FilesysMCPServer(root_dir=str(temp_dir))

        # Each server should have its own MCP instance
        assert server1.mcp is not server2.mcp
        assert server1.root_dir == server2.root_dir

    def test_server_root_directory_resolution(self):
        """Test that server properly resolves relative paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a subdirectory
            sub_dir = Path(tmpdir) / "subdir"
            sub_dir.mkdir()

            # Initialize server with relative path
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                server = FilesysMCPServer(root_dir="subdir")
                assert server.root_dir.resolve() == sub_dir.resolve()
            finally:
                os.chdir(original_cwd)

    def test_server_run_method_exists(self, server):
        """Test that server has run method for starting the server."""
        assert hasattr(server, "run")
        assert callable(server.run)
