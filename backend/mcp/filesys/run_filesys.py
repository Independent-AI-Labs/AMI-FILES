#!/usr/bin/env python
"""Run Filesystem MCP server."""

import sys
from pathlib import Path

# Bootstrap path discovery - find base WITHOUT hardcoded parent counts
current = Path(__file__).resolve().parent
while current != current.parent:
    if (current / ".git").exists():
        if (current / "base").exists() and (
            current / "base" / "backend" / "utils" / "path_finder.py"
        ).exists():
            sys.path.insert(0, str(current / "base"))
            break
        elif (
            current.name == "base"
            and (current / "backend" / "utils" / "path_finder.py").exists()
        ):
            sys.path.insert(0, str(current))
            break
    current = current.parent

# Now we can import the proper path finder
from backend.utils.path_finder import setup_base_import  # noqa: E402

setup_base_import(Path(__file__))

from backend.mcp.run_server import setup_environment  # noqa: E402

if __name__ == "__main__":
    # Setup environment first (will re-exec if needed)
    module_root, python = setup_environment(Path(__file__))

    # Add files module root to sys.path for imports
    sys.path.insert(0, str(module_root))
    # Also add parent directory for the server.py import
    sys.path.insert(0, str(Path(__file__).parent))

    # NOW import after environment is set up
    import argparse

    from server import FilesysMCPServer

    from backend.mcp.run_server import run_server

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

    run_server(
        server_class=FilesysMCPServer,
        server_args={"root_dir": args.root_dir},
        transport=transport,
        port=8768,  # Files uses 8768
    )
