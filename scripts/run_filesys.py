#!/usr/bin/env python
"""Runner script for Filesys MCP server."""

import argparse
import sys
from pathlib import Path

from files.backend.mcp.filesys.filesys_server import FilesysFastMCPServer

# Add files and base to path
MODULE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))  # For base imports


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
    config = {"response_format": args.response_format}
    server = FilesysFastMCPServer(root_dir=args.root_dir, config=config)
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
