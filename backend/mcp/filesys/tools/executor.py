"""Tool executor for filesystem MCP server."""

from pathlib import Path
from typing import Any

from loguru import logger

from .git_handlers import (
    git_commit,
    git_diff,
    git_fetch,
    git_history,
    git_merge_abort,
    git_pull,
    git_push,
    git_restore,
    git_stage,
    git_unstage,
)
from .handlers import (
    create_dirs,
    delete_paths,
    find_paths,
    list_dir,
    modify_file,
    read_from_file,
    replace_in_file,
    write_to_file,
)


class ToolExecutor:
    """Executes filesystem tools."""

    def __init__(self, root_dir: Path):
        """Initialize the tool executor.

        Args:
            root_dir: Root directory for file operations
        """
        self.root_dir = root_dir

        # Map tool names to handlers
        self.handlers = {
            # Filesystem tools
            "list_dir": list_dir,
            "create_dirs": create_dirs,
            "find_paths": find_paths,
            "read_from_file": read_from_file,
            "write_to_file": write_to_file,
            "delete_paths": delete_paths,
            "modify_file": modify_file,
            "replace_in_file": replace_in_file,
            # Git tools
            "git_stage": git_stage,
            "git_unstage": git_unstage,
            "git_commit": git_commit,
            "git_diff": git_diff,
            "git_history": git_history,
            "git_restore": git_restore,
            "git_fetch": git_fetch,
            "git_pull": git_pull,
            "git_push": git_push,
            "git_merge_abort": git_merge_abort,
        }

    async def execute(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a tool with given arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if tool_name not in self.handlers:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            # Get the handler
            handler = self.handlers[tool_name]

            # Add root_dir to arguments for all handlers
            result = await handler(self.root_dir, **arguments)  # type: ignore[operator]

            # Ensure we return a proper result structure
            if "error" in result:
                logger.error(f"Tool {tool_name} failed: {result['error']}")
                return {"error": result["error"]}
            if "result" in result:
                return result["result"]  # type: ignore[no-any-return]
            return result  # type: ignore[no-any-return]

        except TypeError as e:
            logger.error(f"Invalid arguments for tool {tool_name}: {e}")
            return {"error": f"Invalid arguments: {e!s}"}
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return {"error": f"Execution failed: {e!s}"}
