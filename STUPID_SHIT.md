# FILES MODULE - CODE ISSUES REPORT

## CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION

### 1. POLLING PATTERN
**Needs investigation:**
- **localfs/local_file_server.py:803** - `time.sleep(0.1)` for stream reading
  - Comment says "Avoid busy-waiting" but still uses sleep
  - Should investigate async stream reading alternatives

### 2. EXCEPTION HANDLING (CRITICAL)
**All need specific exception types and logging:**
- **localfs/file_utils.py:86,288,536,966** - 4 broad exception handlers
- **localfs/local_file_server.py:108,288,359,394,410,420,451,461,576,683,839** - 11 broad exception handlers

All are marked with `# pylint: disable=broad-exception-caught` which just suppresses the warning without fixing the issue.

### 3. LARGE FILES (SOFT LIMITS)
**Files approaching/exceeding limits:**
- **localfs/file_utils.py** - 998 lines (Should be split into logical modules)
- **localfs/local_file_server.py** - 841 lines (Should be split)
- **backend/mcp/filesys/tools/git_handlers.py** - 728 lines (Consider splitting git operations)
- **backend/mcp/filesys/tools/handlers.py** - 581 lines (Acceptable but monitor)
- **tests/unit/test_git_tools.py** - 508 lines (Test file, acceptable)

### 4. TYPE IGNORES
**Need investigation:**
- **backend/mcp/filesys/tools/executor.py:87,94,95** - Handler execution type issues
- **backend/mcp/filesys/tools/definitions.py:335** - Argument type mismatch
- **scripts/run_tests.py:11** - Import attribute issue

### 5. IMPORT ORDER
**Legitimate (path setup required):**
- **backend/mcp/filesys/server.py:14-18** - Must setup paths before imports

## PRIORITY FIXES

1. **CRITICAL:** Replace broad exception catching with specific exception types and proper logging
2. **HIGH:** Split file_utils.py and local_file_server.py into smaller, focused modules
3. **MEDIUM:** Investigate async alternatives to sleep-based stream reading
4. **LOW:** Review type ignores and add proper type annotations

## RECOMMENDATIONS
1. Create specific exception classes for file operations
2. Split file_utils.py into:
   - file_operations.py (basic CRUD)
   - file_search.py (search/filter operations)
   - file_metadata.py (metadata operations)
3. Split local_file_server.py into:
   - server_core.py (main server logic)
   - request_handlers.py (request processing)
   - stream_handlers.py (streaming operations)
4. Add structured logging with context for all exceptions
5. Consider using aiofiles for async file operations instead of sleep loops