#!/usr/bin/env python
"""Runner script for Filesys MCP server."""

import argparse
import sys
from pathlib import Path


def _ensure_repo_on_path() -> None:
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists() and (current / "base").exists():
            sys.path.insert(0, str(current))
            return
        current = current.parent


def main() -> None:
    """Run the Filesys MCP server."""

    _ensure_repo_on_path()

    from base.backend.utils.runner_bootstrap import ensure_module_venv  # noqa: PLC0415

    ensure_module_venv(Path(__file__))

    from files.backend.mcp.filesys.filesys_server import FilesysFastMCPServer  # noqa: PLC0415

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
