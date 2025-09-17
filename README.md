# AMI-FILES

AMI-FILES is the orchestration layer's secure file fabric. It gives AI agents
and human operators a governed way to explore, change, and analyse code or
content while preserving the compliance posture demanded by regulated teams.

## Why Teams Deploy AMI-FILES
- Enable automation to change repositories without bypassing enterprise guardrails.
- Shorten investigation time by pairing fast file search with document and image
  extraction.
- Keep git history auditable even when non-engineering agents are issuing
  commands.
- Centralise script execution, logging, and validation inside a sandboxed service
  that mirrors the wider AMI platform policies.

## Platform Overview
AMI-FILES ships as a FastMCP server. Callers interact through MCP tools that map
one-to-one with guarded operations inside the module. The service sits alongside
other AMI components but retains its own dependency set and runtime isolation.

### Capability Pillars
1. **Governed Filesystem Access** - fine-grained read and write primitives with
   path validation, pre-commit style linting, and large file checks.
2. **Version-Control Discipline** - staged git commands so automation stays inside
the same workflows as human contributors.
3. **Programmable Execution** - transient Python execution with background task
   management for data preparation or migration scripts.
4. **Document Intelligence** - extractor suite for PDFs, spreadsheets, office
   documents, and images, with optional Gemini reasoning when an API key is
   present.

### Tool Families
- **Filesystem:** `list_dir`, `create_dirs`, `find_paths`, `read_from_file`,
  `write_to_file`, `delete_paths`, `modify_file`, `replace_in_file`
- **Git:** `git_status`, `git_stage`, `git_unstage`, `git_commit`, `git_diff`,
  `git_history`, `git_restore`, `git_fetch`, `git_pull`, `git_push`,
  `git_merge_abort`
- **Python Execution:** `python_run`, `python_run_background`,
  `python_task_status`, `python_task_cancel`, `python_list_tasks`
- **Document and Image:** `index_document`, `read_document`, `read_image`

## Business-Centric Outcomes
| Outcome | How AMI-FILES Supports It |
|---------|---------------------------|
| Faster incident response | Agents can triage repositories, search logs, and patch issues without waiting for human engineers to run commands. |
| Audit-ready automation | Every mutation flows through git-aware tooling and is logged with arguments, timings, and validation output. |
| Safe experimentation | Sandboxing and protected-directory rules stop accidental writes to infrastructure folders or other AMI modules. |
| Knowledge discovery | Document and image extractors unlock latent information inside PDFs, decks, and scans for downstream analytics. |

## Operating Model
- **Server:** `FilesysFastMCPServer` consolidates tool registration and enforces
  the sandbox root supplied at startup.
- **Utilities:** Shared helpers in `backend/mcp/filesys/utils` provide fast file
  search, path validation, and pre-commit lifting.
- **Extractors:** Classes under `backend/extractors` implement the
  `DocumentExtractor` protocol and return structured models from
  `backend/models/document.py`.
- **Gemini Integration:** `backend/services/gemini_client.py` wraps outbound API
  calls and gracefully degrades when no credentials are configured.

## Working With The Module
- Bootstrap the environment via `python module_setup.py` or
  `uv run --directory files python3 module_setup.py`.
- Launch the FastMCP server locally with
  `uv run --directory files python3 scripts/run_filesys_fastmcp.py`.
- Run the test suite using
  `uv run --directory files python3 scripts/run_tests.py`.
- Set `GEMINI_API_KEY` in the environment to enable multimodal image analysis.

## Guardrails and Compliance
- `validate_path` blocks access to protected directories, preventing writes into
  `.git`, `.venv`, sibling modules, or orchestrator roots.
- `PreCommitValidator` executes lint and policy checks before content hits disk.
- `FileUtils` enforces maximum size thresholds and differentiates text versus
  binary payloads.
- Background Python tasks are tracked in a registry so callers can inspect,
  cancel, or retry long-running work.

## Roadmap Highlights
- Reconnect document persistence once the orchestrator finalises the UnifiedCRUD
  layer.
- Expand coverage for Gemini-assisted extraction workflows in the integration
  suite.
- Continue aligning lint/type policies with the `base` and `browser` modules as
  shared configs evolve.
