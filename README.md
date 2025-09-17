# AMI-FILES

AMI-FILES implements the orchestration layer's secure file tooling. The module exposes
filesystem, git, Python execution, and document analysis utilities via a FastMCP
server that is consumable by automations or other AMI modules. The codebase mirrors
the structure and guardrails used by `base` and `browser`, including path
sandboxes, pre-commit style validations, and shared logging patterns.

## Feature Surface

### Filesystem Operations
- `list_dir` - enumerate directories with optional globbing, recursion, and
  result limits.
- `create_dirs` - create one or more directories after sandbox validation.
- `find_paths` - combine fast keyword search with pattern matching inside the
  sandbox root.
- `read_from_file` - slice files with line/byte offsets, encoding transforms,
  and optional line numbering.
- `write_to_file` - write text or binary content after running the shared
  `PreCommitValidator` and size checks.
- `delete_paths` - remove files or directories recursively with protected-path
  enforcement.
- `modify_file` - replace precise line/byte regions with new content.
- `replace_in_file` - perform literal or regex text replacements.

### Git Operations
- `git_status`, `git_diff`, `git_history`, `git_restore` for local repository
  inspection and recovery.
- `git_stage`, `git_unstage`, `git_commit` for manipulating the index.
- `git_fetch`, `git_pull`, `git_push`, `git_merge_abort` for remote
  coordination. Parameters mirror the CLI flags allowed by the underlying
  helpers in `files.backend.mcp.filesys.tools.git_tools`.

### Python Execution
- `python_run` - execute scripts, modules, or inline code using either the
  module's virtualenv (`venv`) or the system interpreter. The helper enforces
  safe working directories and injects standard library imports for scripts
  executed via `runpy`.
- `python_run_background` plus `python_task_status`, `python_task_cancel`, and
  `python_list_tasks` - manage a cooperative background execution pool for
  longer-running scripts.

### Document & Image Analysis
- `index_document` and `read_document` route to extractor implementations for
  PDF, DOCX, XLSX/CSV, and plain text files. Output is returned as structured
  `Document*` models without persisting to storage (UnifiedCRUD integration is
  still pending).
- `read_image` provides OCR and high-level reasoning through the shared
  Gemini client when `GEMINI_API_KEY` is available. When no key is present, the
  tool gracefully returns metadata-only results.

## Document Pipeline Details
- Extractors live in `backend/extractors/` and share the
  `DocumentExtractor` interface defined in `base.py`.
- Models in `backend/models/document.py` describe the structured payloads that
  FastMCP responses return.
- Gemini access is brokered through `backend/services/gemini_client.py`, which
  centralises authentication, retries, and rate limiting.
- Persistence is intentionally omitted; callers are expected to manage storage
  until the UnifiedCRUD layer is reintroduced.

## Security & Compliance Guardrails
- All path arguments pass through `validate_path` in
  `backend/mcp/filesys/utils/path_utils.py`. Write/delete operations deny access
  to protected directories such as `.git`, `.venv`, cache folders, and the root
  of other AMI modules.
- `write_to_file`, `modify_file`, and `replace_in_file` invoke
  `PreCommitValidator` to run fast linting before mutating disk.
- File-size and binary checks inside `FileUtils` prevent accidental processing
  of excessively large artifacts.
- Log output uses `loguru` and `logging` consistently; exceptions are logged and
  re-surfaced to the caller.

## Configuration
- Set `GEMINI_API_KEY` to enable multimodal image analysis. Without the key the
  Gemini client skips remote calls and withholds Gemini-specific fields.
- Scripts default to the current working directory as the sandbox root. Override
  by instantiating `FilesysFastMCPServer(root_dir=...)` inside your runner.
- Module setup is delegated to `base/module_setup.py` via `module_setup.py`, so
  environment creation stays consistent across AMI modules.

## Command-Line Entrypoints
- `python module_setup.py` - provision the module venv via base tooling.
- `python scripts/run_filesys.py` - run the Filesys MCP server with stdio
  transport for local development.
- `python scripts/run_filesys_fastmcp.py` - launch the FastMCP server using the
  shared runner helpers.
- `python scripts/run_tests.py` - execute the module's tests (defaults to the
  full suite unless flags are provided).

When using `uv`, these can be invoked with `uv run --directory files ...` from
repo root.

## Directory Layout
```
backend/
  extractors/            # PDF, DOCX, spreadsheet, and image extractors
  models/                # Document dataclasses returned by MCP tools
  services/
    gemini_client.py     # Multimodal client wrapping Gemini
  mcp/filesys/
    filesys_server.py    # FastMCP server wiring
    tools/               # Tool implementations (filesystem, git, python, document)
    utils/               # Validation, fast search, and helper utilities
res/
  *_extensions.json      # File-type metadata consumed by extractors
scripts/                 # Local runners and maintenance commands
tests/                   # Unit and integration coverage for MCP tools
```

## Runtime Dependencies
Key libraries declared in `pyproject.toml` include:
- `mcp` for the FastMCP server surface
- `pyahocorasick` and `regex` for fast text search
- `PyMuPDF`, `python-docx`, `openpyxl`, `pandas`, and `Pillow` for document and
  spreadsheet parsing
- `aiohttp` for outbound HTTP calls (Gemini)
- `loguru` for structured logging

Development extras add `pytest`, `pytest-asyncio`, `ruff`, `mypy`, and
`pre-commit` to match the orchestrator-wide tooling expectations.

## Testing
```bash
# From repository root
uv run --directory files python3 scripts/run_tests.py

# Focus on FastMCP integration tests
uv run --directory files pytest tests/integration/test_filesys_fastmcp_server.py
```

## Open Work
- Wire document persistence through the shared UnifiedCRUD layer when available.
- Expand integration coverage for complex document extraction flows (large PDFs,
  image-heavy documents, Gemini-enabled analyses).
- Continue aligning this module's lint/type configurations with `base` and
  `browser` as those evolve.
