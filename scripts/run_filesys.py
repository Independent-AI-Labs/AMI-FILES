#!/usr/bin/env python
"""Runner script for Filesys MCP server."""

import argparse
import importlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

MODULE_ROOT = Path(__file__).resolve().parent.parent

if TYPE_CHECKING:
    from files.backend.mcp.filesys.filesys_server import FilesysFastMCPServer


def configure_sys_path() -> None:
    """Ensure repository roots are on sys.path for dynamic imports."""

    for candidate in (MODULE_ROOT, MODULE_ROOT.parent):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


def load_server_class() -> type["FilesysFastMCPServer"]:
    """Import the Filesys FastMCP server after sys.path is ready."""

    configure_sys_path()
    module = importlib.import_module("files.backend.mcp.filesys.filesys_server")
    return cast("type[FilesysFastMCPServer]", module.FilesysFastMCPServer)


def main() -> None:
    """Run the Filesys MCP server."""

    parser = argparse.ArgumentParser(description="Filesys MCP Server")
    parser.add_argument(
        "--root-dir",
        type=str,
        default=".",
        help="Root directory for file operations",
    )
    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
        help="Transport type",
    )
    parser.add_argument(
        "--response-format",
        type=str,
        default="json",
        choices=["json", "yaml"],
        help="Response format",
    )

    args = parser.parse_args()

    # Create and run server
    server_class = load_server_class()
    config = {"response_format": args.response_format}
    server = server_class(root_dir=args.root_dir, config=config)
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
