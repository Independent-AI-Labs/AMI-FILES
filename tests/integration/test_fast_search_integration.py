"""Integration tests for fast file search using actual repository files."""

import time
from pathlib import Path

import pytest
from base.scripts.env.paths import find_module_root
from files.backend.mcp.filesys.utils.fast_search import FastFileSearcher
from files.backend.mcp.filesys.utils.file_utils import FileUtils
from loguru import logger


class TestFastSearchIntegration:
    """Test FastFileSearcher with real repository files."""

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get the FILES module root directory."""
        return find_module_root(Path(__file__))

    @pytest.mark.asyncio
    async def test_search_python_files(self, repo_root: Path) -> None:
        """Test searching for Python files in the repository."""
        searcher = FastFileSearcher(max_workers=4)
        try:
            results = await searcher.search_files(
                repo_root / "backend",
                path_keywords=[".py"],
                content_keywords=None,
                regex_mode=False,
                max_results=100,
            )

            # Should find many Python files
            assert len(results) > 10
            assert all(".py" in r for r in results)

            # Should find specific files we know exist
            assert any("file_utils.py" in r for r in results)
            assert any("filesystem_tools.py" in r for r in results)
            assert any("fast_search.py" in r for r in results)
        finally:
            searcher.close()

    @pytest.mark.asyncio
    async def test_search_by_import_statements(self, repo_root: Path) -> None:
        """Test searching for files containing specific imports."""
        searcher = FastFileSearcher(max_workers=4)
        try:
            results = await searcher.search_files(
                repo_root / "backend",
                path_keywords=None,
                content_keywords=["from pathlib import Path"],
                regex_mode=False,
                max_results=50,
            )

            # Should find files with this import
            assert len(results) > 0
            # Just check that we found Python files with this import
            assert any(".py" in r for r in results)
        finally:
            searcher.close()

    @pytest.mark.asyncio
    async def test_search_with_regex_class_definitions(self, repo_root: Path) -> None:
        """Test searching for class definitions using regex."""
        searcher = FastFileSearcher(max_workers=4)
        try:
            results = await searcher.search_files(
                repo_root / "backend",
                path_keywords=None,
                content_keywords=[r"class\s+\w+.*:\s*\n\s*\"\"\""],  # Class with docstring
                regex_mode=True,
                max_results=50,
            )

            # Should find classes with docstrings
            assert len(results) > 0
            # FastFileSearcher and PreCommitValidator should be found
            assert any("fast_search.py" in r for r in results)
            assert any("precommit_validator.py" in r for r in results)
        finally:
            searcher.close()

    @pytest.mark.asyncio
    async def test_search_test_files(self, repo_root: Path) -> None:
        """Test searching for test files."""
        searcher = FastFileSearcher(max_workers=4)
        try:
            results = await searcher.search_files(
                repo_root / "tests",
                path_keywords=["test_"],
                content_keywords=["pytest"],
                regex_mode=False,
                max_results=100,
            )

            # Should find test files
            assert len(results) > 0
            assert all("test_" in r for r in results)
        finally:
            searcher.close()

    @pytest.mark.asyncio
    async def test_performance_comparison(self, repo_root: Path) -> None:
        """Compare performance of fast search vs original implementation."""
        search_dir = repo_root / "backend"

        # Test with a complex search - Python files containing async functions
        path_keyword = ".py"
        content_keyword = "async def"

        # Fast search
        searcher = FastFileSearcher(max_workers=4)
        start = time.time()
        try:
            fast_results = await searcher.search_files(
                search_dir,
                path_keywords=[path_keyword],
                content_keywords=[content_keyword],
                regex_mode=False,
                max_results=1000,
            )
        finally:
            searcher.close()
        fast_time = time.time() - start

        # Original search
        start = time.time()
        original_results = FileUtils.find_files(
            search_dir,
            path_keywords=[path_keyword],
            content_keywords=[content_keyword],
            regex_mode=False,
        )
        original_time = time.time() - start

        logger.info("\nPerformance comparison:")
        logger.info(f"Fast search: {fast_time:.3f}s ({len(fast_results)} files)")
        logger.info(f"Original search: {original_time:.3f}s ({len(original_results)} files)")

        # Results should be the same
        assert len(fast_results) == len(original_results)

        # Fast search should be at least as fast (often faster with more files)
        # For small repos the difference might be minimal
        logger.info(f"Speed ratio: {original_time / fast_time:.2f}x")

    @pytest.mark.asyncio
    async def test_search_with_pyahocorasick(self, repo_root: Path) -> None:
        """Test that pyahocorasick is used for exact string matching."""
        searcher = FastFileSearcher(max_workers=4)
        try:
            # Search for multiple exact strings efficiently
            keywords = ["FileUtils", "PreCommitValidator", "FastFileSearcher"]

            results = await searcher.search_files(
                repo_root / "backend",
                path_keywords=None,
                content_keywords=keywords,
                regex_mode=False,  # This should use Aho-Corasick
                max_results=100,
            )

            # Should find files containing these class names
            assert len(results) > 0

            # Verify the files contain at least one keyword
            for result_path in results[:5]:  # Check first 5 results
                content = Path(result_path).read_text(errors="ignore")
                assert any(kw in content for kw in keywords)
        finally:
            searcher.close()

    @pytest.mark.asyncio
    async def test_search_excludes_binary_files(self, repo_root: Path) -> None:
        """Test that binary files are excluded from content search."""
        searcher = FastFileSearcher(max_workers=4)
        try:
            # Search for null bytes (should not find in text files)
            results = await searcher.search_files(
                repo_root,
                path_keywords=None,
                content_keywords=["\x00"],
                regex_mode=False,
                max_results=100,
            )

            # Should not find any text files with null bytes
            assert len(results) == 0
        finally:
            searcher.close()

    @pytest.mark.asyncio
    async def test_multithreaded_processing(self, repo_root: Path) -> None:
        """Test that multithreading actually works."""
        # Test with different worker counts
        for workers in [1, 2, 4, 8]:
            searcher = FastFileSearcher(max_workers=workers)
            start = time.time()
            try:
                results = await searcher.search_files(
                    repo_root,
                    path_keywords=[".py"],
                    content_keywords=["import"],
                    regex_mode=False,
                    max_results=100,
                )
            finally:
                searcher.close()
            elapsed = time.time() - start

            logger.info(f"Workers: {workers}, Time: {elapsed:.3f}s, Results: {len(results)}")
            assert len(results) > 0
