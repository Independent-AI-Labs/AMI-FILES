"""Filesystem MCP server using FastMCP."""

from pathlib import Path
from typing import Any

# Use standard import setup
from base.backend.utils.standard_imports import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from loguru import logger  # noqa: E402
from mcp.server import FastMCP  # noqa: E402

from .tools.document_tools import (  # noqa: E402
    index_document_tool,
    read_document_tool,
    read_image_tool,
)
from .tools.filesystem_tools import (  # noqa: E402
    create_dirs_tool,
    delete_paths_tool,
    find_paths_tool,
    list_dir_tool,
    modify_file_tool,
    read_from_file_tool,
    replace_in_file_tool,
    write_to_file_tool,
)
from .tools.git_tools import (  # noqa: E402
    git_commit_tool,
    git_diff_tool,
    git_fetch_tool,
    git_history_tool,
    git_merge_abort_tool,
    git_pull_tool,
    git_push_tool,
    git_restore_tool,
    git_stage_tool,
    git_status_tool,
    git_unstage_tool,
)
from .tools.python_tools import (  # noqa: E402
    python_list_tasks_tool,
    python_run_background_tool,
    python_run_tool,
    python_task_cancel_tool,
    python_task_status_tool,
)


class FilesysFastMCPServer:
    """Filesystem MCP server using FastMCP."""

    def __init__(
        self, root_dir: str | None = None, config: dict[str, Any] | None = None
    ):
        """Initialize Filesystem FastMCP server.

        Args:
            root_dir: Root directory for file operations (defaults to current directory)
            config: Server configuration
        """
        self.config = config or {}
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()

        # Ensure root directory exists and is absolute
        try:
            self.root_dir = self.root_dir.resolve(strict=True)
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Root directory does not exist: {root_dir}") from e

        if not self.root_dir.is_dir():
            raise ValueError(f"Root path is not a directory: {self.root_dir}")

        # Create FastMCP server
        self.mcp = FastMCP(name="FilesysMCPServer")

        # Register tools
        self._register_tools()

        logger.info(f"Filesystem MCP server initialized with root: {self.root_dir}")

    def _register_tools(self):
        """Register filesystem tools with FastMCP."""

        # File system tools
        @self.mcp.tool(description="List directory contents")
        async def list_dir(
            path: str = ".",
            recursive: bool = False,
            pattern: str | None = None,
            limit: int = 100,
        ) -> dict[str, Any]:
            """List directory contents."""
            return await list_dir_tool(self.root_dir, path, recursive, pattern, limit)

        @self.mcp.tool(description="Create directories")
        async def create_dirs(paths: list[str]) -> dict[str, Any]:
            """Create directories."""
            return await create_dirs_tool(self.root_dir, paths)

        @self.mcp.tool(description="Find paths matching patterns or keywords")
        async def find_paths(
            patterns: list[str] | None = None,
            path: str = ".",
            keywords_path_name: list[str] | None = None,
            keywords_file_content: list[str] | None = None,
            regex_keywords: bool = False,
            use_fast_search: bool = True,
            max_workers: int = 8,
            recursive: bool = True,
        ) -> dict[str, Any]:
            """Find paths."""
            return await find_paths_tool(
                self.root_dir,
                patterns,
                path,
                keywords_path_name,
                keywords_file_content,
                regex_keywords,
                use_fast_search,
                max_workers,
                recursive,
            )

        @self.mcp.tool(description="Read file contents")
        async def read_from_file(
            path: str,
            start_line: int | None = None,
            end_line: int | None = None,
            start_offset_inclusive: int = 0,
            end_offset_inclusive: int = -1,
            offset_type: str = "line",
            output_format: str = "raw_utf8",
            file_encoding: str = "utf-8",
            add_line_numbers: bool | None = None,
        ) -> dict[str, Any]:
            """Read from file."""
            return await read_from_file_tool(
                self.root_dir,
                path,
                start_line,
                end_line,
                start_offset_inclusive,
                end_offset_inclusive,
                offset_type,
                output_format,
                file_encoding,
                add_line_numbers,
            )

        @self.mcp.tool(description="Write content to file")
        async def write_to_file(
            path: str,
            content: str,
            mode: str = "text",
            input_format: str = "raw_utf8",
            file_encoding: str = "utf-8",
            validate_with_precommit: bool = True,
        ) -> dict[str, Any]:
            """Write to file."""
            return await write_to_file_tool(
                self.root_dir,
                path,
                content,
                mode,
                input_format,
                file_encoding,
                validate_with_precommit,
            )

        @self.mcp.tool(description="Delete files or directories")
        async def delete_paths(paths: list[str]) -> dict[str, Any]:
            """Delete paths."""
            return await delete_paths_tool(self.root_dir, paths)

        @self.mcp.tool(
            description="Modify file by replacing content at specific offsets"
        )
        async def modify_file(
            path: str,
            start_offset_inclusive: int,
            end_offset_inclusive: int,
            new_content: str,
            offset_type: str = "line",
        ) -> dict[str, Any]:
            """Modify file."""
            return await modify_file_tool(
                self.root_dir,
                path,
                start_offset_inclusive,
                end_offset_inclusive,
                new_content,
                offset_type,
            )

        @self.mcp.tool(description="Replace text in file")
        async def replace_in_file(
            path: str, old_content: str, new_content: str, is_regex: bool = False
        ) -> dict[str, Any]:
            """Replace in file."""
            return await replace_in_file_tool(
                self.root_dir, path, old_content, new_content, is_regex
            )

        # Git tools
        @self.mcp.tool(description="Get git repository status")
        async def git_status(
            repo_path: str | None = None,
            short: bool = False,
            branch: bool = True,
            untracked: bool = True,
        ) -> dict[str, Any]:
            """Get git status."""
            return await git_status_tool(
                self.root_dir, repo_path, short, branch, untracked
            )

        @self.mcp.tool(description="Stage files for commit")
        async def git_stage(
            repo_path: str | None = None,
            files: list[str] | None = None,
            all: bool = False,
        ) -> dict[str, Any]:
            """Stage files."""
            return await git_stage_tool(self.root_dir, repo_path, files, all)

        @self.mcp.tool(description="Unstage files")
        async def git_unstage(
            repo_path: str | None = None,
            files: list[str] | None = None,
            all: bool = False,
        ) -> dict[str, Any]:
            """Unstage files."""
            return await git_unstage_tool(self.root_dir, repo_path, files, all)

        @self.mcp.tool(description="Commit changes")
        async def git_commit(
            message: str,
            repo_path: str | None = None,
            amend: bool = False,
            all: bool = False,
        ) -> dict[str, Any]:
            """Commit changes."""
            return await git_commit_tool(self.root_dir, message, repo_path, amend, all)

        @self.mcp.tool(description="Show differences")
        async def git_diff(
            repo_path: str | None = None,
            staged: bool = False,
            files: list[str] | None = None,
        ) -> dict[str, Any]:
            """Show diff."""
            return await git_diff_tool(self.root_dir, repo_path, staged, files)

        @self.mcp.tool(description="Show commit history")
        async def git_history(
            repo_path: str | None = None, limit: int = 10, oneline: bool = False
        ) -> dict[str, Any]:
            """Show history."""
            return await git_history_tool(self.root_dir, repo_path, limit, oneline)

        @self.mcp.tool(description="Restore files")
        async def git_restore(
            repo_path: str | None = None,
            files: list[str] | None = None,
            staged: bool = False,
        ) -> dict[str, Any]:
            """Restore files."""
            return await git_restore_tool(self.root_dir, repo_path, files, staged)

        @self.mcp.tool(description="Fetch from remote")
        async def git_fetch(
            repo_path: str | None = None, remote: str = "origin", all: bool = False
        ) -> dict[str, Any]:
            """Fetch from remote."""
            return await git_fetch_tool(self.root_dir, repo_path, remote, all)

        @self.mcp.tool(description="Pull from remote")
        async def git_pull(
            repo_path: str | None = None,
            remote: str = "origin",
            branch: str | None = None,
            rebase: bool = False,
        ) -> dict[str, Any]:
            """Pull from remote."""
            return await git_pull_tool(self.root_dir, repo_path, remote, branch, rebase)

        @self.mcp.tool(description="Push to remote")
        async def git_push(
            repo_path: str | None = None,
            remote: str = "origin",
            branch: str | None = None,
            force: bool = False,
            set_upstream: bool = False,
        ) -> dict[str, Any]:
            """Push to remote."""
            return await git_push_tool(
                self.root_dir, repo_path, remote, branch, force, set_upstream
            )

        @self.mcp.tool(description="Abort merge")
        async def git_merge_abort(repo_path: str | None = None) -> dict[str, Any]:
            """Abort merge."""
            return await git_merge_abort_tool(self.root_dir, repo_path)

        # Python execution tools
        @self.mcp.tool(description="Execute Python script or code")
        async def python_run(
            script: str,
            args: list[str] | None = None,
            timeout: int = 300,
            cwd: str | None = None,
            python: str = "venv",
        ) -> dict[str, Any]:
            """Execute Python script."""
            return await python_run_tool(
                self.root_dir, script, args, timeout, cwd, python
            )

        @self.mcp.tool(description="Execute Python script in background")
        async def python_run_background(
            script: str,
            args: list[str] | None = None,
            cwd: str | None = None,
            python: str = "venv",
        ) -> dict[str, Any]:
            """Execute Python script in background."""
            return await python_run_background_tool(
                self.root_dir, script, args, cwd, python
            )

        @self.mcp.tool(description="Get status of background Python task")
        async def python_task_status(task_id: str) -> dict[str, Any]:
            """Get Python task status."""
            return await python_task_status_tool(task_id)

        @self.mcp.tool(description="Cancel background Python task")
        async def python_task_cancel(task_id: str) -> dict[str, Any]:
            """Cancel Python task."""
            return await python_task_cancel_tool(task_id)

        @self.mcp.tool(description="List all background Python tasks")
        async def python_list_tasks() -> dict[str, Any]:
            """List Python tasks."""
            return await python_list_tasks_tool()

        # Document tools
        @self.mcp.tool(description="Parse and index documents for searchable storage")
        async def index_document(
            path: str,
            extract_tables: bool = True,
            extract_images: bool = False,
            storage_backends: list[str] | None = None,
        ) -> dict[str, Any]:
            """Index document."""
            return await index_document_tool(
                path, extract_tables, extract_images, storage_backends
            )

        @self.mcp.tool(description="Read and parse documents into structured data")
        async def read_document(
            path: str,
            extraction_template: dict[str, Any] | None = None,
            extract_tables: bool = True,
            extract_images: bool = False,
        ) -> dict[str, Any]:
            """Read document."""
            return await read_document_tool(
                path, extraction_template, extract_tables, extract_images
            )

        @self.mcp.tool(description="Analyze images using multimodal LLM")
        async def read_image(
            path: str,
            instruction: str | None = None,
            perform_ocr: bool = True,
            extract_chart_data: bool = False,
        ) -> dict[str, Any]:
            """Read image."""
            return await read_image_tool(
                path, instruction, perform_ocr, extract_chart_data
            )

    def run(self, transport: str = "stdio"):
        """Run the server.

        Args:
            transport: Transport type (stdio, sse, or streamable-http)
        """
        self.mcp.run(transport=transport)  # type: ignore[arg-type]
