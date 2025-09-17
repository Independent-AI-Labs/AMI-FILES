"""Enhanced file content formatter with line numbers and better display."""


class FileFormatter:
    """Format file content for better readability in MCP responses."""

    @staticmethod
    def format_with_line_numbers(
        content: str,
        start_line: int = 1,
        highlight_lines: list[int] | None = None,
    ) -> str:
        """Format content with line numbers.

        Args:
            content: The file content to format
            start_line: Starting line number (1-based)
            highlight_lines: Optional list of line numbers to highlight

        Returns:
            Formatted content with line numbers
        """
        lines = content.split("\n")
        formatted_lines = []
        max_line_num = start_line + len(lines) - 1
        padding = len(str(max_line_num))

        for i, line in enumerate(lines):
            line_num = start_line + i
            # Add marker for highlighted lines
            marker = ">" if highlight_lines and line_num in highlight_lines else " "
            formatted_line = f"{marker}{line_num:>{padding}} | {line}"
            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)

    @staticmethod
    def format_diff_style(old_content: str, new_content: str) -> str:
        """Format content changes in diff style.

        Args:
            old_content: Original content
            new_content: Modified content

        Returns:
            Diff-style formatted changes
        """
        old_lines = old_content.split("\n")
        new_lines = new_content.split("\n")

        formatted = []
        formatted.append("--- Original")
        formatted.append("+++ Modified")
        formatted.append("=" * 40)

        # Simple line-by-line comparison (not a full diff algorithm)
        max_lines = max(len(old_lines), len(new_lines))

        for i in range(max_lines):
            old_line = old_lines[i] if i < len(old_lines) else None
            new_line = new_lines[i] if i < len(new_lines) else None

            if old_line == new_line:
                if old_line is not None:
                    formatted.append(f"  {i + 1:3} | {old_line}")
            else:
                if old_line is not None:
                    formatted.append(f"- {i + 1:3} | {old_line}")
                if new_line is not None:
                    formatted.append(f"+ {i + 1:3} | {new_line}")

        return "\n".join(formatted)

    @staticmethod
    def format_search_results(file_path: str, content: str, search_term: str, context_lines: int = 2) -> str:
        """Format search results with context.

        Args:
            file_path: Path to the file
            content: File content
            search_term: Term that was searched
            context_lines: Number of context lines to show

        Returns:
            Formatted search results with context
        """
        lines = content.split("\n")
        results = []
        results.append(f"=== {file_path} ===")

        for i, line in enumerate(lines):
            if search_term.lower() in line.lower():
                # Show context
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)

                if start > 0:
                    results.append("  ...")

                for j in range(start, end):
                    line_num = j + 1
                    if j == i:
                        # Highlight the matching line
                        results.append(f"> {line_num:4} | {lines[j]}")
                    else:
                        results.append(f"  {line_num:4} | {lines[j]}")

                if end < len(lines):
                    results.append("  ...")

                results.append("")  # Empty line between matches

        return "\n".join(results)
