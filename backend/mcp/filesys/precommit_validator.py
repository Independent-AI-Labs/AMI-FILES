"""Pre-commit validation for file operations."""

import contextlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from loguru import logger


class PreCommitValidator:
    """Validates files using pre-commit hooks before writing."""

    def __init__(self, config_path: Path | None = None):
        """Initialize the validator.

        Args:
            config_path: Path to precommit config JSON
        """
        if config_path is None:
            config_path = Path(__file__).parent / "precommit_config.json"

        self.config = self._load_config(config_path)
        self.enabled = self.config.get("enabled", True)
        self.file_extensions = self.config.get("file_extensions", {})
        self.skip_on_missing = self.config.get("skip_on_missing_hook", True)
        self.max_file_size_kb = self.config.get("max_file_size_kb", 1024)

    def _load_config(self, config_path: Path) -> dict[str, Any]:
        """Load configuration from JSON file.

        Args:
            config_path: Path to config file

        Returns:
            Configuration dictionary
        """
        if not config_path.exists():
            logger.warning(f"Pre-commit config not found at {config_path}")
            return {"enabled": False}

        try:
            with config_path.open() as f:
                data: dict[str, Any] = json.load(f)
                return data
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load pre-commit config: {e}")
            return {"enabled": False}

    def _check_precommit_available(self) -> bool:
        """Check if pre-commit is installed and configured.

        Returns:
            True if pre-commit is available
        """
        try:
            # Check if pre-commit is installed
            result = subprocess.run(
                ["pre-commit", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
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

        except (subprocess.SubprocessError, FileNotFoundError):
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
        if not self.enabled:
            return {"valid": True, "errors": [], "modified_content": content}

        # Check file size
        content_bytes = (
            content if isinstance(content, bytes) else content.encode(encoding)
        )
        if len(content_bytes) > self.max_file_size_kb * 1024:
            return {
                "valid": True,
                "errors": ["File too large for pre-commit validation"],
                "modified_content": content,
            }

        # Check if pre-commit is available
        if not self._check_precommit_available():
            if self.skip_on_missing:
                logger.debug("Pre-commit not available, skipping validation")
                return {"valid": True, "errors": [], "modified_content": content}
            return {
                "valid": False,
                "errors": ["Pre-commit is not installed or configured"],
                "modified_content": content,
            }

        # Find git root
        git_root = self._find_git_root()
        if not git_root:
            return {
                "valid": True,
                "errors": ["Not in a git repository"],
                "modified_content": content,
            }

        # Create temporary file with the content
        suffix = file_path.suffix if file_path else ".tmp"
        errors = []
        modified_content = content
        tmp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb" if isinstance(content, bytes) else "w",
                suffix=suffix,
                delete=False,
                dir=git_root,  # Create in git root so pre-commit can find it
            ) as tmp_file:
                tmp_path = Path(tmp_file.name)

                # Write content
                if isinstance(content, bytes):
                    tmp_file.write(content)
                else:
                    tmp_file.write(content)

            # Run pre-commit on the temporary file
            try:
                # Get relative path from git root for pre-commit
                rel_path = tmp_path.relative_to(git_root)

                result = subprocess.run(
                    ["pre-commit", "run", "--files", str(rel_path)],
                    cwd=git_root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                # Check if hooks modified the file
                if tmp_path.exists():
                    if isinstance(content, bytes):
                        modified_content = tmp_path.read_bytes()
                    else:
                        modified_content = tmp_path.read_text(encoding=encoding)

                # pre-commit returns 0 if all hooks passed, 1 if any failed
                if result.returncode != 0:
                    # Parse errors from output
                    if result.stdout:
                        errors.append(result.stdout)
                    if result.stderr:
                        errors.append(result.stderr)

                    # Check if the file was modified (hooks may have fixed issues)
                    content_changed = modified_content != content

                    # If hooks fixed the issues, consider it valid with the fixed content
                    if content_changed:
                        # Re-run to check if fixes resolved all issues
                        if tmp_path.exists():
                            if isinstance(modified_content, bytes):
                                tmp_path.write_bytes(modified_content)
                            else:
                                tmp_path.write_text(modified_content, encoding=encoding)

                        recheck = subprocess.run(
                            ["pre-commit", "run", "--files", str(rel_path)],
                            cwd=git_root,
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )

                        if recheck.returncode == 0:
                            # Hooks fixed all issues
                            return {
                                "valid": True,
                                "errors": ["Pre-commit hooks applied automatic fixes"],
                                "modified_content": modified_content,
                            }

            except subprocess.TimeoutExpired:
                errors.append("Pre-commit validation timed out")
            except subprocess.SubprocessError as e:
                errors.append(f"Pre-commit execution failed: {e}")

        finally:
            # Clean up temporary file
            if tmp_path and tmp_path.exists():
                with contextlib.suppress(OSError):
                    tmp_path.unlink()

        valid = len(errors) == 0
        return {
            "valid": valid,
            "errors": errors,
            "modified_content": modified_content if valid else content,
        }
