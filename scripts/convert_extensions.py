"""Convert BigCode extensions JSON to a simple text extensions list."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import cast

from loguru import logger

BINARY_EXTENSIONS: set[str] = {
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
}

CATEGORY_RULES: dict[str, set[str]] = {
    "markup": {".html", ".xml", ".svg", ".xhtml", ".xht", ".xaml"},
    "config": {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".properties"},
    "data": {".csv", ".tsv", ".sql", ".graphql"},
    "documentation": {".md", ".markdown", ".rst", ".txt", ".asciidoc", ".adoc"},
    "other": {".diff", ".patch", ".log"},
}

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "markup": "Markup ({lang})",
    "config": "Configuration ({lang})",
    "data": "Data format ({lang})",
    "documentation": "Documentation ({lang})",
    "other": "Other text ({lang})",
    "programming": "{lang}",
}

# Find module root
_current = Path(__file__).resolve()
while _current != _current.parent:
    if (_current / "res").exists():
        RESOURCE_DIR = _current / "res"
        break
    _current = _current.parent
else:
    raise FileNotFoundError("Could not find res/ directory")

BIGCODE_JSON = RESOURCE_DIR / "bigcode_extensions.json"
TEXT_EXTENSIONS_JSON = RESOURCE_DIR / "text_extensions.json"
MINIMAL_TEXT_EXTENSIONS_JSON = RESOURCE_DIR / "text_extensions_minimal.json"


def load_bigcode_extensions() -> dict[str, list[str]]:
    """Load the BigCode extensions manifest."""

    with BIGCODE_JSON.open() as handle:
        data = json.load(handle)
    return cast(dict[str, list[str]], data)


def build_extension_index(bigcode_data: Mapping[str, Iterable[str]]) -> dict[str, set[str]]:
    """Create a mapping of extension -> languages that use it."""

    extension_map: dict[str, set[str]] = defaultdict(set)
    for language, extensions in bigcode_data.items():
        for ext in extensions:
            extension_map[ext].add(language)
    return extension_map


def categorise_extension(ext: str) -> str:
    """Determine the category for a given extension."""

    for category, candidates in CATEGORY_RULES.items():
        if ext in candidates:
            return category
    return "programming"


def language_summary(languages: Iterable[str]) -> str:
    """Provide a short human-readable summary for language usage."""

    ordered = sorted(languages)
    if not ordered:
        return "unknown"
    if len(ordered) == 1:
        return ordered[0]
    return f"{ordered[0]} and others"


def build_extension_payload(extension_map: dict[str, set[str]]) -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    """Build structured category data and a flat extension list."""

    text_extensions: dict[str, list[dict[str, str]]] = {
        "programming": [],
        "markup": [],
        "config": [],
        "data": [],
        "documentation": [],
        "other": [],
    }
    all_extensions: list[str] = []

    for ext in sorted(extension_map):
        if ext in BINARY_EXTENSIONS:
            continue

        category = categorise_extension(ext)
        summary = language_summary(extension_map[ext])
        description_template = CATEGORY_DESCRIPTIONS[category]
        entry = {"ext": ext, "desc": description_template.format(lang=summary)}

        text_extensions[category].append(entry)
        if ext not in all_extensions:
            all_extensions.append(ext)

    all_extensions.sort()
    return text_extensions, all_extensions


def write_json(path: Path, payload: object) -> None:
    """Write JSON payload with formatting."""

    with path.open("w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)


def main() -> None:
    """Convert BigCode JSON to simple text extensions format."""

    bigcode_data = load_bigcode_extensions()
    extension_map = build_extension_index(bigcode_data)
    categories, flat_list = build_extension_payload(extension_map)

    structured_payload = {
        "description": "Text file extensions recognized for content searching",
        "categories": categories,
        "all_extensions": flat_list,
    }
    write_json(TEXT_EXTENSIONS_JSON, structured_payload)
    logger.info("Generated %s with %d text extensions", TEXT_EXTENSIONS_JSON, len(flat_list))

    minimal_payload = {
        "text_extensions": flat_list,
        "description": "Minimal list of text file extensions for fast file search",
    }
    write_json(MINIMAL_TEXT_EXTENSIONS_JSON, minimal_payload)
    logger.info("Generated %s with minimal extension list", MINIMAL_TEXT_EXTENSIONS_JSON)


if __name__ == "__main__":
    main()
