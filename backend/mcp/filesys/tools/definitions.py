"""Tool definitions for filesystem MCP server."""

from .git_handlers import (
    git_commit,
    git_diff,
    git_fetch,
    git_history,
    git_merge_abort,
    git_pull,
    git_push,
    git_restore,
    git_stage,
    git_unstage,
)
from .handlers import (
    create_dirs,
    delete_paths,
    find_paths,
    list_dir,
    modify_file,
    read_from_file,
    replace_in_file,
    write_to_file,
)
from .registry import ToolRegistry


def register_all_tools(registry: ToolRegistry) -> None:
    """Register all filesystem tools in the registry.

    Args:
        registry: Tool registry to register tools in
    """
    # Register list_dir tool
    registry.register(
        name="list_dir",
        description="Lists the names of files and subdirectories within a specified directory path.",
        handler=list_dir,
        parameters={
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the directory to list (relative to root or absolute within root).",
                },
                "limit": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum number of items to return.",
                },
                "recursive": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, list subdirectories recursively.",
                },
            },
            "required": ["path"],
        },
    )

    # Register create_dirs tool
    registry.register(
        name="create_dirs",
        description="Creates a directory and any necessary parent directories.",
        handler=create_dirs,
        parameters={
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the directory to create.",
                }
            },
            "required": ["path"],
        },
    )

    # Register find_paths tool
    registry.register(
        name="find_paths",
        description="Searches for files based on keywords in path/name or content.",
        handler=find_paths,
        parameters={
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to start the search.",
                },
                "keywords_path_name": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                    "description": "Keywords to search for in file paths/names.",
                },
                "keywords_file_content": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                    "description": "Keywords to search for in file content.",
                },
                "regex_keywords": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, treat keywords as regular expressions.",
                },
            },
            "required": ["path"],
        },
    )

    # Register read_from_file tool
    registry.register(
        name="read_from_file",
        description="Reads file content with support for offsets and various formats.",
        handler=read_from_file,
        parameters={
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to read.",
                },
                "start_offset_inclusive": {
                    "type": "integer",
                    "default": 0,
                    "description": "Starting offset (0-indexed).",
                },
                "end_offset_inclusive": {
                    "type": "integer",
                    "default": -1,
                    "description": "Ending offset (-1 for end of file).",
                },
                "offset_type": {
                    "type": "string",
                    "enum": ["line", "char", "byte"],
                    "default": "line",
                    "description": "How offsets are interpreted.",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["raw_utf8", "quoted-printable", "base64"],
                    "default": "raw_utf8",
                    "description": "Output format for the content.",
                },
                "file_encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding for reading text files.",
                },
            },
            "required": ["path"],
        },
    )

    # Register write_to_file tool
    registry.register(
        name="write_to_file",
        description="Writes content to a file, creating parent directories if needed.",
        handler=write_to_file,
        parameters={
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to write.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["text", "binary"],
                    "default": "text",
                    "description": "Write mode.",
                },
                "input_format": {
                    "type": "string",
                    "enum": ["raw_utf8", "quoted-printable", "base64"],
                    "default": "raw_utf8",
                    "description": "Format of the input content.",
                },
                "file_encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding for writing text files.",
                },
            },
            "required": ["path", "content"],
        },
    )

    # Register delete_paths tool
    registry.register(
        name="delete_paths",
        description="Deletes multiple files or directories.",
        handler=delete_paths,
        parameters={
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file or directory paths to delete.",
                }
            },
            "required": ["paths"],
        },
    )

    # Register modify_file tool
    registry.register(
        name="modify_file",
        description="Modifies a file by replacing a range of content with new content.",
        handler=modify_file,
        parameters={
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to modify.",
                },
                "start_offset_inclusive": {
                    "type": "integer",
                    "description": "Starting offset for replacement.",
                },
                "end_offset_inclusive": {
                    "type": "integer",
                    "description": "Ending offset for replacement.",
                },
                "new_content": {
                    "type": "string",
                    "description": "New content to insert.",
                },
                "offset_type": {
                    "type": "string",
                    "enum": ["line", "char", "byte"],
                    "default": "line",
                    "description": "How offsets are interpreted.",
                },
                "input_format": {
                    "type": "string",
                    "enum": ["raw_utf8", "quoted-printable", "base64"],
                    "default": "raw_utf8",
                    "description": "Format of the new content.",
                },
                "file_encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding for the file.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["text", "binary"],
                    "default": "text",
                    "description": "File mode.",
                },
            },
            "required": [
                "path",
                "start_offset_inclusive",
                "end_offset_inclusive",
                "new_content",
            ],
        },
    )

    # Register replace_in_file tool
    registry.register(
        name="replace_in_file",
        description="Replaces occurrences of old_content with new_content within a file.",
        handler=replace_in_file,
        parameters={
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file.",
                },
                "old_content": {
                    "type": "string",
                    "description": "Content to find and replace.",
                },
                "new_content": {
                    "type": "string",
                    "description": "Content to replace with.",
                },
                "number_of_occurrences": {
                    "type": "integer",
                    "default": -1,
                    "description": "Number of occurrences to replace (-1 for all).",
                },
                "is_regex": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, treat old_content as a regular expression.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["text", "binary"],
                    "default": "text",
                    "description": "File mode.",
                },
                "input_format": {
                    "type": "string",
                    "enum": ["raw_utf8", "quoted-printable", "base64"],
                    "default": "raw_utf8",
                    "description": "Format of the content strings.",
                },
                "file_encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding for the file.",
                },
            },
            "required": ["path", "old_content", "new_content"],
        },
    )

    # Register git tools
    from .git_definitions import get_git_tools

    for tool_def in get_git_tools():
        handler_map = {
            "git_stage": git_stage,
            "git_unstage": git_unstage,
            "git_commit": git_commit,
            "git_diff": git_diff,
            "git_history": git_history,
            "git_restore": git_restore,
            "git_fetch": git_fetch,
            "git_pull": git_pull,
            "git_push": git_push,
            "git_merge_abort": git_merge_abort,
        }

        handler = handler_map.get(tool_def["name"])
        if handler:
            registry.register(
                name=tool_def["name"],
                description=tool_def["description"],
                handler=handler,  # type: ignore[arg-type]
                parameters=tool_def["inputSchema"],
            )
