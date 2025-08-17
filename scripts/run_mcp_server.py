#!/usr/bin/env python
"""Files MCP Server wrapper - uses base logic for .venv management."""
# mypy: ignore-errors

import sys
from pathlib import Path

# Find project roots
SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

# Find main repository root (has base/ and .git)
MAIN_ROOT = None
current = SCRIPT_DIR
while current != current.parent:
    if (current / "base").exists() and (current / ".git").exists():
        MAIN_ROOT = current
        break
    current = current.parent

if not MAIN_ROOT:
    print("ERROR: Could not find main repository root (with base/ directory)")
    sys.exit(1)

# Find files module root
PROJECT_ROOT = SCRIPT_DIR.parent
current = SCRIPT_DIR
while current != current.parent:
    if (current / "backend" / "mcp" / "filesys").exists():
        PROJECT_ROOT = current
        break
    current = current.parent

# Add base to path so we can import the base MCP launcher
BASE_PATH = MAIN_ROOT / "base"
if str(BASE_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_PATH))

# Import the base MCP launcher
try:
    from scripts.start_mcp_server import main as start_mcp_main
except ImportError as e:
    print(f"ERROR: Could not import base start_mcp_server: {e}")
    sys.exit(1)


def main():
    """Run MCP server for the files module."""
    mcp_base_path = PROJECT_ROOT / "backend" / "mcp" / "filesys"

    return start_mcp_main(
        project_root=PROJECT_ROOT,
        mcp_base_path=str(mcp_base_path),
        project_name="Files MCP Server",
    )


if __name__ == "__main__":
    sys.exit(main())
