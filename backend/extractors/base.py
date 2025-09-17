"""Base document extractor abstract class."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)
MIN_HEADING_LENGTH = 4
MAX_HEADING_LENGTH = 100
MAX_HEADING_LEVEL = 6
MAX_SAMPLE_ROWS = 10
BOOLEAN_VALUES = {"true", "false", "yes", "no", "1", "0", "t", "f", "y", "n"}
DATE_PATTERNS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M:%S",
)


class ExtractionResult(BaseModel):
    """Result of document extraction."""

    # Metadata
    file_path: str
    file_type: str
    file_size: int

    # Extracted content
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: list[str] = []
    language: str = "en"

    # Content sections
    sections: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []

    # Raw text
    full_text: str | None = None

    # Processing metadata
    extraction_method: str
    processing_time_ms: int
    error_messages: list[str] = []
    warnings: list[str] = []


class DocumentExtractor(ABC):
    """Abstract base class for document extractors."""

    def __init__(self) -> None:
        """Initialize the document extractor."""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def can_extract(self, file_path: Path) -> bool:
        """Check if this extractor can handle the given file."""

    @abstractmethod
    async def extract(
        self,
        file_path: Path,
        options: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        """Extract content from document."""

    async def validate_file(self, file_path: Path) -> None:
        """Validate file exists and is readable."""
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        if not file_path.is_file():
            msg = f"Not a file: {file_path}"
            raise ValueError(msg)

        if not file_path.stat().st_size:
            msg = f"File is empty: {file_path}"
            raise ValueError(msg)

        # Check file permissions
        try:
            with file_path.open("rb") as file_handle:
                file_handle.read(1)
        except PermissionError as e:
            msg = f"Cannot read file {file_path}: {e}"
            raise PermissionError(msg) from e
        except Exception:
            self.logger.exception(f"Error validating file {file_path}")
            raise

    def extract_sections_from_text(self, text: str) -> list[dict[str, Any]]:
        """Extract sections from plain text using common patterns"""
        sections = []
        lines = text.split("\n")
        current_section = None
        current_content: list[str] = []
        section_counter = 0

        for line in lines:
            # Check for heading patterns
            if self._is_heading(line):
                # Save previous section
                if current_section:
                    current_section["content"] = "\n".join(current_content).strip()
                    sections.append(current_section)

                # Start new section
                section_counter += 1
                current_section = {
                    "level": self._get_heading_level(line),
                    "title": self._clean_heading(line),
                    "order": section_counter,
                    "path": str(section_counter),
                }
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            current_section["content"] = "\n".join(current_content).strip()
            sections.append(current_section)

        # If no sections found, create a single section
        if not sections and text.strip():
            sections.append(
                {
                    "level": 1,
                    "title": "Document Content",
                    "content": text.strip(),
                    "order": 1,
                    "path": "1",
                }
            )

        return sections

    def _is_heading(self, line: str) -> bool:
        """Check if line looks like a heading"""
        line = line.strip()
        if not line:
            return False

        # Markdown headings
        if line.startswith("#"):
            return True

        # Numbered headings (1., 1.1, etc.)

        if re.match(r"^\d+(\.\d+)*\.?\s+\w", line):
            return True

        # All caps headings
        return bool(line.isupper() and MIN_HEADING_LENGTH < len(line) < MAX_HEADING_LENGTH)

    def _get_heading_level(self, line: str) -> int:
        """Determine heading level"""
        line = line.strip()

        # Markdown headings
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            return min(level, MAX_HEADING_LEVEL)

        # Numbered headings

        match = re.match(r"^(\d+(?:\.\d+)*)", line)
        if match:
            parts = match.group(1).split(".")
            return min(len(parts), MAX_HEADING_LEVEL)

        # Default to level 2 for other headings
        return 2

    def _clean_heading(self, line: str) -> str:
        """Clean heading text"""
        stripped = line.strip()
        without_markdown = stripped.lstrip("#").strip()
        return re.sub(r"^\d+(\.\d+)*\.?\s+", "", without_markdown)

    def infer_table_schema(self, headers: list[str], rows: list[dict[str, Any]]) -> dict[str, str]:
        """Infer data types for table columns"""
        schema = {}
        for header in headers:
            values = self._sample_column_values(rows, header)
            schema[header] = self._infer_column_type(values)
        return schema

    def _sample_column_values(self, rows: list[dict[str, Any]], header: str) -> list[Any]:
        """Collect representative non-null samples for a column."""
        return [row.get(header) for row in rows[:MAX_SAMPLE_ROWS] if row.get(header) is not None]

    def _infer_column_type(self, values: list[Any]) -> str:
        """Infer a column data type from sampled values."""
        if not values:
            return "text"

        if self._is_numeric_column(values):
            return "float" if self._has_decimal(values) else "integer"

        if self._is_datetime_column(values):
            return "datetime"

        if self._is_boolean_column(values):
            return "boolean"

        return "text"

    def _is_numeric_column(self, values: list[Any]) -> bool:
        """Return True if all values can be treated as numbers."""
        try:
            return all(isinstance(value, int | float) or str(value).replace(".", "").replace("-", "").isdigit() for value in values)
        except Exception:  # pragma: no cover - defensive guard
            logger.debug("Failed to detect numeric type, treating as text")
            return False

    def _has_decimal(self, values: list[Any]) -> bool:
        """Check whether any sampled numeric value contains decimal precision."""
        return any("." in str(value) for value in values)

    def _is_datetime_column(self, values: list[Any]) -> bool:
        """Return True if values match a known datetime pattern."""
        return any(self._all_values_match_datetime(values, pattern) for pattern in DATE_PATTERNS)

    def _all_values_match_datetime(self, values: list[Any], pattern: str) -> bool:
        """Check whether all values match the supplied datetime pattern."""
        for value in values:
            text = str(value)
            if not text:
                return False
            try:
                datetime.strptime(text, pattern).replace(tzinfo=UTC)
            except ValueError:
                return False
        return True

    def _is_boolean_column(self, values: list[Any]) -> bool:
        """Return True if values map cleanly to boolean representations."""
        return all(str(value).lower() in BOOLEAN_VALUES for value in values)
