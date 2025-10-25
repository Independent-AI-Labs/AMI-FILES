"""Safe Python execution tools for filesystem server."""

import asyncio
import contextlib
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from base.backend.workers.base import WorkerPool
from base.backend.workers.file_subprocess import FileSubprocess
from base.backend.workers.manager import WorkerPoolManager
from base.backend.workers.types import PoolConfig, PoolType
from files.backend.config.loader import files_config
from loguru import logger

DEFAULT_IMPORT_NAMES = ("sys", "os", "json", "datetime")
DEFAULT_IMPORT_BLOCK = "\n".join(f"import {name}" for name in DEFAULT_IMPORT_NAMES)


class _PythonPoolRegistry:
    """Manage shared worker pool instances for background Python tasks."""

    def __init__(self) -> None:
        self._manager: WorkerPoolManager | None = None
        self._pool: WorkerPool[Any, Any] | None = None

    async def get_or_create_pool(self) -> WorkerPool[Any, Any]:
        """Return an initialized worker pool, creating it if needed."""
        if self._pool is None:
            self._manager = WorkerPoolManager()
            worker_config = files_config.get_worker_config()
            config = PoolConfig(
                name="FilesysPythonBgPool",
                pool_type=PoolType.PROCESS,
                max_workers=worker_config["max_workers"],
                min_workers=worker_config["min_workers"],
            )
            self._pool = await self._manager.create_pool(config)
        return self._pool

    def existing_pool(self) -> WorkerPool[Any, Any] | None:
        """Return the existing pool if it has been initialized."""
        return self._pool


_POOL_REGISTRY = _PythonPoolRegistry()


def _resolve_work_dir(root_dir: Path, cwd: str | None) -> Path:
    """Resolve and validate the working directory for script execution."""

    if not cwd:
        return root_dir

    work_dir = Path(cwd)
    if not work_dir.is_absolute():
        work_dir = root_dir / work_dir

    work_dir = work_dir.resolve()
    if not work_dir.is_relative_to(root_dir):
        raise ValueError("Working directory must be within root directory")

    return work_dir


def _python_bin_from_venv(venv_root: Path) -> Path:
    """Return the Python executable path inside a virtual environment."""

    platform_dir = "Scripts" if sys.platform == "win32" else "bin"
    return venv_root / ".venv" / platform_dir / "python"


def _resolve_python_executable(root_dir: Path, python: str) -> str:
    """Resolve the Python interpreter to use for execution."""

    if python == "system":
        python_exe = sys.executable
        logger.debug(f"Using system Python: {python_exe}")
        return python_exe

    if python == "venv":
        candidate = _python_bin_from_venv(root_dir)
        if candidate.exists():
            python_exe = str(candidate)
            logger.debug(f"Using venv Python: {python_exe}")
            return python_exe
        python_exe = sys.executable
        logger.debug(f"No venv found, using system Python: {python_exe}")
        return python_exe

    custom_path = Path(python)
    if not custom_path.is_absolute():
        custom_path = root_dir / custom_path

    candidate = _python_bin_from_venv(custom_path)
    if not candidate.exists():
        raise ValueError(f"No .venv found in {custom_path}")

    python_exe = str(candidate)
    logger.debug(f"Using venv Python from {custom_path}: {python_exe}")
    return python_exe


def _build_script_command(
    script: str,
    args: Iterable[str] | None,
    python_exe: str,
    root_dir: Path,
) -> list[str]:
    """Build the subprocess command for the requested script or code snippet."""

    raw_path = Path(script)
    args_list = list(args or [])

    script_path: Path | None = None
    candidate = raw_path if raw_path.is_absolute() else (root_dir / raw_path)
    with contextlib.suppress(OSError):
        if candidate.exists() and candidate.is_file():
            script_path = candidate.resolve()
        elif raw_path.exists() and raw_path.is_file():
            script_path = raw_path.resolve()

    if script_path is not None:
        if not script_path.is_relative_to(root_dir):
            raise ValueError("Script path must be within root directory")

        argv_repr = ", ".join(repr(item) for item in [str(script_path), *args_list])
        wrapper_lines = [
            "import runpy",
            "import pathlib",
            *DEFAULT_IMPORT_BLOCK.splitlines(),
            f"script_path = pathlib.Path({str(script_path)!r})",
            f"sys.argv = [{argv_repr}]",
            f"shared_globals = {{name: globals()[name] for name in {DEFAULT_IMPORT_NAMES!r}}}",
            "runpy.run_path(",
            "    str(script_path),",
            '    run_name="__main__",',
            "    init_globals=shared_globals,",
            ")",
        ]

        return [python_exe, "-c", "\n".join(wrapper_lines)]

    script_code = script
    if script_code:
        if DEFAULT_IMPORT_BLOCK not in script_code:
            script_code = f"{DEFAULT_IMPORT_BLOCK}\n{script_code}"
    else:
        script_code = DEFAULT_IMPORT_BLOCK

    command = [python_exe, "-c", script_code]
    command.extend(args_list)
    return command


