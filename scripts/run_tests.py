#!/usr/bin/env python
"""Test runner for files module."""

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

# Add base scripts to path
base_scripts = MAIN_ROOT / "base" / "scripts"
if base_scripts.exists():
    sys.path.insert(0, str(base_scripts))
    print(f"Using base scripts from: {base_scripts}")
    from run_tests import main  # type: ignore[attr-defined]
else:
    print(f"ERROR: Cannot find base/scripts directory at {base_scripts}")
    sys.exit(1)


if __name__ == "__main__":
    # Use the base test runner with files module root
    project_root = SCRIPT_DIR.parent  # Parent of scripts/ is files/
    sys.exit(main(project_root, "Files Module"))
