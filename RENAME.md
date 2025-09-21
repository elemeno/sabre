# Project Rename Plan: SABER ➜ SABRE

## Objectives
- Update all code, documentation, and configuration references from "SABER" to "SABRE" while preserving existing behaviour.
- Maintain compatibility where external users or scripts may still rely on the legacy name.
- Validate that packaging, tooling, and CI workflows continue to function after the rename.

## Action Plan
1. **Inventory Current Usage**
   - Use search tools (e.g., `rg "SABER"`) to catalogue occurrences across source code, documentation, configs, package metadata, and tests.
   - Identify case-sensitive variants (e.g., `Saber`, `saber`) and determine desired replacements (`Sabre`, `sabre`).

2. **Decide Naming Conventions**
   - Confirm canonical casing for the new brand (e.g., "SABRE" for all-caps brand, "Sabre" for product references, `sabre` for module/package names).
   - Document any exceptions (e.g., if Python package name remains `saber` for compatibility).

3. **Update Core Package & Modules**
   - Rename top-level package directories if required (e.g., `src/saber/` → `src/sabre/`).
   - Adjust `pyproject.toml`, `__init__.py`, and import paths to reflect the new module name.
   - Provide compatibility shims (e.g., `src/saber/__init__.py` re-exporting `sabre`) to avoid breaking downstream imports during transition.

4. **Revise Configuration & Schema References**
   - Update JSON schema IDs, config file comments, and sample YAML files to use the new name.
   - Ensure CLI help text, logging prefixes, and runtime metadata report "SABRE".

5. **Documentation & Branding**
   - Rewrite README, docs, and marketing materials to reference the new name.
   - Update badges, repository description, and any diagrams or images that embed the old name.

6. **Tooling & CI**
   - Adjust scripts, CI workflows, and packaging metadata (e.g., wheel name, console entry points) to the new branding.
   - Verify that packaging commands (`uv build`, `uv publish`, etc.) produce artifacts with the desired names.

7. **Testing & Validation**
   - Run the full test suite and linting to catch path/import regressions.
   - Perform manual smoke tests of the CLI to ensure entry points resolve after package renames.

8. **Migration Support**
   - Communicate the rename in CHANGELOG or release notes, highlighting compatibility shims and deprecation timelines.
   - Optionally add warnings when legacy module paths (`import saber`) are used, guiding users to the new namespace.

9. **Cleanup**
   - After sufficient deprecation period, remove legacy compatibility code.
   - Archive the rename plan with outcomes for future reference.

## Dependencies & Risks
- Renaming the Python package directory impacts all imports; must be coordinated carefully.
- External integrations (pip installs, config repos) may break if the package name changes abruptly.
- Existing virtual environments may need recreation.
