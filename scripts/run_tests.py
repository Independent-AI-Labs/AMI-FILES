#!/usr/bin/env python
"""Test runner for files module."""

import sys
from pathlib import Path

# Add paths FIRST!
MODULE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))
sys.path.insert(0, str(MODULE_ROOT / "scripts"))

# Import ami_path
from ami_path import setup_ami_paths  # noqa: E402

ORCHESTRATOR_ROOT, MODULE_ROOT, MODULE_NAME = setup_ami_paths()

# NOW safe to import from anywhere
from base.scripts.run_tests import main  # noqa: E402

if __name__ == "__main__":
    # Run tests using base test runner with files module root
    sys.exit(main(project_root=MODULE_ROOT, project_name="Files"))
