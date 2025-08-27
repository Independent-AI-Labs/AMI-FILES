"""Fast multithreaded file search with pyahocorasick and regex optimization."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import ahocorasick
import regex
from loguru import logger


class FastFileSearcher:
    """Optimized file searcher using multithreading and fast pattern matching."""

    def __init__(self, max_workers: int = 8):
        """Initialize the fast searcher.

        Args:
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._load_text_extensions()

    def _load_text_extensions(self):
        """Load text file extensions from resource file."""
        try:
            res_path = (
                Path(__file__).parent.parent.parent.parent
                / "res"
                / "text_extensions_minimal.json"
            )
            if res_path.exists():
                with res_path.open() as f:
                    data = json.load(f)
                    self.text_extensions = set(data.get("text_extensions", []))
            else:
                # Fallback to basic set
                self.text_extensions = {
                    ".txt",
                    ".md",
                    ".py",
                    ".js",
                    ".json",
                    ".xml",
                    ".yaml",
                    ".yml",
                }
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load text extensions: {e}")
            self.text_extensions = {
                ".txt",
                ".md",
                ".py",
                ".js",
                ".json",
                ".xml",
                ".yaml",
                ".yml",
            }

    def _build_aho_corasick(self, keywords: list[str]) -> ahocorasick.Automaton:
        """Build Aho-Corasick automaton for exact string matching.

        Args:
            keywords: List of keywords to search for

        Returns:
            Built automaton for fast multi-pattern matching
        """
        automaton = ahocorasick.Automaton()
        for idx, key in enumerate(keywords):
            automaton.add_word(key, (idx, key))
        automaton.make_automaton()
        return automaton

    def _compile_regex_patterns(self, patterns: list[str]) -> list[regex.Pattern]:
        """Compile regex patterns using the faster 'regex' library.

        Args:
            patterns: List of regex patterns

        Returns:
            List of compiled regex patterns
        """
        compiled = []
        for pattern in patterns:
            try:
                # Use regex library which is faster than re for complex patterns
                compiled.append(regex.compile(pattern, regex.MULTILINE | regex.DOTALL))
            except regex.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        return compiled

    def _search_file_content(
        self,
        file_path: Path,
        automaton: ahocorasick.Automaton | None,
        regex_patterns: list[regex.Pattern] | None,
    ) -> bool:
        """Search file content using Aho-Corasick or regex.

        Args:
            file_path: Path to file to search
            automaton: Aho-Corasick automaton for exact matching
            regex_patterns: Compiled regex patterns

        Returns:
            True if any pattern matches
        """
        try:
            # Read file content
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            # Check with Aho-Corasick (exact matching)
            if automaton:
                for _ in automaton.iter(content):
                    return True

            # Check with regex patterns
            if regex_patterns:
                for pattern in regex_patterns:
                    if pattern.search(content):
                        return True

            return False

        except (OSError, UnicodeDecodeError) as e:
            logger.debug(f"Error reading file {file_path}: {e}")
            return False

    def _search_file_path(
        self,
        file_path: Path,
        automaton: ahocorasick.Automaton | None,
        regex_patterns: list[regex.Pattern] | None,
    ) -> bool:
        """Search file path using Aho-Corasick or regex.

        Args:
            file_path: Path to check
            automaton: Aho-Corasick automaton for exact matching
            regex_patterns: Compiled regex patterns

        Returns:
            True if path matches any pattern
        """
        path_str = str(file_path)

        # Check with Aho-Corasick (exact matching)
        if automaton:
            for _ in automaton.iter(path_str):
                return True

        # Check with regex patterns
        if regex_patterns:
            for pattern in regex_patterns:
                if pattern.search(path_str):
                    return True

        return False

    def _process_file_batch(
        self,
        files: list[Path],
        path_automaton: ahocorasick.Automaton | None,
        path_regex: list[regex.Pattern] | None,
        content_automaton: ahocorasick.Automaton | None,
        content_regex: list[regex.Pattern] | None,
        check_content: bool,
    ) -> list[str]:
        """Process a batch of files in a worker thread.

        Args:
            files: Batch of files to process
            path_automaton: Automaton for path matching
            path_regex: Regex patterns for path matching
            content_automaton: Automaton for content matching
            content_regex: Regex patterns for content matching
            check_content: Whether to check file content

        Returns:
            List of matching file paths
        """
        results = []

        for file_path in files:
            # Check path match
            path_match = False
            if path_automaton or path_regex:
                path_match = self._search_file_path(
                    file_path, path_automaton, path_regex
                )
                if not path_match and not check_content:
                    continue

            # Check content match
            content_match = False
            if check_content and (not (path_automaton or path_regex) or path_match):
                # Only check text files for content
                if self._is_text_file(file_path):
                    content_match = self._search_file_content(
                        file_path, content_automaton, content_regex
                    )

            # Add to results if matched
            if path_match or content_match:
                results.append(str(file_path))

        return results

    def _is_text_file(self, file_path: Path) -> bool:
        """Check if file is likely a text file.

        Args:
            file_path: Path to file

        Returns:
            True if file appears to be text
        """
        if file_path.suffix.lower() in self.text_extensions:
            return True

        # Check by reading first few bytes
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(512)
                # Check for null bytes (binary indicator)
                if b"\x00" in chunk:
                    return False
                # Try to decode as UTF-8
                try:
                    chunk.decode("utf-8")
                    return True
                except UnicodeDecodeError:
                    return False
        except OSError:
            return False

    async def search_files(
        self,
        directory: Path,
        path_keywords: list[str] | None = None,
        content_keywords: list[str] | None = None,
        regex_mode: bool = False,
        max_results: int = 10000,
    ) -> list[str]:
        """Search files using multithreading and optimized pattern matching.

        Args:
            directory: Directory to search in
            path_keywords: Keywords to match in file paths
            content_keywords: Keywords to match in file content
            regex_mode: Whether keywords are regex patterns
            max_results: Maximum number of results

        Returns:
            List of matching file paths
        """
        # Collect all files
        all_files = []
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    all_files.append(file_path)
                    if (
                        len(all_files) >= max_results * 2
                    ):  # Collect more to account for filtering
                        break
        except (OSError, PermissionError) as e:
            logger.warning(f"Error scanning directory {directory}: {e}")

        if not all_files:
            return []

        # Prepare pattern matchers
        path_automaton = None
        path_regex = None
        content_automaton = None
        content_regex = None

        if path_keywords:
            if regex_mode:
                path_regex = self._compile_regex_patterns(path_keywords)
            else:
                path_automaton = self._build_aho_corasick(path_keywords)

        if content_keywords:
            if regex_mode:
                content_regex = self._compile_regex_patterns(content_keywords)
            else:
                content_automaton = self._build_aho_corasick(content_keywords)

        # Split files into batches for parallel processing
        batch_size = max(1, len(all_files) // (self.max_workers * 4))
        batches = [
            all_files[i : i + batch_size] for i in range(0, len(all_files), batch_size)
        ]

        # Process batches in parallel
        loop = asyncio.get_event_loop()
        tasks = []
        for batch in batches:
            task = loop.run_in_executor(
                self.executor,
                self._process_file_batch,
                batch,
                path_automaton,
                path_regex,
                content_automaton,
                content_regex,
                bool(content_keywords),
            )
            tasks.append(task)

        # Gather results
        batch_results = await asyncio.gather(*tasks)

        # Combine and limit results
        all_results = []
        for batch_result in batch_results:
            all_results.extend(batch_result)
            if len(all_results) >= max_results:
                break

        return all_results[:max_results]

    def close(self):
        """Clean up the thread pool."""
        self.executor.shutdown(wait=False)
