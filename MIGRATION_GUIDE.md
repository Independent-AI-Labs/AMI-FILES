# Files Module Migration Guide - Import System Changes

**Date:** 2025-09-02  
**Breaking Change:** Import system overhaul to absolute imports

## Overview

The files module has undergone a complete import system overhaul to improve reliability, prevent circular imports, and provide consistent module resolution across all execution contexts.

## What Changed

### 1. Import Pattern Changes

All relative imports have been converted to absolute imports with the `files.backend` prefix.

**Before:**
```python
# Relative imports (deprecated)
from .base import DocumentExtractor
from .docx_extractor import DOCXExtractor
from ..tools.filesystem_tools import list_dir_tool
from ...utils.file_utils import FileUtils
```

**After:**
```python
# Absolute imports with files prefix
from files.backend.extractors.base import DocumentExtractor
from files.backend.extractors.docx_extractor import DOCXExtractor
from files.backend.mcp.filesys.tools.filesystem_tools import list_dir_tool
from files.backend.mcp.filesys.utils.file_utils import FileUtils
```

### 2. Configuration System

Added centralized configuration system with YAML-based settings:

**New:** `backend/config/settings.yaml`
```yaml
precommit:
  timeouts:
    version_check: 5
    validation_run: 30
  file_limits:
    max_file_size_kb: 1024

file_utils:
  limits:
    max_file_size: 104857600  # 100MB

python_tools:
  timeouts:
    worker_acquire: 30
    execution_default: 300
  workers:
    min_workers: 1
    max_workers: 5
```

Access configuration via:
```python
from files.backend.config import files_config

timeout = files_config.get_precommit_timeout("validation_run")
max_size = files_config.get_file_utils_config()["limits"]["max_file_size"]
```

### 3. Entry Point Script Changes

Entry point scripts now use proper path setup:

**Before:**
```python
from backend.mcp.filesys.server import FilesysMCPServer
```

**After:**
```python
from pathlib import Path
import sys

# Path setup required for entry points
MODULE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))

from files.backend.mcp.filesys.filesys_server import FilesysFastMCPServer
```

## Migration Steps

### Step 1: Update Import Statements

Replace all relative imports in your code:

```bash
# Find all Python files with relative imports
find . -name "*.py" -exec grep -l "from \." {} \;

# Convert patterns:
# from .module -> from files.backend.path.module
# from ..module -> from files.backend.path.module
# from ...module -> from files.backend.path.module
```

### Step 2: Update Entry Points

If you have custom entry point scripts:

1. Add proper path setup at the top
2. Convert imports to absolute paths
3. Use `FilesysFastMCPServer` instead of `FilesysMCPServer`

### Step 3: Update API Usage

Update any external code that imports from the files module:

**Before:**
```python
from backend.extractors import PDFExtractor
from backend.mcp.filesys.server import FilesysMCPServer
```

**After:**
```python
from files.backend.extractors.pdf_extractor import PDFExtractor
from files.backend.mcp.filesys.filesys_server import FilesysFastMCPServer
```

### Step 4: Update Configuration Usage

If you were using hardcoded values, migrate to the configuration system:

**Before:**
```python
TIMEOUT = 30  # Hardcoded
MAX_FILE_SIZE = 100 * 1024 * 1024  # Hardcoded
```

**After:**
```python
from files.backend.config import files_config

timeout = files_config.get_precommit_timeout("validation_run")
max_size = files_config.get_file_utils_config()["limits"]["max_file_size"]
```

## Files Affected

The following files were modified in this change:

### Core Configuration
- `backend/config/__init__.py` (new)
- `backend/config/loader.py` (new)
- `backend/config/settings.yaml` (new)

### Extractors
- `backend/extractors/__init__.py`
- `backend/extractors/docx_extractor.py`
- `backend/extractors/image_extractor.py`
- `backend/extractors/pdf_extractor.py`
- `backend/extractors/spreadsheet_extractor.py`

### MCP Server
- `backend/mcp/filesys/filesys_server.py`
- `backend/mcp/filesys/tools/python_tools.py`
- `backend/mcp/filesys/utils/file_utils.py`
- `backend/mcp/filesys/utils/precommit_validator.py`

### Entry Points
- `scripts/run_filesys.py`
- `scripts/run_filesys_fastmcp.py`

## Validation

After migration, ensure:

1. All imports resolve correctly
2. Entry point scripts run without errors
3. Tests pass: `python scripts/run_tests.py`
4. Type checking passes: `mypy files/backend --config-file=files/mypy.ini`

## Benefits

This change provides:

1. **Consistent Import Resolution**: Works across all execution contexts
2. **Circular Import Prevention**: Absolute paths prevent import loops
3. **Better IDE Support**: IDEs can better resolve and navigate imports
4. **Centralized Configuration**: Single source of truth for settings
5. **Improved Maintainability**: Clear module boundaries and dependencies

## Troubleshooting

### Common Issues

**ImportError: No module named 'files'**
- Ensure `sys.path` includes the parent directory of the files module
- Check that you're using absolute imports with `files.` prefix

**Circular Import Errors**
- All previous circular imports should be resolved with absolute imports
- If you encounter new ones, check for incorrect import paths

**Configuration Not Found**
- Ensure `backend/config/settings.yaml` exists
- Check file permissions and YAML syntax

### Getting Help

1. Check the updated documentation in `README.md`
2. Review code examples for proper import patterns
3. Examine the entry point scripts for path setup patterns
4. Run tests to validate your changes

## Rollback

If you need to rollback temporarily:

```bash
git checkout HEAD~1 -- files/
```

However, this is not recommended as the old import system had reliability issues.