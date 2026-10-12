# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Dry-run no longer creates missing repository directories; missing sources are diagnosed with an empty plan.
- Init parses and preserves existing TOML tables, settings and comments, adds missing defaults, and replaces validated configuration atomically.
- Repository specs directories now follow CLI → environment → TOML → default precedence for both init and sync.
- `repo_specs_dir` and `workspace_subdir` are validated by one check for every source (stored TOML, environment, CLI): they must be relative subdirectories without `..` that stay inside the repository or workspace root. Invalid stored or environment values are reported even when `--repo-specs-dir` overrides them. Absolute paths are no longer accepted for these settings.
- A clean `push` no longer shows up as a `CONFLICT` on the next `push` or `pull`: plans now compare
  against the payload push actually writes (including injected `expose`/`project` frontmatter).
- `pull --force` right after a `push` no longer writes the workspace's injected frontmatter into the repo.

### Security
- Symlinked destinations are refused instead of followed: a symlinked destination file, intermediate
  directory or backup path is planned as `UNSAFE`, skipped, and makes the run exit with status 1.
- Atomic writes use an exclusive temp file instead of a predictable `<file>.tmp` path.
- Overwriting an existing destination first copies it to `<file>.specsync-bak`; if that backup cannot be written, the file is not overwritten.

### Added
- **Core CLI Application**
  - `specsync init` command to initialize a repository with specs directory
  - `specsync pull` command to sync specs from workspace to repository
  - `specsync push` command to sync specs from repository to workspace
  - `specsync info` command to display current configuration
  - Support for `--dry-run`, `--force`, and `--quiet` flags

- **Sync Engine**
  - Bidirectional file synchronization with conflict detection
  - Interactive conflict resolution with diff display
  - Atomic file operations to prevent data corruption
  - Hash-based change detection for efficient syncing
  - Dry-run mode for previewing changes

- **Configuration System**
  - Hierarchical configuration (CLI flags → environment variables → pyproject.toml)
  - Support for environment variables with `SPECSYNC_` prefix
  - Automatic project name detection from git repository
  - Configurable workspace paths and subdirectories
  - Example `.envrc` file for direnv integration

- **Frontmatter Filtering**
  - YAML frontmatter parsing for selective sync
  - Filter by `expose: true` flag in frontmatter
  - Optional project name matching via `project:` field
  - Support for both delimited and non-delimited frontmatter

- **Documentation**
  - Comprehensive README with quick start guide
  - Sphinx-based documentation site with Furo theme
  - Installation, usage, and configuration guides
  - Architecture documentation with design decisions
  - API reference documentation
  - Read the Docs configuration
  - CLAUDE.md for AI assistant guidance
  - AGENTS.md with repository guidelines

- **Development Tooling**
  - Justfile with common development commands
  - Comprehensive test suite with pytest
  - Code coverage tracking
  - Ruff integration for linting and formatting
  - Python 3.11+ support with type hints
  - UV package manager integration

- **Testing**
  - Unit tests for all core modules
  - Integration tests for sync workflows
  - Test fixtures for temporary directories
  - Parametrized tests for edge cases
  - 100% test coverage target

- **Continuous Integration**
  - GitHub Actions workflow running `ruff check`, `ruff format --check` and `pytest` on Python 3.11 and 3.13 (actions pinned by
    SHA, `permissions: contents: read`)

### Changed
- Normalize the Python formatting baseline to match the required nonwriting format check in `just check` and CI.

### Deprecated
- N/A

### Removed
- N/A
