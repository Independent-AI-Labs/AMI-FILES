# Files Module - Setup Contract

- The module delegates environment provisioning to `base/module_setup.py` via
  `files/module_setup.py`. This ensures venv creation, dependency installation,
  and hook configuration stay consistent across AMI modules.
- `module_setup.py` intentionally avoids third-party imports before the venv is
  ready; it relies solely on the Python standard library (`logging`,
  `subprocess`, `pathlib`).
- Any additional bootstrap logic must be added to the base setup layer to keep
  module setup behaviour uniform.

## References
- Orchestrator contract: `../docs/Setup-Contract.md`
- Base setup utilities: `base/backend/utils/{path_finder.py,environment_setup.py,path_utils.py}`
