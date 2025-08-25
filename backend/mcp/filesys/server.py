"""Filesystem MCP Server - Provides file manipulation tools via MCP protocol."""

import sys
from pathlib import Path
from typing import Any

from loguru import logger

# STANDARD IMPORT SETUP - DO NOT MODIFY
current_file = Path(__file__).resolve()
orchestrator_root = current_file
while orchestrator_root != orchestrator_root.parent:
    if (orchestrator_root / ".git").exists() and (orchestrator_root / "base").exists():
        break
    orchestrator_root = orchestrator_root.parent
else:
    raise RuntimeError(f"Could not find orchestrator root from {current_file}")

if str(orchestrator_root) not in sys.path:
    sys.path.insert(0, str(orchestrator_root))

module_names = {"base", "browser", "files", "compliance", "domains", "streams"}
module_root = current_file.parent
while module_root != orchestrator_root:
    if module_root.name in module_names:
        if str(module_root) not in sys.path:
            sys.path.insert(0, str(module_root))
        break
    module_root = module_root.parent

from base.backend.mcp.mcp_server import BaseMCPServer  # noqa: E402
from files.backend.mcp.filesys.tools.definitions import register_all_tools  # noqa: E402
from files.backend.mcp.filesys.tools.executor import ToolExecutor  # noqa: E402
from files.backend.mcp.filesys.tools.registry import ToolRegistry  # noqa: E402


class FilesysMCPServer(BaseMCPServer):
    """MCP server for filesystem operations - provides file manipulation tools."""

    def __init__(self, root_dir: str | None = None, config: dict | None = None):
        """Initialize Filesystem MCP server.

        Args:
            root_dir: Root directory for file operations (defaults to current directory)
            config: Server configuration (including response_format: 'json' or 'yaml')
        """
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()

        # Ensure root directory exists and is absolute
        try:
            self.root_dir = self.root_dir.resolve(strict=True)
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Root directory does not exist: {root_dir}") from e

        if not self.root_dir.is_dir():
            raise ValueError(f"Root path is not a directory: {self.root_dir}")

        # Initialize tool registry and executor for execution
        self.registry = ToolRegistry()
        register_all_tools(self.registry)
        self.executor = ToolExecutor(self.root_dir)

        # Initialize base with config
        super().__init__(config)

        logger.info(f"Filesystem MCP server initialized with root: {self.root_dir}")
        logger.info(f"Registered {len(self.tools)} filesystem tools")

    def register_tools(self) -> None:
        """Register all filesystem tools."""
        # Convert tool registry to MCP format
        for tool in self.registry.list_tools():
            self.tools[tool.name] = {
                "description": tool.description,
                "inputSchema": {
                    "type": "object",
                    "properties": tool.parameters.get("properties", {}),
                    "required": tool.parameters.get("required", []),
                },
            }

    async def execute_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a filesystem tool.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        # Execute using the tool executor
        result = await self.executor.execute(tool_name, arguments)
        return dict(result) if result else {}
