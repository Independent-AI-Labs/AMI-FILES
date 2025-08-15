#!/usr/bin/env python
"""Test runner for files module."""

import sys
from pathlib import Path

# Add base scripts to path
base_scripts = Path(__file__).parent.parent.parent / "base" / "scripts"
if base_scripts.exists():
    sys.path.insert(0, str(base_scripts))
    from run_tests import main  # type: ignore[attr-defined]
else:
    print("ERROR: Cannot find base/scripts directory")
    sys.exit(1)


if __name__ == "__main__":
    # Use the base test runner with files module root
    project_root = Path(__file__).parent.parent
    sys.exit(main(project_root, "Files Module"))
