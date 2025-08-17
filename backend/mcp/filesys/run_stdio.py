"""Run filesystem MCP server with stdio transport."""

import argparse
import asyncio
import sys
from pathlib import Path

# Smart path discovery - find project roots by looking for .git/.venv
current = Path(__file__).resolve().parent
while current != current.parent:
    # Found main orchestrator (has base/ and .git)
    if (current / "base").exists() and (current / ".git").exists():
        sys.path.insert(0, str(current))
        sys.path.insert(0, str(current / "base"))
        break
    # Found module root (has .venv or .git and backend/)
    if ((current / ".venv").exists() or (current / ".git").exists()) and (
        current / "backend"
    ).exists():
        if str(current) not in sys.path:
            sys.path.insert(0, str(current))
    current = current.parent

from loguru import logger  # noqa: E402

from backend.mcp.filesys.server import FilesysMCPServer  # noqa: E402

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
    except (OSError, RuntimeError, ValueError) as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
