#!/usr/bin/env python
"""Run Files MCP server."""

import asyncio
import sys
from pathlib import Path

# Find orchestrator root for proper imports
current = Path(__file__).resolve().parent
while current != current.parent:
    if (current / ".git").exists() and (current / "base").exists():
        orchestrator_root = current
        break
    current = current.parent
else:
    raise RuntimeError("Could not find orchestrator root")

# Add paths for imports
sys.path.insert(0, str(orchestrator_root))
sys.path.insert(0, str(orchestrator_root / "base"))

from backend.utils.path_utils import ModuleSetup  # noqa: E402

# Ensure we're running in the correct virtual environment
ModuleSetup.ensure_running_in_venv(Path(__file__))

# Add files module to path
module_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(module_root))

# Now import the server components
from base.scripts.run_mcp_server import run_stdio  # noqa: E402
from files.backend.mcp.filesys.server import FilesysMCPServer  # noqa: E402


async def main():
    """Run the Files MCP server."""
    # Get config file if exists
    config_file = None
    for name in ["files_config.yaml", "config.yaml"]:
        path = module_root / name
        if path.exists():
            config_file = str(path)
            break

    server_args = {"config_file": config_file} if config_file else {}

    # Run the server
    await run_stdio(FilesysMCPServer, server_args)


if __name__ == "__main__":
    asyncio.run(main())
