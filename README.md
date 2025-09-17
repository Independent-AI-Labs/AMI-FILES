# AMI-FILES: Secure File Operations Platform

## Business Value

AMI-FILES ensures all file operations meet enterprise security and compliance requirements. With built-in access controls, audit logging, and sandboxed execution, every file interaction is traceable and compliant with data protection regulations.

## Core Capabilities

### 🚀 Secure & Auditable File Operations
Every file operation is controlled, logged, and compliant with security policies.

**Compliance Features:**
- **Access Control** - Operations restricted to configured safe paths
- **Audit Logging** - Every read, write, delete tracked with timestamps
- **Pre-commit Validation** - Security and compliance checks before changes
- **Cryptographic Verification** - File integrity checking with hash validation

### 🔌 Filesys MCP Server

Production-ready file system control via Model Context Protocol for AI agents and automation tools.

**File Operations (current implementation):**

| Tool | Purpose | Key Features |
|------|---------|-------------|
| `list_dir` | List directory contents | Recursive search, glob filtering, hard limits |
| `create_dirs` | Create directories | Multiple paths, parent creation, sandbox enforcement |
| `find_paths` | Search for files/dirs | Keyword search, regex/glob support, fast parallel mode |
| `read_from_file` | Read file contents | Line/byte offsets, encoding control, numbered output |
| `write_to_file` | Write file contents | Pre-commit validation, text/binary support |
| `delete_paths` | Delete files/dirs | Recursive deletion with sandbox guard |
| `modify_file` | Replace content by offsets | Line or byte offsets, validation |
| `replace_in_file` | Search and replace text | Regex or literal replacement |

**Git Operations:**

| Tool | Purpose | Key Features |
|------|---------|-------------|
| `git_status` | Repository status | Short/long formats, branch info |
| `git_stage` | Stage files | Explicit paths or `--all` |
| `git_unstage` | Unstage files | File selection or full reset |
| `git_commit` | Create commit | Amend and `--all` support |
| `git_diff` | View changes | Staged or working tree diffs |
| `git_history` | View history | Limit, oneline, grep filters |
| `git_restore` | Restore files | Checkout files with staged toggle |
| `git_fetch` | Fetch from remote | Remote selection, `--all` |
| `git_pull` | Pull from remote | Remote/branch selection, rebase |
| `git_push` | Push changes | Force and set-upstream toggles |
| `git_merge_abort` | Abort merge | Cleanup conflicted merge state |

**Python Execution:**

| Tool | Purpose | Key Features |
|------|---------|-------------|
| `python_run` | Execute Python scripts | Timeout control, cwd override, venv shim |
| `python_run_background` | Fire-and-forget execution | Background task registry |
| `python_task_status` | Inspect background task | Status + stdout/stderr snapshot |
| `python_task_cancel` | Cancel background task | Cooperative cancellation |
| `python_list_tasks` | Enumerate tasks | Helpful for cleanup |

**Document & Image Analysis:**

| Tool | Purpose | Key Features |
|------|---------|-------------|
| `index_document` | Extract and summarize | PDF/DOCX/XLSX routing, optional tables/images |
| `read_document` | Structured extraction | Sections, tables, metadata |
| `read_image` | Image metadata & LLM analysis | OCR metadata, Gemini optional |

Transport and runners are module-specific. For programmatic use, import `FilesysFastMCPServer` and configure the desired transport in your own runner.

### 📄 Document Processing Status

The document tooling exposes three FastMCP endpoints today:

- `index_document` orchestrates extractor selection, builds `Document*` models in memory, and returns summary metadata.
- `read_document` provides structured extraction output (sections, tables, images) without persisting results.
- `read_image` optionally calls Gemini for higher-level analysis when `GEMINI_API_KEY` is configured.

> **Note:** Persistent storage through UnifiedCRUD is not yet wired. See the TODO section for follow-up tasks.

### ⚡ Fast File Search

