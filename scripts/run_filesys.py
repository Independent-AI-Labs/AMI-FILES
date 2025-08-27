#!/usr/bin/env python
"""Run Filesys MCP server with stdio/websocket support."""

import asyncio
import sys
from pathlib import Path

# Get module root
MODULE_ROOT = Path(__file__).resolve().parent.parent

# Add files and parent (for base imports) to path
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))

from base.backend.mcp.mcp_runner import MCPRunner  # noqa: E402

from backend.mcp.filesys.server import FilesysMCPServer  # noqa: E402


async def main():
    """Run the Filesys MCP server."""
    runner = MCPRunner(
        server_class=FilesysMCPServer,
        server_name="Filesys",
        config_files=["filesys_config.yaml", "config.yaml"],
        extra_args={
            "--root-dir": {
                "type": str,
                "help": "Root directory for file operations",
                "default": None,
            }
        },
    )
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
