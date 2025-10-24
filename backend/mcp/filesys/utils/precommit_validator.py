"""Pre-commit validation for file operations."""

import contextlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from files.backend.config.loader import files_config
from files.backend.mcp.filesys.utils.file_utils import FileUtils
from loguru import logger


def _get_precommit_executable() -> str:
    """Get absolute path to pre-commit executable.

    Returns:
        Absolute path to pre-commit command

    Raises:
        RuntimeError: If pre-commit is not found in PATH
    """
    precommit_path = shutil.which("pre-commit")
    if precommit_path is None:
        raise RuntimeError("pre-commit is not installed or not in PATH")
    return precommit_path


class PreCommitValidator:
    """Validates files using pre-commit hooks before writing."""

    def __init__(self) -> None:
        """Initialize the validator."""
        self.enabled: bool = True
        self.skip_on_missing: bool = True
        self.max_file_size_kb: int | float = files_config.get_max_file_size_kb()

    def _check_precommit_available(self) -> bool:
        """Check if pre-commit is installed and configured.

        Returns:
            True if pre-commit is available
        """
        try:
            # Check if pre-commit is installed
            precommit_exe = _get_precommit_executable()
            result = subprocess.run(
                [precommit_exe, "--version"],
                capture_output=True,
                text=True,
                timeout=files_config.get_precommit_timeout("version_check"),
                check=False,
            )
            if result.returncode != 0:
                return False

            # Check if .pre-commit-config.yaml exists in repo root
            # Walk up to find .git directory
            current = Path.cwd()
            while current != current.parent:
                if (current / ".git").exists():
                    return (current / ".pre-commit-config.yaml").exists()
                current = current.parent

            return False

        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"Pre-commit availability check failed: {e}")
            return False

    def _find_git_root(self) -> Path | None:
        """Find the git repository root.

        Returns:
            Path to git root or None if not in a git repo
        """
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        return None

    def should_validate_file(self, file_path: Path) -> bool:
        """Check if a file should be validated based on its extension.

        Args:
            file_path: Path to check

        Returns:
            True if file should be validated with pre-commit
        """
        # Only validate source code files
        return bool(FileUtils.is_source_code_file(file_path))

    def is_precommit_available(self) -> bool:
        """Check if pre-commit is available for use.

        Returns:
            True if pre-commit is available
        """
        return self._check_precommit_available()

    def find_git_root(self) -> Path | None:
        """Find the git repository root directory.

        Returns:
            Path to git root or None if not found
        """
        return self._find_git_root()

    def _prepare_validation(
        self,
        file_path: Path,
        content: str | bytes,
        encoding: str,
    ) -> tuple[dict[str, Any] | None, Path | None, bytes]:
        """Perform early validation checks that may short-circuit the workflow."""

        default_result = {"valid": True, "errors": [], "modified_content": content}
        content_bytes = content if isinstance(content, bytes) else content.encode(encoding)
        result: dict[str, Any] | None = None
        git_root: Path | None = None

        if not self.enabled:
            logger.debug("Pre-commit validation disabled; returning original content")
            result = default_result
        elif not self.should_validate_file(file_path):
            logger.debug(f"Skipping pre-commit validation for non-source file: {file_path}")
            result = default_result
        elif len(content_bytes) > self.max_file_size_kb * 1024:
            result = {
                "valid": True,
                "errors": ["File too large for pre-commit validation"],
                "modified_content": content,
            }
        elif not self._check_precommit_available():
            if self.skip_on_missing:
                logger.debug("Pre-commit not available, skipping validation")
                result = default_result
            else:
                result = {
                    "valid": False,
                    "errors": ["Pre-commit is not installed or configured"],
                    "modified_content": content,
                }
        else:
            git_root = self._find_git_root()
            if not git_root:
                result = {
                    "valid": True,
                    "errors": ["Not in a git repository"],
                    "modified_content": content,
                }

        return result, git_root, content_bytes

    def _write_temp_file(
        self,
        git_root: Path,
        file_path: Path,
        content: str | bytes,
    ) -> Path:
        """Write content to a temporary file accessible to pre-commit."""

        suffix = file_path.suffix if file_path else ".tmp"
        tmp_dir = git_root / ".precommit_tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="wb" if isinstance(content, bytes) else "w",
            suffix=suffix,
            delete=False,
            dir=tmp_dir,
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            if isinstance(content, bytes):
                tmp_file.write(content)
            else:
                tmp_file.write(content)
        return tmp_path

    @staticmethod
    def _collect_process_output(result: subprocess.CompletedProcess[str]) -> list[str]:
        """Extract stdout/stderr messages for diagnostics."""

        messages: list[str] = []
        if result.stdout:
            messages.append(result.stdout)
        if result.stderr:
            messages.append(result.stderr)
        return messages

    def _attempt_autofix(
        self,
        tmp_path: Path,
        rel_path: Path,
        git_root: Path,
        content: str | bytes,
        modified_content: str | bytes,
        encoding: str,
    ) -> tuple[bool, str | bytes, list[str]]:
        """Retry pre-commit after applying automatic fixes."""

        if modified_content == content or not tmp_path.exists():
            return False, modified_content, []

        if isinstance(modified_content, bytes):
            tmp_path.write_bytes(modified_content)
        else:
            tmp_path.write_text(modified_content, encoding=encoding)

        try:
            precommit_exe = _get_precommit_executable()
            recheck = subprocess.run(
                [precommit_exe, "run", "--files", str(rel_path)],
                cwd=git_root,
                capture_output=True,
                text=True,
                timeout=files_config.get_precommit_timeout("recheck_run"),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, modified_content, ["Pre-commit autofix timed out"]
        except subprocess.SubprocessError as error:
            return False, modified_content, [f"Pre-commit autofix failed: {error}"]

        if recheck.returncode == 0:
            return True, modified_content, ["Pre-commit hooks applied automatic fixes"]

        return False, modified_content, self._collect_process_output(recheck)

    def _execute_precommit(
        self,
        tmp_path: Path,
        git_root: Path,
        content: str | bytes,
        encoding: str,
    ) -> tuple[list[str], str | bytes, bool]:
        """Execute pre-commit and process its outcome."""

        errors: list[str] = []
        modified_content: str | bytes = content
        valid_override = False
        rel_path = tmp_path.relative_to(git_root)

        try:
            precommit_exe = _get_precommit_executable()
            result = subprocess.run(
                [precommit_exe, "run", "--files", str(rel_path)],
                cwd=git_root,
                capture_output=True,
                text=True,
                timeout=files_config.get_precommit_timeout("validation_run"),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ["Pre-commit validation timed out"], modified_content, valid_override
        except subprocess.SubprocessError as error:
            return [f"Pre-commit execution failed: {error}"], modified_content, valid_override

        if tmp_path.exists():
            modified_content = tmp_path.read_bytes() if isinstance(content, bytes) else tmp_path.read_text(encoding=encoding)

        if result.returncode == 0:
            return errors, modified_content, valid_override

        errors.extend(self._collect_process_output(result))
        valid_override, modified_content, autofix_messages = self._attempt_autofix(
            tmp_path,
            rel_path,
            git_root,
            content,
            modified_content,
            encoding,
        )
        errors.extend(autofix_messages)
        return errors, modified_content, valid_override

    def _run_precommit(
        self,
        git_root: Path,
        file_path: Path,
        content: str | bytes,
        encoding: str,
    ) -> tuple[list[str], str | bytes, bool]:
        """Run pre-commit against temporary content and capture results."""

        tmp_path = self._write_temp_file(git_root, file_path, content)
        try:
            return self._execute_precommit(tmp_path, git_root, content, encoding)
        finally:
            if tmp_path.exists():
                with contextlib.suppress(OSError):
                    tmp_path.unlink()

    async def validate_content(
        self,
        file_path: Path,
        content: str | bytes,
        encoding: str = "utf-8",
    ) -> dict[str, Any]:
        """Validate file content using pre-commit hooks.

        Args:
            file_path: Path where file will be written
            content: Content to validate
            encoding: File encoding

        Returns:
            Dict with validation results:
                - valid: bool indicating if validation passed
                - errors: List of error messages
                - modified_content: Content after hook fixes (if any)
        """
        early_result, git_root, _ = self._prepare_validation(file_path, content, encoding)
        if early_result is not None:
            return early_result
        if git_root is None:
            raise RuntimeError("Git root not found despite passing early validation")

        errors, modified_content, valid_override = self._run_precommit(
            git_root,
            file_path,
            content,
            encoding,
        )
        valid = valid_override or not errors
        return {
            "valid": valid,
            "errors": errors,
            "modified_content": modified_content if valid else content,
        }
