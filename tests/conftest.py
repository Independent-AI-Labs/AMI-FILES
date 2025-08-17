"""Pytest configuration for files module tests."""

import sys
from pathlib import Path

# Add orchestrator root to path for proper imports
current = Path(__file__).resolve().parent
while current != current.parent:
    if (current / ".git").exists() and (current / "base").exists():
        # Found the main orchestrator root
        sys.path.insert(0, str(current))
        break
    current = current.parent
