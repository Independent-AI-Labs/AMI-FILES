"""Tests for filesystem tool safety checks."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from files.backend.mcp.filesys.tools.filesystem_tools import (
    create_dirs_tool,
    delete_paths_tool,
)


class TestFilesystemTools:
    """Validate path sandbox behavior for filesystem tools."""

    @pytest.fixture
    def temp_root(self) -> Generator[Path, None, None]:
        """Provide an isolated root directory for filesystem operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_create_dirs_tool_blocks_protected_dirs(self, temp_root: Path) -> None:
        """Ensure protected directories cannot be created via the tool."""
        result = await create_dirs_tool(temp_root, [".git/hooks"])
        assert "error" in result
        assert "protected directory" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_delete_paths_tool_blocks_protected_dirs(self, temp_root: Path) -> None:
        """Ensure protected directories cannot be deleted via the tool."""
        protected = temp_root / ".venv"
        protected.mkdir()
        result = await delete_paths_tool(temp_root, [".venv"])
        assert "errors" in result
        assert any("protected directory" in err.lower() for err in result["errors"])
        assert protected.exists()
