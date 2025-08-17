"""Tests for path validation with absolute and relative paths."""

import tempfile
from pathlib import Path

import pytest
from services.mcp.filesys.file_utils import FileUtils


class TestPathValidation:
    """Test path validation for both absolute and relative paths."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_relative_path_validation(self, temp_dir):
        """Test validation of relative paths."""
        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        # Validate relative path
        result = FileUtils.validate_file_path("test.txt", temp_dir)
        assert result == test_file
        assert result.exists()

    def test_nested_relative_path_validation(self, temp_dir):
        """Test validation of nested relative paths."""
        # Create nested structure
        nested_dir = temp_dir / "subdir" / "nested"
        nested_dir.mkdir(parents=True)
        test_file = nested_dir / "file.txt"
        test_file.write_text("content")

        # Validate nested relative path
        result = FileUtils.validate_file_path("subdir/nested/file.txt", temp_dir)
        assert result == test_file
        assert result.exists()

    def test_absolute_path_within_root(self, temp_dir):
        """Test validation of absolute paths within root directory."""
        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        # Use absolute path
        absolute_path = str(test_file.resolve())
        result = FileUtils.validate_file_path(absolute_path, temp_dir)
        assert result == test_file
        assert result.exists()

    def test_absolute_path_matching_structure(self, temp_dir):
        """Test validation of absolute paths that match root structure."""
        # Create a test file
        subdir = temp_dir / "myproject" / "src"
        subdir.mkdir(parents=True)
        test_file = subdir / "main.py"
        test_file.write_text("print('hello')")

        # Simulate a different absolute path with same structure
        # For example, user provides C:/other/path/myproject/src/main.py
        # when root is at temp_dir/myproject
        root_dir = temp_dir / "myproject"

        # This should work - absolute path within root
        result = FileUtils.validate_file_path(str(test_file.resolve()), root_dir)
        assert result == test_file

    def test_absolute_path_outside_root_with_matching_name(self, temp_dir):
        """Test handling of absolute paths outside root with matching directory name."""
        # Create the root structure
        root_name = "testproject"
        root_dir = temp_dir / root_name
        root_dir.mkdir()
        (root_dir / "src").mkdir()

        # Create a fake absolute path that has the same project name
        # This simulates user providing /other/path/testproject/src/file.py
        fake_path = f"/fake/path/{root_name}/src/file.py"

        # This should map to root_dir/src/file.py
        result = FileUtils.validate_file_path(fake_path, root_dir)
        expected = root_dir / "src" / "file.py"
        assert result == expected.resolve()

    def test_path_traversal_prevention(self, temp_dir):
        """Test that path traversal attempts are blocked."""
        # Try to escape root with ../
        with pytest.raises(ValueError) as exc_info:
            FileUtils.validate_file_path("../../../etc/passwd", temp_dir)
        assert "outside the allowed root directory" in str(exc_info.value)

    def test_absolute_path_no_match(self, temp_dir):
        """Test that absolute paths with no matching structure are rejected."""
        root_dir = temp_dir / "myproject"
        root_dir.mkdir()

        # Absolute path that doesn't match our root structure
        with pytest.raises(ValueError) as exc_info:
            FileUtils.validate_file_path(
                "/completely/different/path/file.txt", root_dir
            )
        assert "cannot be mapped to root directory" in str(exc_info.value)

    def test_validate_path_with_must_exist(self, temp_dir):
        """Test the validate_path method with must_exist flag."""
        # Create a test file
        test_file = temp_dir / "exists.txt"
        test_file.write_text("content")

        # Should work for existing file
        result = FileUtils.validate_path("exists.txt", temp_dir, must_exist=True)
        assert result == test_file

        # Should fail for non-existing file
        with pytest.raises(ValueError) as exc_info:
            FileUtils.validate_path("not_exists.txt", temp_dir, must_exist=True)
        assert "Path does not exist" in str(exc_info.value)

    def test_windows_style_paths(self, temp_dir):
        """Test handling of Windows-style paths."""
        # Create test structure
        subdir = temp_dir / "folder"
        subdir.mkdir()
        test_file = subdir / "file.txt"
        test_file.write_text("content")

        # Test with backslashes (Windows style)
        result = FileUtils.validate_file_path("folder\\file.txt", temp_dir)
        assert result == test_file.resolve()

    def test_mixed_separators(self, temp_dir):
        """Test handling of mixed path separators."""
        # Create test structure
        nested = temp_dir / "a" / "b" / "c"
        nested.mkdir(parents=True)
        test_file = nested / "file.txt"
        test_file.write_text("content")

        # Test with mixed separators
        result = FileUtils.validate_file_path("a\\b/c\\file.txt", temp_dir)
        assert result == test_file.resolve()

    def test_dot_notation_paths(self, temp_dir):
        """Test handling of paths with . and .. notation."""
        # Create test structure
        (temp_dir / "dir1").mkdir()
        (temp_dir / "dir2").mkdir()
        test_file = temp_dir / "dir2" / "file.txt"
        test_file.write_text("content")

        # Test with ./
        result = FileUtils.validate_file_path("./dir2/file.txt", temp_dir)
        assert result == test_file.resolve()

        # Test with complex navigation (but staying within root)
        result = FileUtils.validate_file_path("dir1/../dir2/file.txt", temp_dir)
        assert result == test_file.resolve()
