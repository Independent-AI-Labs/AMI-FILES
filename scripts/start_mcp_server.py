#!/usr/bin/env python
"""Files MCP Server wrapper using the generic base MCP launcher."""

import os
import sys
from pathlib import Path

# Smart path setup - works from ANYWHERE
SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

# Find the main git root by looking for base/ directory
# This handles both submodules and main repo
MAIN_ROOT = None
current = SCRIPT_DIR

while current != current.parent:
    # The main repo has base/ directory at its root
    if (current / "base").exists() and (current / ".git").exists():
        MAIN_ROOT = current
        break
    current = current.parent

if not MAIN_ROOT:
    print("ERROR: Could not find main repository root (with base/ directory)")
    print(f"Started search from: {SCRIPT_DIR}")
    sys.exit(1)

print(f"Found main repository at: {MAIN_ROOT}")

# Determine project root (files directory)
# Start from script directory and go up until we find backend/mcp/filesys
PROJECT_ROOT = SCRIPT_DIR.parent  # Default: parent of scripts/
current = SCRIPT_DIR
while current != current.parent:
    if (current / "backend" / "mcp" / "filesys").exists():
        PROJECT_ROOT = current
        break
    current = current.parent

print(f"Project root (files): {PROJECT_ROOT}")

# Change working directory to project root
os.chdir(PROJECT_ROOT)
print(f"Working directory set to: {PROJECT_ROOT}")

# Set up Python paths
# 1. Project root first (to avoid namespace collisions)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"Added to path: {PROJECT_ROOT}")

# 2. Main repository root
if str(MAIN_ROOT) not in sys.path:
    sys.path.insert(1, str(MAIN_ROOT))
    print(f"Added to path: {MAIN_ROOT}")

# 3. Base module
BASE_PATH = MAIN_ROOT / "base"
if BASE_PATH.exists() and str(BASE_PATH) not in sys.path:
    sys.path.insert(1, str(BASE_PATH))
    print(f"Added to path: {BASE_PATH}")

# 4. Base scripts for the generic launcher
BASE_SCRIPTS_PATH = BASE_PATH / "scripts"
if BASE_SCRIPTS_PATH.exists():
    if str(BASE_SCRIPTS_PATH) not in sys.path:
        sys.path.insert(0, str(BASE_SCRIPTS_PATH))
    print(f"Using base scripts from: {BASE_SCRIPTS_PATH}")
else:
    print(f"ERROR: Base scripts not found at {BASE_SCRIPTS_PATH}")
    sys.exit(1)

# Import the generic MCP launcher
try:
    from start_mcp_server import main as start_mcp_main
except ImportError as e:
    print(f"ERROR: Could not import start_mcp_server: {e}")
    print(f"Looked in: {BASE_SCRIPTS_PATH}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)


def main():
    """Run MCP server for the files module."""
    # The MCP scripts are in backend/mcp/filesys/
    mcp_base_path = PROJECT_ROOT / "backend" / "mcp" / "filesys"

    return start_mcp_main(  # type: ignore[call-arg]
        project_root=PROJECT_ROOT,
        mcp_base_path=str(mcp_base_path),
        project_name="AMI-FILES MCP Server",
    )


if __name__ == "__main__":
    sys.exit(main())
