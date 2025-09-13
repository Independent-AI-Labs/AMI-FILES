#!/usr/bin/env python
"""Test runner for files module."""

import sys
from pathlib import Path

from base.scripts.run_tests import main

# Get module root
MODULE_ROOT = Path(__file__).resolve().parent.parent

# Add files and base to path (base imported as 'base')
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))

# Import from base using proper base. prefix

if __name__ == "__main__":
    # Run tests using base test runner with files module root
    sys.exit(main(project_root=MODULE_ROOT, project_name="Files"))
