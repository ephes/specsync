# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SpecSync is a Python CLI tool that synchronizes Markdown files with YAML frontmatter between a git repository's ignored `specs/` folder and an external workspace (e.g., Obsidian vault, Hugo content directory). It uses frontmatter metadata (`expose: true` and optional `project:` field) to determine which files to sync.

## Development Commands

call just --list to get a list of all commands.
most important ones are
just test
just build

## Architecture

The codebase follows a modular design with clear separation of concerns:

- **CLI Layer** (`cli.py`): Argparse-based command interface, dispatches to sync operations
- **Configuration** (`config.py`): Hierarchical config loading (CLI flags → env vars → pyproject.toml)
- **Sync Engine** (`sync.py`): Core logic for building and executing sync plans (pull/push)
- **Selector** (`selector.py`): Document discovery and filtering based on frontmatter rules
- **Frontmatter** (`frontmatter.py`): YAML frontmatter parsing and validation
- **Models** (`models.py`): Data structures (Document, PlanEntry, SyncPlan)
- **Filesystem** (`fs.py`): File operations, atomic writes, git repo detection
- **Prompting** (`prompt.py`): Interactive conflict resolution and user confirmations

The sync flow follows this pattern:
1. Collect eligible documents from source (workspace or repo)
2. Build a sync plan comparing source vs target
3. Display plan and prompt for confirmation (unless --force)
4. Execute plan with atomic file operations

## Configuration System

SpecSync uses a three-tier configuration hierarchy:
1. Command-line flags (highest priority)
2. Environment variables (`SPECSYNC_*` prefix)
3. `pyproject.toml` under `[tool.specsync]` (lowest priority)

Required configuration:
- `workspace_root`: Path to the external workspace (must be set via env var or flag)

## Testing Approach

- Unit tests live in `tests/` directory with `test_*.py` naming
- Use `pytest` fixtures for temporary directories and file creation
- Tests cover individual modules (selector, frontmatter, config) and integration scenarios
- Run a specific test: `uv run pytest tests/test_selector.py::test_function_name -xvs`

## Important Implementation Details

- All file writes use atomic operations (write to temp file, then move)
- Conflict resolution uses interactive prompts with diff display
- Frontmatter parsing handles both `---` delimited YAML and empty files
- The `specs/` directory is automatically added to `.gitignore` during init
- Hash-based comparison determines if files have changed
- Project name auto-detection uses git repo name or directory name as fallback
