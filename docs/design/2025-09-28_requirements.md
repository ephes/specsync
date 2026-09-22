# Specsync Requirements - MVP

## Overview
A command-line tool to synchronize markdown specification files between a git repository's git-ignored specs folder and an external workspace (e.g., Obsidian vault, documentation folder).

## Core Problem Statement
- Need to maintain specification documents alongside code repositories
- Want to edit specs in preferred tools (Obsidian, MacDown, VS Code, etc.) outside the repo
- Specs folder should stay git-ignored to avoid cluttering the repository
- Avoid confusing AI tools and developers with old/irrelevant specifications
- Vault/Spec Workspace is the system of record - all specs live there permanently
- The tool should be easy to integrate in justfiles using uvx / uv tool / pipx

## Typical Workflow
1. Developer uses `specsync pull` to fetch relevant specs from vault to repo
2. AI tools (Claude Code, Codex, etc.) work with and modify specs in the repo
3. Developer uses `specsync push` to save changes back to the vault
4. Vault acts like a "remote" repository for specifications

## Key Design Principles
1. **Tool-agnostic**: No hard dependencies on specific editors or tools
2. **Simple first**: Start with basic sync operations, add complexity later
3. **Vault as source of truth**: The external workspace (vault) is the primary storage
4. **Explicit selection**: Use frontmatter to explicitly mark active specs
5. **Minimal configuration**: Keep configuration surfaces small and predictable

## User Stories

### Primary Use Case
1. **As a developer**, I want to selectively pull only the specs I'm currently working on from my vault (system of record) to my project's git-ignored specs folder, so that:
   - Old/archived specs remain in my vault for reference
   - Only relevant specs are in the repo to work with AI tools (Claude Code, Codex, etc.)
   - I can explicitly control what's active via frontmatter metadata

2. **As a developer**, I want to push changes made by AI tools in the repo back to the vault (system of record), preserving all modifications made during development.

## Functional Requirements

### 1. File Selection
- **YAML frontmatter-based filtering** (primary method)
  - Files must have `expose: true` in YAML frontmatter (delimited by `---`) to be synced
  - Optional `project` field to match repository name
- **Default behavior**: Only sync files explicitly marked for exposure
- Provide clear validation errors when frontmatter is missing, malformed, or not YAML
- When pushing a repo-created file without frontmatter, automatically insert a minimal YAML block with `expose: true` (and inferred metadata) before syncing

### 2. Sync Operations

#### Core Commands (MVP)
- `specsync pull [--dry-run] [--force]`
  - Pulls selected files from vault (system of record) into the repo specs folder
  - Only pulls files with `expose: true` in frontmatter
  - For files that already exist and differ in the repo, prompt interactively with options to overwrite, skip, or show a diff; `--force` skips prompting and always overwrites the repo version
  - `--dry-run` lists files that would be pulled without copying them

- `specsync push [--dry-run] [--force]`
  - Pushes modified files from repo specs folder back to the vault
  - Applies automatic frontmatter insertion before syncing when required metadata is missing
  - For files that differ in the vault, prompt interactively with options to overwrite, skip, or show a diff; `--force` skips prompting and always overwrites the vault version
  - `--dry-run` lists files that would be pushed without copying them

#### Support Commands
- `specsync info` - Show configuration and resolved paths
- `specsync init` - Initialize configuration in current repo, ensure the specs directory exists, and append it to `.gitignore` if missing

### 3. Configuration

#### Configuration Sources & Precedence
1. Command-line flags (highest priority overrides)
2. Environment variables (e.g. `SPECSYNC_WORKSPACE_ROOT`)
3. Repository configuration in `pyproject.toml` under `[tool.specsync]`

#### Minimal Configuration Expectations
```toml
[tool.specsync]
workspace_subdir = "specs"               # Optional subdirectory within workspace
repo_specs_dir = "specs"                 # Folder in repo (git-ignored)
project_name = "my-project"              # Optional, auto-detected if not set

[tool.specsync.filter]
require_expose = true                    # Require expose: true
match_project = true                     # Match project field to repo name
```

### 4. Path Resolution
- Auto-detect git repository root
- Derive project name from (in order): CLI flag, environment variable, pyproject.toml `[tool.specsync]` section, git remote, folder name
- Support both relative and absolute paths for workspace and repo directories

## Non-Functional Requirements

### Usability
- Clear, actionable error messages
- Sensible defaults that work out-of-the-box
- Helpful `--help` documentation

### Compatibility
- Python 3.11+ support
- Cross-platform (Linux, macOS)
- Work with any markdown files
- No external service dependencies

## Technical Constraints

### Development Setup
- Package manager: uv
- Project structure: src layout (`src/specsync/`)
- Testing: pytest
- Linting: ruff via prek pre-commit hooks
- Packaging: PyPI distribution as `specsync-cli`

### Dependencies (Minimal)
- Core: Pure Python standard library
- YAML frontmatter parsing: a lightweight YAML parser library (e.g. PyYAML)
- CLI: `argparse` (standard library)

## Success Criteria
1. Can pull selected specs from vault to repo for AI tools to work with while guarding against data loss
2. Can push modified specs from repo back to vault with automatic metadata management
3. Simple configuration via `pyproject.toml` and optional environment variables
4. Clear selection via YAML frontmatter metadata
5. Vault remains the protected system of record with interactive overwrite safeguards

---

## Next Steps
1. Create detailed technical specification with interactive overwrite flow
2. Design CLI interface for `pull`, `push`, `info`, and `init` commands
3. Set up project structure with uv
4. Implement core commands with proper vault-as-remote mental model
5. Add configuration handling with simplified precedence
6. Write tests