```python
from files.backend.mcp.filesys.fast_search import FastFileSearcher

searcher = FastFileSearcher("/workspace")
results = await searcher.search_files(
    content_keywords=["TODO", "FIXME"],
    path_pattern="*.py"
)
```

## Quick Start

See the orchestrator root README for environment setup. Within a Python environment, use the server classes directly or follow module-specific runner guidance when available.

## Configuration

### Gemini API Setup
Set your Gemini API key as an environment variable:

```bash
export GEMINI_API_KEY="your-api-key-here"
```

### Storage Configuration
The current implementation keeps extracted `Document*` models in memory only. Storage backends will be reintroduced once UnifiedCRUD wiring is restored (see TODOs).

## Compliance & Security

### Current Safeguards
- **Path sandboxing** – `validate_path` enforces a protected-directory allowlist for write/delete operations.
- **Pre-commit validation** – `write_to_file` uses the shared `PreCommitValidator` to lint before writes.
- **Size limits** – File reads respect `FileUtils.check_file_size` to avoid oversized payloads.
- **Structured logging** – All tools log success/error paths via `loguru` for observability.

### Roadmap Items (see TODOs)
- Persistent audit trail once UnifiedCRUD storage is restored.
- Optional content validation hooks for additional compliance scanners.

## Import Conventions

**BREAKING CHANGE (2025-09-02):** All internal imports now use absolute paths with the `files.` prefix.

### Internal Module Imports
All imports within the files module must use the `files.backend` prefix:

```python
# Correct - Absolute imports with files prefix
from files.backend.extractors.pdf_extractor import PDFExtractor
from files.backend.extractors.docx_extractor import DOCXExtractor
from files.backend.mcp.filesys.tools.filesystem_tools import list_dir_tool

# Incorrect - Relative imports (deprecated)
from .extractors import PDFExtractor
from ..tools.filesystem_tools import list_dir_tool
```

### Cross-Module Imports
When importing from other orchestrator modules, use the `base.backend` prefix:

```python
# Correct - Cross-module import
from base.backend.utils.standard_imports import setup_imports

# Configuration import from orchestrator
from base.backend.config.loader import orchestrator_config
```

### Entry Point Scripts
Entry point scripts must set up the module path before importing:

```python
#!/usr/bin/env python
"""Entry point script pattern."""

from pathlib import Path
import sys

# Add both files and base to Python path
MODULE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))  # For base imports

# Now safe to import
from files.backend.mcp.filesys.filesys_server import FilesysFastMCPServer
```

## Usage Examples

### Document Extraction

```python
from files.backend.extractors.pdf_extractor import PDFExtractor
from files.backend.extractors.docx_extractor import DOCXExtractor

# Extract PDF
pdf_extractor = PDFExtractor()
result = await pdf_extractor.extract(
    Path("document.pdf"),
    options={
        "extract_tables": True,
        "extract_images": True
    }
)

print(f"Extracted {len(result.sections)} sections")
print(f"Found {len(result.tables)} tables")
```

## TODO

- [ ] Restore parity with the historical tool surface (`move_paths`, `copy_paths`, `get_file_info`, `calculate_hash`, `validate_content`).
- [ ] Persist `Document*` models using UnifiedCRUD and emit audit records for document workflows.
- [ ] Extend automated tests to cover document extraction and Gemini-assisted image analysis paths.
- [ ] Revisit README claims once the above features land to keep docs in sync with reality.

### MCP Server Usage

```python
from files.backend.mcp.filesys.filesys_server import FilesysFastMCPServer

# Initialize server
server = FilesysFastMCPServer()

# Index a document
result = await server.handle_tool_call(
    "index_document",
    {
        "path": "/path/to/document.pdf",
        "extract_tables": True,
        "extract_images": False,
        "storage_backends": ["graph", "vector"]
    }
)

print(f"Document indexed with ID: {result['document_id']}")
```

### Image Analysis with Gemini

