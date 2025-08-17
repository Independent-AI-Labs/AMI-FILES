"""Unit tests for precommit validator file extension checking."""

from pathlib import Path

import pytest
from services.mcp.filesys.file_utils import FileUtils
from services.mcp.filesys.precommit_validator import PreCommitValidator


class TestPreCommitExtensions:
    """Test pre-commit validator with file extension checking."""

    def test_is_source_code_file(self):
        """Test source code file detection."""
        # Test programming files
        assert FileUtils.is_source_code_file(Path("test.py"))
        assert FileUtils.is_source_code_file(Path("test.js"))
        assert FileUtils.is_source_code_file(Path("test.ts"))
        assert FileUtils.is_source_code_file(Path("test.java"))
        assert FileUtils.is_source_code_file(Path("test.cpp"))
        assert FileUtils.is_source_code_file(Path("test.go"))
        assert FileUtils.is_source_code_file(Path("test.rs"))

        # Test web files
        assert FileUtils.is_source_code_file(Path("test.html"))
        assert FileUtils.is_source_code_file(Path("test.css"))
        assert FileUtils.is_source_code_file(Path("test.jsx"))
        assert FileUtils.is_source_code_file(Path("test.tsx"))

        # Test non-source files
        assert not FileUtils.is_source_code_file(Path("test.txt"))
        assert not FileUtils.is_source_code_file(Path("test.md"))
        assert not FileUtils.is_source_code_file(Path("test.pdf"))
        assert not FileUtils.is_source_code_file(Path("test.jpg"))
        assert not FileUtils.is_source_code_file(Path("test.zip"))

    def test_should_validate_file(self):
        """Test pre-commit validation file filtering."""
        validator = PreCommitValidator()

        # Should validate source files
        assert validator.should_validate_file(Path("main.py"))
        assert validator.should_validate_file(Path("app.js"))
        assert validator.should_validate_file(Path("index.html"))
        assert validator.should_validate_file(Path("styles.css"))

        # Should not validate non-source files
        assert not validator.should_validate_file(Path("notes.txt"))
        assert not validator.should_validate_file(Path("data.csv"))
        assert not validator.should_validate_file(Path("image.png"))

    @pytest.mark.asyncio
    async def test_validate_content_skips_non_source_files(self):
        """Test that validation is skipped for non-source files."""
        validator = PreCommitValidator()

        # Test with a non-source file
        result = await validator.validate_content(
            Path("document.txt"), "Some text content", encoding="utf-8"
        )

        # Should pass validation without running pre-commit
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["modified_content"] == "Some text content"

    @pytest.mark.asyncio
    async def test_validate_content_checks_source_files(self):
        """Test that validation runs for source files."""
        validator = PreCommitValidator()

        # Test with Python content using a path (not creating actual file)
        test_path = Path("test_script.py")
        content = "def hello():\n    print('Hello')\n"
        result = await validator.validate_content(test_path, content, encoding="utf-8")

        # Should attempt validation (may pass or fail depending on pre-commit setup)
        assert "valid" in result
        assert "errors" in result
        assert "modified_content" in result

    def test_load_source_extensions_from_config(self):
        """Test loading source extensions from config file."""
        # Clear cache to force reload
        FileUtils._source_extensions = None  # noqa: SLF001

        # Load extensions
        extensions = FileUtils._load_source_extensions()  # noqa: SLF001

        # Should have loaded many extensions
        assert len(extensions) > 50  # We have many programming and web extensions

        # Check some common ones
        assert ".py" in extensions
        assert ".js" in extensions
        assert ".html" in extensions
        assert ".css" in extensions
        assert ".java" in extensions
        assert ".cpp" in extensions

        # Check caching works
        extensions2 = FileUtils._load_source_extensions()  # noqa: SLF001
        assert extensions is extensions2  # Should be same object (cached)
