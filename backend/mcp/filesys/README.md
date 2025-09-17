# Filesystem FastMCP Server

This package exposes the `FilesysFastMCPServer`, a FastMCP implementation that
powers the AMI-FILES module. It wires filesystem, git, Python execution, and
document tooling into a single server entry point while reusing the shared
safety utilities found under `backend/mcp/filesys/utils`.

## Registered Tool Families

### Filesystem
`list_dir`, `create_dirs`, `find_paths`, `read_from_file`, `write_to_file`,
`delete_paths`, `modify_file`, `replace_in_file`

### Git
`git_status`, `git_stage`, `git_unstage`, `git_commit`, `git_diff`,
`git_history`, `git_restore`, `git_fetch`, `git_pull`, `git_push`,
`git_merge_abort`

### Python Execution
`python_run`, `python_run_background`, `python_task_status`,
`python_task_cancel`, `python_list_tasks`

### Document & Image
`index_document`, `read_document`, `read_image`

Refer to `files.backend.mcp.filesys.tools.*` for argument details and return
payloads.

## Usage

```python
from files.backend.mcp.filesys.filesys_server import FilesysFastMCPServer

server = FilesysFastMCPServer(root_dir="/workspace")
server.run(transport="stdio")
```

- `root_dir` defaults to `Path.cwd()` and is validated on startup.
- Alternative transports supported by FastMCP (`sse`, `streamable-http`) can be
  passed via `run()`.

## Safeguards
- All tool calls validate paths through `validate_path`, blocking access to
  protected directories and enforcing the configured root.
- Mutating operations route through `PreCommitValidator` and `FileUtils` for
  size checks, binary detection, and lint-style feedback.
- Background Python tasks are tracked centrally so callers can inspect or cancel
  long-running work.

## Testing

```
uv run --directory files python3 scripts/run_tests.py
```

Unit and integration suites cover filesystem, git, python, and document flows,
including FastMCP wiring.
