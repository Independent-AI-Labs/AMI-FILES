"""Filesystem MCP server using FastMCP."""

import uuid
from pathlib import Path
from typing import Any, Literal

from base.backend.utils.standard_imports import setup_imports
from files.backend.mcp.filesys.tools.facade.document import document_tool
from files.backend.mcp.filesys.tools.facade.filesystem import filesystem_tool
from files.backend.mcp.filesys.tools.facade.git import git_tool
from files.backend.mcp.filesys.tools.facade.metadata import metadata_tool
from files.backend.mcp.filesys.tools.facade.python import python_tool
from loguru import logger
from mcp.server import FastMCP

# Use standard import setup

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()


class FilesysFastMCPServer:
    """Filesystem MCP server using FastMCP."""

    def __init__(self, root_dir: str | None = None, config: dict[str, Any] | None = None) -> None:
        """Initialize Filesystem FastMCP server.

        Args:
            root_dir: Root directory for file operations (defaults to current directory)
            config: Server configuration
        """
        self.config = config or {}
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()

        # Generate session ID for validation and logging
        self.session_id = self.config.get("session_id", str(uuid.uuid4())[:8])

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

        logger.info(f"Filesystem MCP server initialized with root: {self.root_dir}, session: {self.session_id}")

    def _register_tools(self) -> None:
        """Register facade tools with FastMCP."""

        self._register_filesystem_tool()
        self._register_git_tool()
        self._register_python_tool()
        self._register_document_tool()
        self._register_metadata_tool()

    def _register_filesystem_tool(self) -> None:
        """Register filesystem facade tool."""

        @self.mcp.tool(
            description=(
                "Filesystem operations (list, create, find, read, write, delete, modify, replace). "
                "Write operations run LLM validation for Python files using scripts/automation validators. "
                "Session-based validation with fail-open behavior."
            )
        )
        async def filesystem(
            action: Literal["list", "create", "find", "read", "write", "delete", "modify", "replace"],
            path: str | None = None,
            paths: list[str] | None = None,
            content: str | None = None,
            recursive: bool = False,
            pattern: str | None = None,
            limit: int = 100,
            patterns: list[str] | None = None,
            keywords_path_name: list[str] | None = None,
            keywords_file_content: list[str] | None = None,
            regex_keywords: bool = False,
            use_fast_search: bool = True,
            max_workers: int = 8,
            start_line: int | None = None,
            end_line: int | None = None,
            start_offset_inclusive: int = 0,
            end_offset_inclusive: int = -1,
            offset_type: str = "line",
            output_format: str = "raw_utf8",
            file_encoding: str = "utf-8",
            add_line_numbers: bool | None = None,
            mode: str = "text",
            input_format: str = "raw_utf8",
            validate_with_llm: bool = True,
            new_content: str | None = None,
            old_content: str | None = None,
            is_regex: bool = False,
        ) -> dict[str, Any]:
            return await filesystem_tool(
                self.root_dir,
                action,
                path,
                paths,
                content,
                recursive,
                pattern,
                limit,
                patterns,
                keywords_path_name,
                keywords_file_content,
                regex_keywords,
                use_fast_search,
                max_workers,
                start_line,
                end_line,
                start_offset_inclusive,
                end_offset_inclusive,
                offset_type,
                output_format,
                file_encoding,
                add_line_numbers,
                mode,
                input_format,
                validate_with_llm,
                self.session_id,
                new_content,
                old_content,
                is_regex,
            )

    def _register_git_tool(self) -> None:
        """Register git facade tool."""

        @self.mcp.tool(
            description=(
                "Git operations (status, stage, unstage, commit, diff, history, restore, fetch, pull, push, merge_abort). "
                "Commit calls scripts/git_commit.sh (auto-stages all changes). "
                "Push calls scripts/git_push.sh (runs tests before push)."
            )
        )
        async def git(
            action: Literal[
                "status",
                "stage",
                "unstage",
                "commit",
                "diff",
                "history",
                "restore",
                "fetch",
                "pull",
                "push",
                "merge_abort",
            ],
            repo_path: str | None = None,
            message: str | None = None,
            files: list[str] | None = None,
            stage_all: bool = False,
            unstage_all: bool = False,
            amend: bool = False,
            staged: bool = False,
            limit: int = 10,
            oneline: bool = False,
            grep: str | None = None,
            remote: str = "origin",
            branch: str | None = None,
            fetch_all: bool = False,
            rebase: bool = False,
            force: bool = False,
            set_upstream: bool = False,
            short: bool = False,
            show_branch: bool = True,
            untracked: bool = True,
        ) -> dict[str, Any]:
            return await git_tool(
                self.root_dir,
                action,
                repo_path,
                message,
                files,
                stage_all,
                unstage_all,
                amend,
                staged,
                limit,
                oneline,
                grep,
                remote,
                branch,
                fetch_all,
                rebase,
                force,
                set_upstream,
                short,
                show_branch,
                untracked,
            )

    def _register_python_tool(self) -> None:
        """Register python facade tool."""

        @self.mcp.tool(
            description=(
                "Python execution (run, run_background, task_status, task_cancel, list_tasks). Background tasks return task_id for monitoring and cancellation."
            )
        )
        async def python(
            action: Literal["run", "run_background", "task_status", "task_cancel", "list_tasks"],
            script: str | None = None,
            args: list[str] | None = None,
            timeout: int = 300,
            cwd: str | None = None,
            python_: str = "venv",
            task_id: str | None = None,
        ) -> dict[str, Any]:
            return await python_tool(
                self.root_dir,
                action,
                script,
                args,
                timeout,
                cwd,
                python_,
                task_id,
            )

    def _register_document_tool(self) -> None:
        """Register document facade tool."""

        @self.mcp.tool(
            description=(
                "Document processing (index, read, read_image). "
                "Index stores documents for search. Read extracts structured data. "
                "read_image analyzes images using multimodal LLM."
            )
        )
        async def document(
            action: Literal["index", "read", "read_image"],
            path: str,
            extraction_template: dict[str, Any] | None = None,
            extract_tables: bool = True,
            extract_images: bool = False,
            storage_backends: list[str] | None = None,
            instruction: str | None = None,
            perform_ocr: bool = True,
            extract_chart_data: bool = False,
        ) -> dict[str, Any]:
            return await document_tool(
                action,
                path,
                extraction_template,
                extract_tables,
                extract_images,
                storage_backends,
                instruction,
                perform_ocr,
                extract_chart_data,
            )

    def _register_metadata_tool(self) -> None:
        """Register metadata facade tool."""

        @self.mcp.tool(
            description=(
                "Metadata management (list, read, write, delete, git). "
                "Manages progress/feedback logs and .meta directories. "
                "Uses git for versioning metadata changes."
            )
        )
        async def metadata(
            action: Literal["list", "read", "write", "delete", "git"],
            module: str | None = None,
            artifact_type: str | None = None,
            artifact_path: str | None = None,
            content: str | None = None,
            git_action: str | None = None,
            message: str | None = None,
        ) -> dict[str, Any]:
            return await metadata_tool(
                action,
                module,
                artifact_type,
                artifact_path,
                content,
                git_action,
                message,
            )

    def run(self, transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
        """Run the server.

        Args:
            transport: Transport type (stdio, sse, or streamable-http)
        """
        self.mcp.run(transport=transport)
