#!/usr/bin/env bash
'exec "$(dirname "$0")/../scripts/ami-run.sh" "$(dirname "$0")/run_filesys.py" "$@" #'

"""Runner script for Filesys MCP server."""

# Standard library imports FIRST
import argparse
import sys
from pathlib import Path

# Bootstrap sys.path - MUST come before base imports
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))

# Now we can import from base
from base.backend.utils.runner_bootstrap import ensure_module_venv  # noqa: E402
from files.backend.mcp.filesys.filesys_server import FilesysFastMCPServer  # noqa: E402


def main() -> None:
    """Run the Filesys MCP server."""
    ensure_module_venv(Path(__file__))

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
