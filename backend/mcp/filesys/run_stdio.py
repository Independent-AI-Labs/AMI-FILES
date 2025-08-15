"""Run filesystem MCP server with stdio transport."""

import argparse
import asyncio
import sys
from pathlib import Path

# Smart path setup - works regardless of where script is run from
_current_file = Path(__file__).resolve()
_current_dir = _current_file.parent

# Find git root by traversing up
_search_dir = _current_dir
while _search_dir != _search_dir.parent:
    if (_search_dir / ".git").exists():
        # Add git root and base module to path
        sys.path.insert(0, str(_search_dir))
        if (_search_dir / "base").exists():
            sys.path.insert(0, str(_search_dir / "base"))
        break
    _search_dir = _search_dir.parent

# Find project root (files directory)
_project_root = _current_dir
while _project_root != _project_root.parent:
    if (_project_root / "backend" / "mcp" / "filesys").exists():
        sys.path.insert(0, str(_project_root))
        break
    _project_root = _project_root.parent

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
