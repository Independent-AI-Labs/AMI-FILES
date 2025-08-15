"""Run filesystem MCP server with stdio transport."""

import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger

from backend.mcp.filesys.server import FilesysMCPServer

# Configure logging
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="INFO")


async def main():
    """Main entry point for stdio server."""
    parser = argparse.ArgumentParser(description="Filesystem MCP Server (stdio)")
    parser.add_argument(
        "--root-dir",
        type=str,
        default=str(Path.cwd()),
        help="Root directory for file operations (default: current directory)",
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=100 * 1024 * 1024,
        help="Maximum file size in bytes (default: 100MB)",
    )
    args = parser.parse_args()

    # Create and run server
    try:
        server = FilesysMCPServer(root_dir=args.root_dir)
        logger.info(
            f"Starting Filesystem MCP server (stdio) with root: {args.root_dir}"
        )
        await server.run_stdio()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
