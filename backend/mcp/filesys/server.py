"""Filesystem MCP Server - Provides file manipulation tools via MCP protocol."""

from pathlib import Path

# Use standard import setup
from base.backend.utils.standard_imports import setup_imports
from loguru import logger

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()


from base.backend.mcp.server_base import StandardMCPServer  # noqa: E402
from files.backend.mcp.filesys.tools.executor import ToolExecutor  # noqa: E402
from files.backend.mcp.filesys.tools.registry import ToolRegistry  # noqa: E402


class FilesysMCPServer(StandardMCPServer[ToolRegistry, ToolExecutor]):
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

        # Pass root_dir to parent for executor initialization
        super().__init__(config, root_dir=self.root_dir)

        logger.info(f"Filesystem MCP server initialized with root: {self.root_dir}")
        logger.info(f"Registered {len(self.tools)} filesystem tools")

    def get_registry_class(self):
        """Get the tool registry class."""
        return ToolRegistry

    def get_executor_class(self):
        """Get the tool executor class."""
        return ToolExecutor

    def register_tools_to_registry(self, registry: ToolRegistry) -> None:
        """Register filesystem tools to the registry."""
        from files.backend.mcp.filesys.tools.definitions import register_all_tools

        register_all_tools(registry)

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

    # execute_tool is inherited from StandardMCPServer
