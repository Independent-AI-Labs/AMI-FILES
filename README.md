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

**File Operations:**

| Tool | Purpose | Key Features |
|------|---------|-------------|
| `list_dir` | List directory contents | Recursive, filtering, limits |
| `create_dirs` | Create directories | Multiple paths, parents |
| `find_paths` | Search for files/dirs | Regex, glob patterns |
| `read_from_file` | Read file contents | Line numbers, encoding |
| `write_to_file` | Write file contents | Atomic writes, backups |
| `delete_paths` | Delete files/dirs | Safe delete, recursive |
| `move_paths` | Move/rename items | Batch operations |
| `copy_paths` | Copy files/dirs | Preserve metadata |
| `get_file_info` | Get metadata | Size, dates, permissions |
| `calculate_hash` | File checksums | MD5, SHA256, SHA512 |
| `validate_content` | Pre-commit validation | Auto-fix, linting |

**Git Operations:**

| Tool | Purpose | Key Features |
|------|---------|-------------|
| `git_status` | Repository status | Staged/unstaged files |
| `git_diff` | View changes | Unified diff format |
| `git_stage` | Stage files | Pattern matching |
| `git_commit` | Create commit | Message templates |
| `git_log` | View history | Filtering, limits |
| `git_push` | Push changes | Dry run, force |

**Transport Modes:**
```bash
# CLI integration (stdio)
python backend/mcp/filesys/run_filesys.py --root-dir /safe/workspace

# Network access (websocket)
python backend/mcp/filesys/run_filesys.py --transport websocket --port 8766
```

### 📄 Compliant Document Processing

**Secure Processing Features:**
- **PDF** - Extract with data classification and redaction support
- **Word** - Parse while preserving document permissions
- **Excel** - Process with cell-level access control
- **Images** - OCR with PII detection and masking capabilities

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

```bash
# Clone and setup
git clone https://github.com/Independent-AI-Labs/AMI-FILES.git
cd AMI-FILES
uv venv .venv && uv pip install -r requirements.txt

# Run MCP server
python backend/mcp/filesys/run_filesys.py --root-dir ./workspace
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

## Configuration

### Gemini API Setup
Set your Gemini API key as an environment variable:

```bash
export GEMINI_API_KEY="your-api-key-here"
```

### Storage Configuration
Configure storage backends for document models:

```python
class Document(StorageModel):
    class Meta:
        storage_configs = {
            "graph": StorageConfig(
                storage_type=StorageType.GRAPH,
                host="172.72.72.2",
                port=9080
            ),
            "vector": StorageConfig(
                storage_type=StorageType.VECTOR,
                host="172.72.72.2",
                port=5432
            )
        }
```

## Compliance & Security

### Data Protection Features
- **Path Sandboxing** - Restrict operations to approved directories
- **PII Detection** - Automatic identification of sensitive data
- **Retention Policies** - Automatic file expiry and deletion
- **Access Logging** - Complete audit trail for compliance

### GDPR Compliance
- **Right to Access** - Export all files related to a data subject
- **Right to Erasure** - Secure deletion with verification
- **Data Portability** - Standard format exports
- **Consent Tracking** - Document processing permissions

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
# Run all tests
python scripts/run_tests.py

# Run specific test
python scripts/run_tests.py tests/unit/test_filesys_mcp_server.py

# Run with coverage
python -m pytest --cov=backend --cov-report=html
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