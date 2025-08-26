#!/usr/bin/env python
"""Run Files MCP server."""

import asyncio
import sys
from pathlib import Path

# STANDARD IMPORT SETUP - DO NOT MODIFY
current_file = Path(__file__).resolve()
orchestrator_root = current_file
while orchestrator_root != orchestrator_root.parent:
    if (orchestrator_root / ".git").exists() and (orchestrator_root / "base").exists():
        break
    orchestrator_root = orchestrator_root.parent
else:
    raise RuntimeError(f"Could not find orchestrator root from {current_file}")

if str(orchestrator_root) not in sys.path:
    sys.path.insert(0, str(orchestrator_root))

module_names = {"base", "browser", "files", "compliance", "domains", "streams"}
module_root = current_file.parent
while module_root != orchestrator_root:
    if module_root.name in module_names:
        if str(module_root) not in sys.path:
            sys.path.insert(0, str(module_root))
        break
    module_root = module_root.parent

from base.backend.utils.module_setup import ModuleSetup  # noqa: E402

ModuleSetup.ensure_running_in_venv(Path(__file__))

MODULE_ROOT = module_root

# Now import the server components
import argparse  # noqa: E402
from typing import Any  # noqa: E402

import yaml  # noqa: E402
from files.backend.mcp.filesys.server import FilesysMCPServer  # noqa: E402


async def main():
    """Run the Files MCP server."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Filesys MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "websocket"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host for websocket server (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for websocket server (default: 8765)",
    )
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--root-dir", help="Root directory for file operations")
    args = parser.parse_args()

    # Get config file
    config_file = args.config
    if not config_file:
        for name in ["files_config.yaml", "config.yaml"]:
            path = MODULE_ROOT / name
            if path.exists():
                config_file = str(path)
                break

    config: dict[str, Any] = {}
    if config_file:
        with Path(config_file).open() as f:
            config = yaml.safe_load(f) or {}

    # Create and run the server
    root_dir = args.root_dir if args.root_dir else None
    server = FilesysMCPServer(root_dir=root_dir, config=config)

    if args.transport == "websocket":
        await server.run_websocket(args.host, args.port)
    else:
        await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