```python
from files.backend.services.gemini_client import GeminiClient

# Initialize client
client = GeminiClient(api_key="your-key")

async with client:
    # Analyze chart
    result = await client.extract_chart_data("chart.png")
    print(result["response"])
    
    # Perform OCR
    ocr_result = await client.perform_ocr("scanned_doc.png")
    print(ocr_result["response"])
```

### Document Search

```python
from files.backend.mcp.filesys.utils.fast_search import FastFileSearcher

# Initialize search
searcher = FastFileSearcher("/workspace")

# Search documents
results = await searcher.search_files(
    content_keywords=["machine learning"],
    path_pattern="*.pdf",
    max_results=10
)

for result in results:
    print(f"{result['path']}: {result['score']}")
```

## Architecture

```
AMI-FILES/
├── backend/
│   ├── extractors/         # Document extractors
│   │   ├── base.py            # Base extractor class
│   │   ├── pdf_extractor.py   # PDF processing
│   │   ├── docx_extractor.py  # Word processing
│   │   ├── spreadsheet_extractor.py  # Excel/CSV
│   │   └── image_extractor.py # Image processing
│   │
│   ├── models/            # Document models
│   │   └── document.py       # StorageModel implementations
│   │
│   ├── services/          # External services
│   │   └── gemini_client.py  # Gemini API client
│   │
│   └── mcp/               # MCP server
│       └── filesys/
│           ├── server.py          # MCP server implementation
│           ├── fast_search.py     # Fast file search
│           └── tools/
│               ├── document_handlers.py  # Document tools
│               └── git_handlers.py       # Git tools
│
├── res/                   # Resources
│   └── *_extensions.json     # File type definitions
│
└── tests/                 # Test suite
    ├── unit/                 # Unit tests
    └── integration/          # Integration tests
```

## Testing

```bash
# From repository root
python scripts/run_tests.py -k files

# Or directly with pytest
pytest -k files --cov=files/backend --cov-report=term-missing
```

## API Reference

### Extractors

All extractors implement the `DocumentExtractor` base class:

```python
async def extract(
    self,
    file_path: Path,
    options: dict[str, Any] | None = None
) -> ExtractionResult
```

**Options:**
- `extract_tables`: Extract structured tables
- `extract_images`: Extract embedded images
- `max_pages`: Limit pages to process
- `perform_ocr`: Enable OCR for images

### MCP Tools

**index_document**
```python
{
    "path": str,              # Document path
    "extract_tables": bool,   # Extract tables
    "extract_images": bool,   # Extract images
    "storage_backends": list  # Storage targets
}
```

**read_document**
```python
{
    "path": str,                    # Document path
    "extraction_template": dict,    # Optional template
    "extract_tables": bool,         # Include tables
    "extract_images": bool          # Include images
}
```

**read_image**
```python
{
    "path": str,                # Image path
    "instruction": str,         # Analysis instruction
    "perform_ocr": bool,        # Perform OCR
    "extract_chart_data": bool  # Extract chart data
}
```

## Performance

- PDF processing: ~1000 pages/minute
- Image analysis: 60 requests/minute (Gemini rate limit)
- Search: <100ms for 100k files
- Extraction accuracy: >95% for text, >90% for tables

## Dependencies

Core dependencies:
- `pymupdf>=1.25.1` - PDF processing
- `python-docx>=1.1.2` - Word documents
- `openpyxl>=3.1.5` - Excel files
- `pandas>=2.2.3` - Data processing
- `Pillow>=11.1.0` - Image processing
- `sentence-transformers>=3.3.1` - Embeddings
- `aiohttp>=3.11.11` - Async HTTP

## Contributing

Please follow the guidelines in `CLAUDE.md`:
- Use uv for dependency management
- Run tests before committing
- Maximum 300 lines per class
- Proper error handling with logging
- Type hints on all functions

## License

MIT License - See LICENSE file for details

## Support

- GitHub Issues: [AMI-FILES Issues](https://github.com/Independent-AI-Labs/AMI-FILES/issues)
- Main Project: [AMI-ORCHESTRATOR](https://github.com/Independent-AI-Labs/AMI-ORCHESTRATOR)