async def python_run_tool(
    root_dir: Path,
    script: str,
    args: list[str] | None = None,
    timeout: int = 300,
    cwd: str | None = None,
    python: str = "venv",
) -> dict[str, Any]:
    """Execute Python script safely.

    Args:
        root_dir: Root directory for validation
        script: Python script path or code to execute
        args: Additional arguments
        timeout: Execution timeout in seconds (default: 300)
        cwd: Working directory (must be within root_dir)
        python: Python to use - "system", "venv", or path to directory with .venv

    Returns:
        Execution result with stdout, stderr, return code, and success flag
    """

    try:
        resolved_root = root_dir.resolve()
        work_dir = _resolve_work_dir(resolved_root, cwd)
        python_exe = _resolve_python_executable(resolved_root, python)
        cmd_args = _build_script_command(script, args, python_exe, resolved_root)

        logger.debug(f"Executing command: {cmd_args}")
        logger.debug(f"Working directory: {work_dir}")

        executor = FileSubprocess(work_dir=work_dir)
        result: dict[str, Any] = await executor.run(cmd_args, timeout=timeout)

        logger.debug(f"Subprocess completed with returncode={result.get('returncode')}")

        if result.get("timeout"):
            logger.warning(f"Python execution timed out after {timeout} seconds")

        return result

    except ValueError as error:
        logger.warning(f"Python execution rejected: {error}")
        return {"error": str(error), "success": False}
    except (OSError, RuntimeError, TimeoutError) as error:
        logger.error(f"Python execution failed: {error}")
        return {"error": str(error), "success": False}


async def python_run_background_tool(
    root_dir: Path,
    script: str,
    args: list[str] | None = None,
    cwd: str | None = None,
    python: str = "venv",
) -> dict[str, Any]:
    """Execute Python script in background using worker pool.

    Args:
        root_dir: Root directory for validation
        script: Python script path or code to execute
        args: Additional arguments
        cwd: Working directory
        python: Python to use - "system", "venv", or path to directory with .venv

    Returns:
        Task information including task_id
    """
    try:
        pool = await _POOL_REGISTRY.get_or_create_pool()
        timeout = files_config.get_python_timeout("worker_acquire")
        task_id = await pool.acquire_worker(timeout=timeout)

        async def execute() -> dict[str, Any]:
            try:
                return await python_run_tool(root_dir, script, args, 0, cwd, python)
            finally:
                await pool.release_worker(task_id)

        # Fire-and-forget task; caller will poll via task status
        asyncio.create_task(execute())

        return {
            "success": True,
            "task_id": task_id,
            "status": "running",
            "message": f"Python script submitted as background task {task_id}",
        }

    except (OSError, RuntimeError, ValueError) as error:
        logger.error(f"Failed to start background Python execution: {error}")
        return {"error": str(error), "success": False}


async def python_task_status_tool(task_id: str) -> dict[str, Any]:
    """Get status of a background Python task.

    Args:
        task_id: Task identifier

    Returns:
        Task status information
    """
    try:
        pool = _POOL_REGISTRY.existing_pool()

        if pool is None:
            return {"error": "No background tasks running", "success": False}

        # Check worker status
        worker = pool.all_workers.get(task_id)
        if worker:
            return {
                "success": True,
                "task_id": task_id,
                "status": worker.state.value,
                "created_at": worker.created_at.isoformat(),
                "task_count": worker.task_count,
            }

        return {
            "error": f"Task {task_id} not found",
            "success": False,
        }

    except (RuntimeError, KeyError) as error:
        logger.error(f"Failed to get task status: {error}")
        return {"error": str(error), "success": False}


async def python_task_cancel_tool(task_id: str) -> dict[str, Any]:
    """Cancel a background Python task.

    Args:
        task_id: Task identifier

    Returns:
        Cancellation result
    """
    try:
        pool = _POOL_REGISTRY.existing_pool()

        if pool is None:
            return {"error": "No background tasks running", "success": False}

        # Release the worker (this will cancel the task)
        await pool.release_worker(task_id)

        return {
            "success": True,
            "task_id": task_id,
            "message": f"Task {task_id} cancelled",
        }

    except (RuntimeError, KeyError) as error:
        logger.error(f"Failed to cancel task: {error}")
        return {"error": str(error), "success": False}


async def python_list_tasks_tool() -> dict[str, Any]:
    """List all background Python tasks.

    Returns:
        List of active tasks
    """
    try:
        pool = _POOL_REGISTRY.existing_pool()

        if pool is None:
            return {
                "tasks": [],
                "message": "No background tasks running",
                "success": True,
            }

        tasks = [
            {
                "task_id": worker_id,
                "state": worker.state.value,
                "created_at": worker.created_at.isoformat(),
                "task_count": worker.task_count,
                "error_count": worker.error_count,
            }
            for worker_id, worker in pool.all_workers.items()
        ]

        return {
            "success": True,
            "tasks": tasks,
            "total": len(tasks),
            "pool_info": {
                "min_workers": pool.config.min_workers,
                "max_workers": pool.config.max_workers,
                "active_workers": len(pool.all_workers),
            },
        }

    except RuntimeError as error:
        logger.error(f"Failed to list tasks: {error}")
        return {"error": str(error), "success": False}
