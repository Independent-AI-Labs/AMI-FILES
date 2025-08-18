# AMI-FILES

## Intelligent Document Processing Module

AMI-FILES provides advanced document processing, extraction, and analysis capabilities for the AMI-ORCHESTRATOR ecosystem, including multi-format support, semantic search, and AI-powered image analysis.

## Key Features

### Document Extractors
Specialized extractors for various document formats with consistent API:

- **PDFExtractor**: PyMuPDF-based PDF processing with text, table, and image extraction
- **DOCXExtractor**: Word document processing with structure preservation
- **SpreadsheetExtractor**: Excel/CSV processing with schema detection
- **ImageExtractor**: Image metadata and OCR capabilities

### Document Models
StorageModel-based document representations with multi-storage support:

- **Document**: Main document model with graph and vector storage
- **DocumentSection**: Hierarchical document sections
- **DocumentTable**: Structured table data
- **DocumentImage**: Visual content with analysis metadata

### MCP Server Tools
Model Context Protocol tools for document operations:

- **index_document**: Parse and index documents for searchable storage
- **read_document**: Extract structured data with templates
- **read_image**: Analyze images with Gemini Vision AI

### Gemini Integration
Advanced image analysis with Google's Gemini API:

- Chart and graph data extraction
- OCR for scanned documents
- Diagram understanding
- Batch processing with rate limiting

## Installation

```bash
# Clone the files module
git clone https://github.com/Independent-AI-Labs/AMI-FILES.git
cd AMI-FILES

# Create virtual environment with uv
uv venv .venv

# Activate environment
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

## Usage Examples

### Document Extraction

```python
from backend.extractors import PDFExtractor, DOCXExtractor

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
from backend.mcp.filesys.server import FilesysMCPServer

# Initialize server
server = FilesysMCPServer()

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
from backend.services.gemini_client import GeminiClient

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
from backend.mcp.filesys.fast_search import FastSearch

# Initialize search
search = FastSearch()

# Search documents
results = await search.search_files(
    directory="/docs",
    pattern="machine learning",
    file_type="pdf",
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