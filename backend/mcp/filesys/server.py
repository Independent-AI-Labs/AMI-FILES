"""Filesystem MCP Server - Provides file manipulation tools via MCP protocol."""

import sys
from pathlib import Path
from typing import Any

from loguru import logger

# Add parent directory to path for base module imports if needed
_parent_dir = Path(__file__).parent.parent.parent.parent.parent
if _parent_dir.exists() and str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from base.backend.mcp.mcp_server import BaseMCPServer  # noqa: E402

from backend.mcp.filesys.tools.definitions import register_all_tools  # noqa: E402
from backend.mcp.filesys.tools.executor import ToolExecutor  # noqa: E402
from backend.mcp.filesys.tools.registry import ToolRegistry  # noqa: E402


class FilesysMCPServer(BaseMCPServer):
    """MCP server for filesystem operations - provides file manipulation tools."""

    def __init__(self, root_dir: str | None = None, config: dict | None = None):
        """Initialize Filesystem MCP server.

        Args:
            root_dir: Root directory for file operations (defaults to current directory)
            config: Server configuration (including response_format: 'json' or 'yaml')
        """
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()
        self.response_format = (
            config.get("response_format", "json") if config else "json"
        )

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
            Tool execution result (formatted as JSON or YAML based on config)
        """
        # Execute using the tool executor
        result = await self.executor.execute(tool_name, arguments)

        # Format response based on configuration
        if self.response_format == "yaml" and not result.get("error"):
            # Convert result to YAML format for better readability
            try:
                # For certain tools, format the output specially
                if tool_name == "read_from_file" and "content" in result:
                    # Keep content as-is for readability
                    yaml_result = {
                        "path": result.get("path"),
                        "encoding": result.get("encoding"),
                        "format": result.get("format"),
                        "content": result.get("content"),  # Content with line numbers
                    }
                    return yaml_result

                # For other tools, just return as-is (will be serialized by transport)
                return result
            except Exception as e:
                logger.warning(f"Failed to format as YAML: {e}, returning JSON")
                return result

        return result
