"""Base document extractor abstract class."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


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
            with open(file_path, "rb") as f:
                f.read(1)
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
        import re

        if re.match(r"^\d+(\.\d+)*\.?\s+\w", line):
            return True

        # All caps headings
        return bool(line.isupper() and len(line) > 3 and len(line) < 100)

    def _get_heading_level(self, line: str) -> int:
        """Determine heading level"""
        line = line.strip()

        # Markdown headings
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            return min(level, 6)

        # Numbered headings
        import re

        match = re.match(r"^(\d+(?:\.\d+)*)", line)
        if match:
            parts = match.group(1).split(".")
            return min(len(parts), 6)

        # Default to level 2 for other headings
        return 2

    def _clean_heading(self, line: str) -> str:
        """Clean heading text"""
        line = line.strip()

        # Remove markdown markers
        line = line.lstrip("#").strip()

        # Remove numbering
        import re

        line = re.sub(r"^\d+(\.\d+)*\.?\s+", "", line)

        return line

    def infer_table_schema(
        self, headers: list[str], rows: list[dict[str, Any]]
    ) -> dict[str, str]:
        """Infer data types for table columns"""
        schema = {}

        for header in headers:
            # Sample values from column
            values = [
                row.get(header) for row in rows[:10] if row.get(header) is not None
            ]

            if not values:
                schema[header] = "text"
                continue

            # Try to infer type
            data_type = "text"

            # Check for numbers
            try:
                all_numbers = all(
                    isinstance(v, (int, float))
                    or str(v).replace(".", "").replace("-", "").isdigit()
                    for v in values
                )
                if all_numbers:
                    has_decimal = any("." in str(v) for v in values)
                    data_type = "float" if has_decimal else "integer"
            except Exception:
                logger.debug("Failed to detect numeric type, treating as text")

            # Check for dates
            if data_type == "text":
                from datetime import datetime

                date_patterns = [
                    "%Y-%m-%d",
                    "%m/%d/%Y",
                    "%d/%m/%Y",
                    "%Y/%m/%d",
                    "%Y-%m-%d %H:%M:%S",
                ]

                for pattern in date_patterns:
                    try:
                        all_dates = all(
                            datetime.strptime(str(v), pattern)  # noqa: DTZ007
                            is not None
                            for v in values
                            if v
                        )
                        if all_dates:
                            data_type = "datetime"
                            break
                    except Exception:
                        logger.debug(f"Date pattern {pattern} did not match")

            # Check for booleans
            if data_type == "text":
                bool_values = {
                    "true",
                    "false",
                    "yes",
                    "no",
                    "1",
                    "0",
                    "t",
                    "f",
                    "y",
                    "n",
                }
                all_bools = all(str(v).lower() in bool_values for v in values)
                if all_bools:
                    data_type = "boolean"

            schema[header] = data_type

        return schema
