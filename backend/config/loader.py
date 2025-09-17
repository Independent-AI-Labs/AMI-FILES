"""Configuration loader for files backend settings."""

import os
from pathlib import Path
from typing import Any, cast

import yaml
from loguru import logger

# Find the config file
CONFIG_PATH = Path(__file__).parent / "settings.yaml"


class FilesConfigLoader:
    """Load and manage files backend configurations from YAML."""

    _instance = None

    def __new__(cls) -> "FilesConfigLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self.config_path = CONFIG_PATH
            self._config: dict[str, Any] | None = None
            self._load_config()
            self._initialized = True

    def _load_config(self) -> None:
        """Load the YAML configuration with environment variable substitution."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            self._config = self._get_default_config()
            return

        try:
            with self.config_path.open() as f:
                content = f.read()

            # Expand environment variables
            content = os.path.expandvars(content)

            config = yaml.safe_load(content)
            if config is None:
                logger.warning(f"Invalid or empty configuration file: {self.config_path}, using defaults")
                self._config = self._get_default_config()
                return

            # Merge with defaults to ensure all required keys exist
            self._config = self._merge_with_defaults(config)
            logger.debug(f"Loaded configuration from {self.config_path}")

        except Exception as e:
            logger.error(f"Error loading config file {self.config_path}: {e}, using defaults")
            self._config = self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration values."""
        return {
            "precommit": {
                "timeouts": {
                    "version_check": 5,
                    "validation_run": 30,
                    "recheck_run": 30,
                },
                "file_limits": {
                    "max_file_size_kb": 1024,
                },
            },
            "file_utils": {
                "limits": {
                    "max_file_size": 104857600,  # 100MB
                }
            },
            "python_tools": {
                "timeouts": {
                    "worker_acquire": 30,
                    "execution_default": 300,
                },
                "workers": {
                    "min_workers": 1,
                    "max_workers": 5,
                },
            },
            "filesystem": {
                "encoding": {
                    "default": "utf-8",
                },
                "chunk_sizes": {
                    "read_buffer": 8192,
                },
            },
        }

    def _merge_with_defaults(self, config: dict[str, Any]) -> dict[str, Any]:
        """Merge loaded config with defaults to ensure all keys exist."""
        defaults = self._get_default_config()

        def merge_dicts(default: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
            """Recursively merge dictionaries."""
            result = default.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dicts(result[key], value)
                else:
                    result[key] = value
            return result

        return merge_dicts(defaults, config)

    def get_precommit_config(self) -> dict[str, Any]:
        """Get pre-commit configuration."""
        if self._config is None:
            return cast(dict[str, Any], self._get_default_config()["precommit"])
        return cast(dict[str, Any], self._config.get("precommit", {}))

    def get_file_utils_config(self) -> dict[str, Any]:
        """Get file utilities configuration."""
        if self._config is None:
            return cast(dict[str, Any], self._get_default_config()["file_utils"])
        return cast(dict[str, Any], self._config.get("file_utils", {}))

    def get_python_tools_config(self) -> dict[str, Any]:
        """Get Python tools configuration."""
        if self._config is None:
            return cast(dict[str, Any], self._get_default_config()["python_tools"])
        return cast(dict[str, Any], self._config.get("python_tools", {}))

    def get_filesystem_config(self) -> dict[str, Any]:
        """Get filesystem configuration."""
        if self._config is None:
            return cast(dict[str, Any], self._get_default_config()["filesystem"])
        return cast(dict[str, Any], self._config.get("filesystem", {}))

    # Convenience methods for specific values
    def get_precommit_timeout(self, timeout_type: str) -> int:
        """Get specific pre-commit timeout value."""
        config = self.get_precommit_config()
        return cast(int, config.get("timeouts", {}).get(timeout_type, 30))

    def get_max_file_size_kb(self) -> int:
        """Get maximum file size for pre-commit validation in KB."""
        config = self.get_precommit_config()
        return cast(int, config.get("file_limits", {}).get("max_file_size_kb", 1024))

    def get_max_file_size_bytes(self) -> int:
        """Get maximum file size for general processing in bytes."""
        config = self.get_file_utils_config()
        return cast(int, config.get("limits", {}).get("max_file_size", 104857600))

    def get_python_timeout(self, timeout_type: str) -> int:
        """Get specific Python tools timeout value."""
        config = self.get_python_tools_config()
        return cast(int, config.get("timeouts", {}).get(timeout_type, 30))

    def get_worker_config(self) -> dict[str, int]:
        """Get worker pool configuration."""
        config = self.get_python_tools_config()
        return cast(dict[str, int], config.get("workers", {"min_workers": 1, "max_workers": 5}))


# Singleton instance
files_config = FilesConfigLoader()
