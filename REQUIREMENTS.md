# Files Module Requirements

This document captures the operative requirements for the current AMI-FILES
implementation. It supersedes older specifications that described UI surfaces or sync
engines that no longer exist in this module.

## Functional Scope

1. **Filesystem MCP Server**
   - Expose file inspection and mutation tools (`list_dir`, `find_paths`,
     `read_from_file`, `write_to_file`, `delete_paths`, `modify_file`,
     `replace_in_file`, `create_dirs`).
   - Enforce sandbox boundaries defined by the module root and the protected
     directory list in `backend/mcp/filesys/utils/path_utils.py`.

2. **Git Operations**
   - Surface local repository status, history, staging, commit, and restoration
     helpers.
   - Provide fetch/pull/push tooling that maps cleanly to the underlying git
     CLI while obeying the same sandbox constraints.

3. **Python Execution**
   - Allow scripted execution inside the module virtualenv or a caller-supplied
     interpreter, both in foreground and background modes.
   - Track background jobs so callers can check status, gather output snippets,
     and cancel work cooperatively.

4. **Document & Image Analysis**
   - Support PDF, DOCX, spreadsheet, plain text, and image extraction via
     specialized extractors.
   - Return structured models (`Document`, `DocumentSection`, `DocumentTable`,
     `DocumentImage`) in FastMCP responses.
   - Integrate optional Gemini-powered analysis when `GEMINI_API_KEY` is
     configured. Without a key the tools must still return extractor metadata.

## Non-Functional Requirements

- **Security**
  - Every disk mutation must run through `PreCommitValidator` and the shared file
    utility guards for size, encoding, and binary detection.
  - Background execution must reject scripts located outside the sandbox and
    must manage subprocess lifetime responsibly.

- **Observability**
  - Log with context using `loguru`/`logging`. Exceptions should surface as
    structured error payloads to MCP clients.
  - Provide timing/metadata fields in document responses to aid downstream
    monitoring.

- **Quality Gates**
  - Maintain parity with orchestrator-wide `ruff`, `mypy`, and `pre-commit`
    configurations.
  - Keep unit and integration tests green via `scripts/run_tests.py` and expand
    coverage alongside new tool features.

- **Extensibility**
  - New extractors should implement the `DocumentExtractor` protocol and slot
    into `_get_extractor` in `document_tools.py`.
  - Tool additions must register via `FilesysFastMCPServer._register_*` helpers
    to keep FastMCP wiring centralized.

## Out of Scope

- UI rendering, sync engines, and remote storage adapters formerly described in
  older documents are no longer part of AMI-FILES.
- Unified persistence is deferred until the orchestrator introduces the new
  UnifiedCRUD layer.
