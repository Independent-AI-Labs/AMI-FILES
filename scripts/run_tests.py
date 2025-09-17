#!/usr/bin/env python
"""Test runner for files module."""

import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))

from base.scripts.run_tests import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(project_root=MODULE_ROOT, project_name="Files"))
