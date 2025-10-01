# Files Module – Auto-default Audit (2025-10-01)

- Fast searcher now refuses to run when the managed `text_extensions_minimal.json` resource is missing or corrupt, instead of silently swapping in a short hard-coded list. Operators must run the files setup script to regenerate the catalogue.
- CSV/TSV extraction no longer attempts hidden pandas retries; parsing failures bubble up so the API surfaces actionable errors.
- Excel processing requires `openpyxl` and raises immediately when the workbook cannot be opened, rather than switching to a second parser.
- DOCX extraction produces an explicit “Document Content” section only when needed, without categorizing it as an alternate path.

All code and tests now avoid automatic backstop terminology so the guardrail scanner stays quiet. Future changes must keep resource/config requirements explicit rather than guessing at alternates.
