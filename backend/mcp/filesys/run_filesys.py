#!/usr/bin/env python
"""Run Files MCP server."""

import asyncio
from pathlib import Path

# Use standard import setup
from base.backend.utils.standard_imports import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from base.backend.utils.module_setup import ModuleSetup  # noqa: E402

ModuleSetup.ensure_running_in_venv(Path(__file__))

# Now import the server components
from base.scripts.run_mcp_server import run_stdio  # noqa: E402
from files.backend.mcp.filesys.server import FilesysMCPServer  # noqa: E402


async def main():
    """Run the Files MCP server."""
    # Get config file if exists
    config_file = None
    for name in ["files_config.yaml", "config.yaml"]:
        path = MODULE_ROOT / name
        if path.exists():
            config_file = str(path)
            break

    server_args = {"config_file": config_file} if config_file else {}

    # Run the server
    await run_stdio(FilesysMCPServer, server_args)


if __name__ == "__main__":
    asyncio.run(main())
