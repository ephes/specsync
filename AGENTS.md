# Repository Guidelines

## Project Structure & Module Organization
- `src/specsync/` holds the CLI entry points, sync engine, configuration loader, and supporting utilities.
- `tests/` contains pytest-based unit suites that mirror the structure of `src/specsync`.
- `docs/` is a Sphinx + MyST documentation site; HTML output lives in `docs/_build/` (gitignored).
- `specs/` stores synchronized Markdown specifications pulled from external workspaces.
- Top-level helpers include `justfile` for repeatable tasks and `pyproject.toml` for packaging, dependency groups, and tooling configuration.

## Build, Test, and Development Commands
- ``just install`` — install all dependency groups via `uv`.
- ``just check`` — run lint, format check, and tests in one pass.
- ``just lint`` / ``just lint-fix`` — run Ruff (and autofix when requested).
- ``just format`` / ``just format-check`` — apply or verify formatting with Ruff.
- ``just test`` / ``just test-coverage`` — execute pytest suites, optionally with coverage reporting.
- ``just docs-build`` / ``just docs-serve`` / ``just docs-watch`` — build, preview, and live-reload the documentation site.

## Coding Style & Naming Conventions
- Python code targets 3.11+, uses 4-space indentation, and follows Ruff’s defaults for linting and formatting.
- Prefer descriptive module and function names (e.g., `sync_workspace`, `load_config_from_env`).
- Keep docstrings Google- or NumPy-style as required by Sphinx autodoc; include short summaries and parameter sections.

## Testing Guidelines
- Write tests with pytest; mirror `src/specsync/<module>` in `tests/<module>_test.py` or similar.
- Use `pytest.mark.parametrize` for table-driven scenarios and fixtures for shared setup.
- Run ``just test`` before opening a PR; use ``just test-coverage`` when validating larger changes.

## Commit & Pull Request Guidelines
- Current history starts with “Initial commit”; adopt short, imperative subject lines (e.g., “Add pull conflict resolver”).
- Squash trivial fixups before pushing. Reference related issues or specs in the description when applicable.
- PRs should describe motivation, summarize changes, link the relevant documentation/spec updates, and note manual test steps or screenshots if behavior changes.

## Documentation Workflow
- Update Markdown guides under `docs/` alongside feature work and run ``just docs-check`` to catch broken links.
- When architecture decisions change, refresh both `docs/architecture.md` and the root `ARCHITECTURE.md` summary.
