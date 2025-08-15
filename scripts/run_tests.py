#!/usr/bin/env python
"""Test runner for files module."""

import sys
from pathlib import Path

# Smart path setup - find git root regardless of where we're run from
SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

# Find git root by traversing up
GIT_ROOT = None
current = SCRIPT_DIR
while current != current.parent:
    if (current / ".git").exists():
        GIT_ROOT = current
        break
    current = current.parent

if not GIT_ROOT:
    print("ERROR: Could not find git repository root")
    sys.exit(1)

# Add base scripts to path
base_scripts = GIT_ROOT / "base" / "scripts"
if base_scripts.exists():
    sys.path.insert(0, str(base_scripts))
    from run_tests import main  # type: ignore[attr-defined]
else:
    print(f"ERROR: Cannot find base/scripts directory at {base_scripts}")
    sys.exit(1)


if __name__ == "__main__":
    # Use the base test runner with files module root
    project_root = Path(__file__).parent.parent
    sys.exit(main(project_root, "Files Module"))
