# Filesystem MCP Server

A Model Context Protocol (MCP) server that provides comprehensive filesystem operations following the browser MCP architecture pattern.

## Features

- **File Operations**: Read, write, modify, and delete files
- **Directory Management**: Create, list, and navigate directories
- **Search Capabilities**: Find files by path patterns or content
- **Content Replacement**: Replace text in files with regex support
- **Binary Support**: Handle both text and binary files
- **Encoding Support**: Base64, quoted-printable, and UTF-8 formats
- **Security**: Path validation to prevent access outside root directory

## Available Tools

### list_dir
Lists files and subdirectories within a specified directory.
- Supports recursive listing
- Configurable result limit

### create_dirs
Creates directories including parent directories as needed.

### find_paths
Searches for files based on:
- Keywords in file paths/names
- Keywords in file content
- Regular expression support

### read_from_file
Reads file content with:
- Offset support (line, char, byte)
- Multiple output formats
- Binary file handling

### write_to_file
Writes content to files with:
- Text and binary modes
- Multiple input formats
- Automatic parent directory creation

### delete_paths
Deletes multiple files or directories in a single operation.

### modify_file
Modifies specific ranges within files:
- Line, character, or byte-based offsets
- Preserves surrounding content

### replace_in_file
Replaces content within files:
- Plain text or regex patterns
- Control number of replacements
- Binary and text file support

## Usage

### Standalone Server (stdio)
```bash
python scripts/run_filesys.py --root-dir /path/to/root
```

### Integration with MCP Client

```python
from files.backend.mcp.filesys.filesys_server import FilesysFastMCPServer

# Create server with specific root directory
server = FilesysFastMCPServer(root_dir="/path/to/files")

# Run with stdio transport
await server.run_stdio()

# Or run with WebSocket transport
await server.run_websocket(host="localhost", port=8765)
```

## Security

All file operations are restricted to the configured root directory. Path traversal attempts are blocked to prevent unauthorized access to system files.

## Testing

The server includes comprehensive test coverage:
- Unit tests for all operations
- Integration tests for workflows
- Error handling validation
- Protocol compliance verification

Run tests:
```bash
python scripts/run_tests.py
```