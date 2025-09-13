# Files Module — Setup Contract

Delegation
- Use Base `AMIModuleSetup` from `base/module_setup.py` to provision `.venv`, install Base + Files requirements, and set up hooks.

Entrypoints
- Module-specific runner may be provided; if present, it owns all path/import setup. Otherwise, start servers programmatically.

Known deviations (to correct)
- `module_setup.py` imports `loguru` at top-level before venv creation. Replace with stdlib `logging` during setup or defer imports until after deps are installed.

Policy references
- Orchestrator contract: `/docs/Setup-Contract.md`
- Base setup utilities: `base/backend/utils/{path_finder.py, environment_setup.py, path_utils.py}`
