"""Tool registry for filesystem MCP server."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    """Represents a filesystem tool."""

    name: str
    description: str
    handler: Callable
    parameters: dict[str, Any]


class ToolRegistry:
    """Registry for filesystem tools."""

    def __init__(self):
        """Initialize the tool registry."""
        self._tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable,
        parameters: dict[str, Any],
    ) -> None:
        """Register a new tool.

        Args:
            name: Tool name
            description: Tool description
            handler: Tool handler function
            parameters: Tool parameters schema
        """
        self._tools[name] = Tool(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters,
        )

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool if found, None otherwise
        """
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """List all registered tools.

        Returns:
            List of registered tools
        """
        return list(self._tools.values())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: Tool name

        Returns:
            True if tool is registered, False otherwise
        """
        return name in self._tools
