#!/usr/bin/env python
"""Files module test runner - uses base test runner."""

import os
import sys
from pathlib import Path

# Set working directory to files module root
MODULE_ROOT = Path(__file__).resolve().parent.parent
os.chdir(MODULE_ROOT)

# Find and import base test runner
current = MODULE_ROOT.parent
if (current / "base").exists():
    sys.path.insert(0, str(current / "base" / "scripts"))
else:
    print("ERROR: Cannot find base module")
    sys.exit(1)

from run_tests import main as base_main  # noqa: E402


def main():
    """Run tests for files module."""
    return base_main(project_root=MODULE_ROOT, project_name="Files Module")  # type: ignore[call-arg]


if __name__ == "__main__":
    sys.exit(main())
