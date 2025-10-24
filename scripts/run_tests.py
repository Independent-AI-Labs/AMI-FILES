#!/usr/bin/env python
"""Minimal test runner for modules without tests.

Exit codes:
  0 - No tests directory or all tests passed
  1 - Tests failed
"""

import logging
import subprocess
import sys
from pathlib import Path

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    """Run minimal test check."""
    # Find module root (where this script lives)
    script_dir = Path(__file__).resolve().parent
    module_root = script_dir.parent

    tests_dir = module_root / "tests"

    # No tests directory = success (nothing to test)
    if not tests_dir.exists():
        logger.info(f"No tests directory found at {tests_dir}")
        logger.info("✓ Module has no tests to run")
        return 0

    # Tests directory exists but is empty = success
    test_files = list(tests_dir.rglob("test_*.py"))
    if not test_files:
        logger.info(f"Tests directory exists at {tests_dir} but contains no test files")
        logger.info("✓ Module has no test files to run")
        return 0

    # Has tests - need pytest
    venv_python = module_root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        logger.error(f"ERROR: Virtual environment not found at {venv_python}")
        logger.error("Run: python module_setup.py")
        return 1

    # Run pytest
    logger.info(f"Running {len(test_files)} test file(s) in {tests_dir}")
    result = subprocess.run(
        [str(venv_python), "-m", "pytest", str(tests_dir), "-v"] + sys.argv[1:],
        check=False,
        cwd=module_root,
    )

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
