"""Convert BigCode extensions JSON to a simple text extensions list."""

import json
from pathlib import Path

from loguru import logger


def main() -> None:
    """Convert BigCode JSON to simple text extensions format."""
    # Read the BigCode JSON
    bigcode_path = Path(__file__).parent.parent / "res" / "bigcode_extensions.json"
    with bigcode_path.open() as f:
        bigcode_data = json.load(f)

    # Collect all unique extensions with their language
    extensions_map: dict[str, list[str]] = {}

    for language, extensions in bigcode_data.items():
        for ext in extensions:
            if ext not in extensions_map:
                extensions_map[ext] = []
            extensions_map[ext].append(language)

    # Create simple text extensions list
    text_extensions: dict[str, list[dict[str, str]]] = {}

    # Common text file categories
    text_extensions["programming"] = []
    text_extensions["markup"] = []
    text_extensions["config"] = []
    text_extensions["data"] = []
    text_extensions["documentation"] = []
    text_extensions["other"] = []

    # Categorize extensions
    for ext, languages in sorted(extensions_map.items()):
        lang_str = languages[0] if len(languages) == 1 else f"{languages[0]} and others"

        # Skip binary-like extensions
        if ext in [
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".o",
            ".a",
            ".lib",
            ".class",
            ".pyc",
            ".pyo",
        ]:
            continue

        # Categorize based on extension or language
        if ext in [".html", ".xml", ".svg", ".xhtml", ".xht", ".xaml"]:
            text_extensions["markup"].append(
                {"ext": ext, "desc": f"Markup ({lang_str})"}
            )
        elif ext in [
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".properties",
        ]:
            text_extensions["config"].append(
                {"ext": ext, "desc": f"Configuration ({lang_str})"}
            )
        elif ext in [".csv", ".tsv", ".sql", ".graphql"]:
            text_extensions["data"].append(
                {"ext": ext, "desc": f"Data format ({lang_str})"}
            )
        elif ext in [".md", ".markdown", ".rst", ".txt", ".asciidoc", ".adoc"]:
            text_extensions["documentation"].append(
                {"ext": ext, "desc": f"Documentation ({lang_str})"}
            )
        elif ext in [".diff", ".patch", ".log"]:
            text_extensions["other"].append(
                {"ext": ext, "desc": f"Other text ({lang_str})"}
            )
        else:
            # Most are programming languages
            text_extensions["programming"].append({"ext": ext, "desc": lang_str})

    # Create the final JSON structure
    all_extensions: list[str] = []
    output = {
        "description": "Text file extensions recognized for content searching",
        "categories": text_extensions,
        "all_extensions": all_extensions,
    }

    # Collect all extensions in a flat list
    for category in text_extensions.values():
        for item in category:
            if item["ext"] not in all_extensions:
                all_extensions.append(item["ext"])

    all_extensions.sort()

    # Write the output
    output_path = Path(__file__).parent.parent / "res" / "text_extensions.json"
    with output_path.open("w") as f:
        json.dump(output, f, indent=2, sort_keys=False)

    logger.info(f"Generated {output_path} with {len(all_extensions)} text extensions")

    # Also generate a minimal version with just the extensions list
    minimal = {
        "text_extensions": all_extensions,
        "description": "Minimal list of text file extensions for fast file search",
    }

    minimal_path = Path(__file__).parent.parent / "res" / "text_extensions_minimal.json"
    with minimal_path.open("w") as f:
        json.dump(minimal, f, indent=2)

    logger.info(f"Generated {minimal_path} with minimal extension list")


if __name__ == "__main__":
    main()
