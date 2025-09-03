# CODE EXCEPTIONS - FILES MODULE

This file documents legitimate code patterns that might appear problematic but are actually necessary for the module's functionality.

## 1. Large File Sizes (Monitoring Required)

### Git Operations Handler
**Location:** `backend/mcp/filesys/tools/git_handlers.py` - 728 lines

**Justification:**
Comprehensive git operations require extensive functionality. The file is well-organized with clear separation of concerns for different git commands (clone, pull, push, commit, branch, etc.).

### File System Operations Handler  
**Location:** `backend/mcp/filesys/tools/handlers.py` - 581 lines

**Justification:**
Core file system operations handler that provides all file manipulation capabilities. Breaking it down would create unnecessary complexity and reduce code clarity.

## 2. Import Order Requirements

### Path Setup Required
**Location:** Entry point scripts (`scripts/run_filesys.py`, `scripts/run_filesys_fastmcp.py`)

**Justification:**
Entry point scripts must modify `sys.path` BEFORE importing local modules to ensure correct module resolution.

### Pattern:

```python
from pathlib import Path
import sys

# Add both files and base to Python path
MODULE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))  # For base imports

# Now safe to import with absolute paths
from files.backend.mcp.filesys.filesys_server import FilesysFastMCPServer
```

### Import Convention (BREAKING CHANGE 2025-09-02)
**All internal imports now use absolute paths with `files.backend` prefix**

**Justification:**
Ensures consistent import resolution across different execution contexts and prevents circular import issues.

### Examples:

```python
# Correct - Internal module imports
from files.backend.extractors.pdf_extractor import PDFExtractor
from files.backend.mcp.filesys.tools.filesystem_tools import list_dir_tool

# Correct - Cross-module imports  
from base.backend.utils.standard_imports import setup_imports

# Deprecated - Relative imports (no longer supported)
from .extractors import PDFExtractor
from ..tools import filesystem_tools
```

## 3. Type Ignores for Handler Execution

### Dynamic Handler Invocation
**Location:** `backend/mcp/filesys/tools/executor.py:87,94,95`

**Justification:**
Handler functions are dynamically resolved and invoked based on tool names. Type checking cannot statically verify these dynamic calls.

### Argument Type Mismatches
**Location:** `backend/mcp/filesys/tools/definitions.py:335`

**Justification:**
MCP protocol requires specific argument structures that don't always match Python's type hints exactly.

## Summary

All critical issues have been resolved in this module:
- Deleted obsolete localfs directory (1000+ lines of problematic code)
- Fixed ALL broad exception handlers with specific types
- All tests passing (62 passed, 1 skipped)

The remaining items are acceptable patterns or soft limits that should be monitored but don't require immediate action.