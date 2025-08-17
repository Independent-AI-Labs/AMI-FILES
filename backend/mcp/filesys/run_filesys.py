#!/usr/bin/env python
"""Run Filesystem MCP server."""

import sys
from pathlib import Path

# Bootstrap path discovery - find ORCHESTRATOR ROOT (parent with base/ submodule)
current = Path(__file__).resolve().parent
orchestrator_root = None
while current != current.parent:
    if (current / ".git").exists() and (current / "base").exists():
        # Found the main orchestrator root
        orchestrator_root = current
        break
    current = current.parent

if not orchestrator_root:
    raise RuntimeError("Could not find orchestrator root")

# Add orchestrator root to path FIRST so we can import both base and local modules properly
sys.path.insert(0, str(orchestrator_root))

# Now import from base using proper namespace
from base.backend.utils.path_finder import setup_base_import  # noqa: E402

setup_base_import(Path(__file__))

from base.backend.mcp.run_server import setup_environment  # noqa: E402

if __name__ == "__main__":
    # Setup environment first (will re-exec if needed)
    module_root, python = setup_environment(Path(__file__))

    # Ensure module root is FIRST in sys.path
    module_str = str(module_root)
    if module_str in sys.path:
        sys.path.remove(module_str)
    sys.path.insert(0, module_str)

    # NOW import after environment is set up
    import argparse
    import asyncio

    from base.backend.mcp.run_server import run_stdio, run_websocket

    # Import the filesys server from THIS module (files)
    # Since orchestrator root is in path, we can use files.backend
    from files.backend.mcp.filesys.server import FilesysMCPServer

    # Parse args
    parser = argparse.ArgumentParser(description="Filesystem MCP Server")
    parser.add_argument(
        "transport", nargs="?", default="stdio", choices=["stdio", "websocket", "ws"]
    )
    parser.add_argument(
        "--root-dir", default=str(Path.cwd()), help="Root directory for file operations"
    )
    args = parser.parse_args()

    transport = "websocket" if args.transport in ["websocket", "ws"] else "stdio"
    server_args = {"root_dir": args.root_dir}

    # Run the appropriate transport
    if transport == "stdio":
        asyncio.run(run_stdio(FilesysMCPServer, server_args))
    else:
        asyncio.run(run_websocket(FilesysMCPServer, server_args, port=8768))
