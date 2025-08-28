"""Safe Python execution tools for filesystem server."""

import asyncio
import sys
from pathlib import Path
from typing import Any

# Import file-based subprocess from base
from base.backend.workers.file_subprocess import FileSubprocess
from loguru import logger


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
        # Validate working directory
        if cwd:
            work_dir = Path(cwd)
            if not work_dir.is_absolute():
                work_dir = root_dir / work_dir
            if not work_dir.resolve().is_relative_to(root_dir):
                return {
                    "error": "Working directory must be within root directory",
                    "success": False,
                }
        else:
            work_dir = root_dir

        # Determine Python executable
        if python == "system":
            python_exe = sys.executable
            logger.debug(f"Using system Python: {python_exe}")
        elif python == "venv":
            # Look for venv in root_dir
            venv_python = (
                root_dir
                / ".venv"
                / ("Scripts" if sys.platform == "win32" else "bin")
                / "python"
            )
            if venv_python.exists():
                python_exe = str(venv_python)
                logger.debug(f"Using venv Python: {python_exe}")
            else:
                python_exe = sys.executable
                logger.debug(f"No venv found, using system Python: {python_exe}")
        else:
            # Custom path provided
            custom_path = Path(python)
            if not custom_path.is_absolute():
                custom_path = root_dir / custom_path
            venv_python = (
                custom_path
                / ".venv"
                / ("Scripts" if sys.platform == "win32" else "bin")
                / "python"
            )
            if venv_python.exists():
                python_exe = str(venv_python)
                logger.debug(f"Using venv Python from {custom_path}: {python_exe}")
            else:
                return {"error": f"No .venv found in {custom_path}", "success": False}

        # Check if script is a file or code
        script_path = Path(script)
        if script_path.exists() and script_path.is_file():
            # Execute file without unbuffered output flag (might be causing issues)
            cmd_args = [python_exe, str(script_path)]
        else:
            # Execute code directly without unbuffered output flag
            cmd_args = [python_exe, "-c", script]

        # Add additional arguments
        if args:
            cmd_args.extend(args)

        logger.debug(f"Executing command: {cmd_args}")
        logger.debug(f"Working directory: {work_dir}")

        # Use file-based subprocess for reliable execution
        executor = FileSubprocess(work_dir=work_dir)
        result = await executor.run(cmd_args, timeout=timeout)

        logger.debug(f"Subprocess completed with returncode={result.get('returncode')}")

        # Return result in expected format
        if result.get("timeout"):
            logger.warning(f"Python execution timed out after {timeout} seconds")

        return result  # type: ignore[no-any-return]

    except Exception as e:
        logger.error(f"Python execution failed: {e}")
        return {"error": str(e)}


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
        # Import here to avoid circular dependency
        from base.backend.workers.base import WorkerPoolManager
        from base.backend.workers.types import PoolConfig, PoolType

        # Get or create pool manager and pool
        if not hasattr(python_run_background_tool, "_manager"):
            python_run_background_tool._manager = WorkerPoolManager()  # type: ignore[attr-defined] # noqa: SLF001
            config = PoolConfig(
                name="FilesysPythonBgPool",
                pool_type=PoolType.PROCESS,
                max_workers=5,
                min_workers=1,
            )
            python_run_background_tool._pool = (  # type: ignore[attr-defined] # noqa: SLF001
                await python_run_background_tool._manager.create_pool(config)  # type: ignore[attr-defined] # noqa: SLF001
            )

        pool = python_run_background_tool._pool  # type: ignore[attr-defined] # noqa: SLF001

        # Submit task to pool
        task_id = await pool.acquire_worker(timeout=30)

        # Execute in background
        async def execute():
            try:
                result = await python_run_tool(
                    root_dir, script, args, 0, cwd, python
                )  # 0 = no timeout
                return result
            finally:
                await pool.release_worker(task_id)

        task = asyncio.create_task(execute())
        del task  # Let it run in background

        return {
            "success": True,
            "task_id": task_id,
            "status": "running",
            "message": f"Python script submitted as background task {task_id}",
        }

    except Exception as e:
        logger.error(f"Failed to start background Python execution: {e}")
        return {"error": str(e), "success": False}


async def python_task_status_tool(task_id: str) -> dict[str, Any]:
    """Get status of a background Python task.

    Args:
        task_id: Task identifier

    Returns:
        Task status information
    """
    try:
        if not hasattr(python_run_background_tool, "_pool"):
            return {"error": "No background tasks running", "success": False}

        pool = python_run_background_tool._pool  # noqa: SLF001

        # Check worker status
        worker = pool._workers.get(task_id)  # noqa: SLF001
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

    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return {"error": str(e), "success": False}


async def python_task_cancel_tool(task_id: str) -> dict[str, Any]:
    """Cancel a background Python task.

    Args:
        task_id: Task identifier

    Returns:
        Cancellation result
    """
    try:
        if not hasattr(python_run_background_tool, "_pool"):
            return {"error": "No background tasks running", "success": False}

        pool = python_run_background_tool._pool  # noqa: SLF001

        # Release the worker (this will cancel the task)
        await pool.release_worker(task_id)

        return {
            "success": True,
            "task_id": task_id,
            "message": f"Task {task_id} cancelled",
        }

    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        return {"error": str(e), "success": False}


async def python_list_tasks_tool() -> dict[str, Any]:
    """List all background Python tasks.

    Returns:
        List of active tasks
    """
    try:
        if not hasattr(python_run_background_tool, "_pool"):
            return {
                "tasks": [],
                "message": "No background tasks running",
                "success": True,
            }

        pool = python_run_background_tool._pool  # noqa: SLF001

        tasks = []
        for worker_id, worker in pool._workers.items():  # noqa: SLF001
            tasks.append(
                {
                    "task_id": worker_id,
                    "state": worker.state.value,
                    "created_at": worker.created_at.isoformat(),
                    "task_count": worker.task_count,
                    "error_count": worker.error_count,
                }
            )

        return {
            "success": True,
            "tasks": tasks,
            "total": len(tasks),
            "pool_info": {
                "min_workers": pool.min_workers,
                "max_workers": pool.max_workers,
                "active_workers": len(pool._workers),  # noqa: SLF001
            },
        }

    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        return {"error": str(e), "success": False}
