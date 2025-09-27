# AMI Files Module

The Files module exposes governed filesystem operations, git workflows, document extraction, and lightweight Python execution through a FastMCP server. It is designed for agent-driven automation while keeping repository state auditable.

## Capabilities

### Filesystem Tools
- `list_dir`, `find_paths`, `create_dirs`, `read_from_file`, `write_to_file`, `modify_file`, `replace_in_file`, `delete_paths`.
- Path validation (`validate_path`) prevents access outside the configured root (no writes into `.git`, sibling modules, or `.venv`).

### Git Workflows
- `git_status`, `git_stage`, `git_unstage`, `git_commit`, `git_restore`, `git_diff`, `git_history`, `git_fetch`, `git_pull`, `git_push`, `git_merge_abort`.
- Commands run inside the sandbox root so agent actions follow the same controls as human contributors.

### Python Task Runner
- `python_run`, `python_run_background`, `python_task_status`, `python_task_cancel`, `python_list_tasks` allow short-lived scripts and background jobs.
- Execution state is tracked in-memory; tasks can be queried or cancelled by id.

### Document & Image Extraction
- `index_document`, `read_document` support PDFs, Word, spreadsheets via extractors under `backend/extractors/`.
- `read_image` wraps OCR/Gemini-assisted analysis when `GEMINI_API_KEY` is available; gracefully degrades without credentials.

All tools return structured responses (status, payload, error messages) so callers can attach results to compliance evidence.

## Running the FastMCP Server

```bash
# StdIO transport
uv run --python 3.12 --project files python scripts/run_filesys_fastmcp.py --root <path>

# Streamable HTTP transport (for web clients)
uv run --python 3.12 --project files python scripts/run_filesys_fastmcp.py --transport streamable-http --port 8787
```

`--root` defaults to the current working directory; set it explicitly for production deployments.

## Tests

```bash
uv run --python 3.12 --project files python scripts/run_tests.py
```

Tests cover path validation, git workflows, extractors, and MCP tool wiring. Some extraction tests require libreoffice/ghostscript; they skip automatically if dependencies are absent.

## Environment & Setup

- `module_setup.py` delegates to Base `EnvironmentSetup`; run `uv run --python 3.12 python module_setup.py` from the repository root or `uv run --project files python module_setup.py` from inside the module.
- `default.env` documents required environment variables (Git author, Gemini API key, etc.).
- `config/settings.yaml` holds default extractor behaviour; override via env variables mirroring the consolidated compliance docs.

## Compliance Hooks

- Mutating tools should log to the Base audit trail once the compliance backend is implemented. The current implementation logs at INFO level via `loguru`; map these events to `audit_log` as part of the compliance server work.
- MCP tool schemas align with the consolidated requirements in `compliance/docs/consolidated`; reference those docs when extending capabilities.

## Roadmap

1. Wire audit logging + evidence export into the forthcoming compliance MCP server.
2. Persist extraction results using Base DataOps once the compliance backend adds evidence storage.
3. Expand document/image tests with golden fixtures when Gemini support is toggled on.
