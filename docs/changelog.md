# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Changed
- N/A (Initial release)

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A
