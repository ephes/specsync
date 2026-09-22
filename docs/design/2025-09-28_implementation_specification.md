# Specsync Technical Specification

## 1. Purpose and Scope
- Define the architecture, behaviors, and interfaces for the Specsync CLI MVP.
- Cover pull/push synchronization between a git-ignored repository specs directory and an external workspace (vault).
- Assume Python 3.11+, uv-managed project, dependency on PyYAML for frontmatter parsing, otherwise stdlib only.

## 2. High-Level Architecture
- **CLI Entrypoint (`specsync.cli`)**
  - Parses arguments via `argparse` and dispatches to subcommand handlers.
  - Shared options resolved once and passed downstream as a `Config` instance.
- **Configuration Layer (`specsync.config`)**
  - Loads and merges settings from CLI flags, environment variables, and `pyproject.toml`.
  - Provides normalised paths, filter flags, and defaults for interactive behavior.
- **Frontmatter Utilities (`specsync.frontmatter`)**
  - Parse, validate, and render YAML frontmatter blocks.
  - Surface precise errors for malformed documents.
- **Selection Engine (`specsync.selector`)**
  - Enumerates candidate spec files.
  - Applies metadata-based filters (expose/project).
  - Produces `SpecDocument` objects for further processing.
- **Sync Engine (`specsync.sync`)**
  - Builds `SyncPlan` objects for pull and push operations.
  - Delegates conflict resolution to prompt/force logic.
  - Executes file copy/update operations with atomic writes.
- **Prompt & UX Helpers (`specsync.prompt`)**
  - Manage interactive prompts, diff previews, and batch actions.
  - Graceful fallback when stdin is non-interactive.
- **Filesystem Utilities (`specsync.fs`)**
  - Cross-platform path utilities, hashing, directory creation, gitignore manipulation.
- **Logging Helpers (`specsync.logging`)**
  - Structured info/warn/error output respecting verbosity flags.

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ CLI (argparse)├─────► Config Layer ├─────► Sync Engine   │
└──────┬───────┘      └────┬────────┘      └────┬────────┬┘
       │                   │                   │        │
       │                   │                   │        │
       ▼                   ▼                   ▼        ▼
 Logging Helpers     Frontmatter Utils     Selector   Prompt
```

## 3. CLI Interface

### 3.1 Global Options
- `--workspace-root PATH` (override `SPECSYNC_WORKSPACE_ROOT`).
- `--repo-specs-dir PATH` (override config repo specs directory).
- `--project-name NAME` (override detected project name).
- `--dry-run` (skip copying files; show plan only).
- `--force` (skip interactive prompts, force overwrites).
- `--quiet` (suppress info-level output; prompts still shown).
- `--version` (print version and exit).

### 3.2 Subcommands

#### `specsync pull`
- Purpose: Pull selected specs from vault/workspace (source of truth) to repo (working copy).
- Specific flags: inherits global options only.
- Behavior: build sync plan, prompt on conflicts unless `--force`, copy files.
- Direction: vault → repo

#### `specsync push`
- Purpose: Push modified specs from repo (working copy) back to vault/workspace (source of truth).
- Specific flags: inherits global options only.
- Behavior: inject frontmatter when missing, prompt on conflicts, copy files.
- Direction: repo → vault

#### `specsync info`
- Output resolved configuration table: repo root, workspace root, project name, filter flags, yaml parser info.
- Optionally print environment and CLI overrides when `--verbose` (future hook).

#### `specsync init`
- Creates repo specs directory if missing.
- Appends specs directory to `.gitignore` (idempotent).
- Writes starter `[tool.specsync]` block to `pyproject.toml` when absent.
- Optional `--include-sample` to drop a `sample-spec.md` template (future optional flag).

### 3.3 Exit Codes
- `0`: success (including dry-run).
- `1`: user-facing error (invalid config, parse errors, missing directories).
- `2`: execution aborted due to conflicts unanswered (non-interactive without `--force`).
- `3`: unexpected internal error.

## 4. Configuration Resolution

### 4.1 Sources (Precedence Order)
1. CLI flags (highest priority)
2. Environment variables: `SPECSYNC_WORKSPACE_ROOT`, `SPECSYNC_PROJECT_NAME`
3. `pyproject.toml` `[tool.specsync]` section
4. Built-in defaults (lowest priority)

**Note:** Use direnv, shell profiles, or other environment management tools to set `SPECSYNC_WORKSPACE_ROOT` persistently.

### 4.2 Dataclass Shape
```python
@dataclass
class Config:
    repo_root: Path
    workspace_root: Path
    workspace_subdir: Path
    workspace_specs_dir: Path    # workspace_root / workspace_subdir (NO project_name)
    repo_specs_dir: Path         # repo_root / repo_specs_dir (relative from config)
    project_name: str            # Used for filtering only, not paths
    require_expose: bool
    match_project: bool
    dry_run: bool
    force: bool
    quiet: bool
```

### 4.3 Validation Rules
- Workspace root must exist for `pull` operations (error if missing).
- Workspace specs directory (workspace_root/workspace_subdir) will be created automatically during `push` if missing.
- Repo specs directory will be created automatically during operations if missing.
- Project name detection order:
  1. CLI flag `--project-name`
  2. Environment variable `SPECSYNC_PROJECT_NAME`
  3. `pyproject.toml` `[tool.specsync] project_name`
  4. `pyproject.toml` `[project] name` (if exists)
  5. Git remote origin URL (parse last segment, strip `.git`)
  6. Repository root folder name

### 4.4 Git Remote Detection
- Run `git config --get remote.origin.url`
- Parse URL formats: `git@github.com:user/repo.git` → `repo`
- Handle HTTPS: `https://github.com/user/repo` → `repo`
- If multiple remotes exist, prefer `origin`; log warning if ambiguous

### 4.5 `specsync init` Output Example
```toml
[tool.specsync]
workspace_subdir = "specs"  # Within SPECSYNC_WORKSPACE_ROOT
repo_specs_dir = "specs"    # Within repo root
# project_name = "my-project"  # Optional, auto-detected from git/folder

[tool.specsync.filter]
require_expose = true
match_project = true  # If true, only sync files with matching project field
```

**Path Resolution Example:**
- `SPECSYNC_WORKSPACE_ROOT` = `~/Documents/Obsidian`
- `workspace_subdir` = `specs`
- Final workspace path = `~/Documents/Obsidian/specs/`
- All `.md` files in this directory can be synced (if they have `expose: true`)
- The `project` field in frontmatter is used for filtering, NOT for path construction

## 5. Frontmatter Handling

### 5.1 Parsing Algorithm
1. Read file text as UTF-8, normalize line endings to `\n`.
2. Check if file begins with exactly `---\n` (after normalization).
3. Find the FIRST occurrence of `\n---\n` or `\n---\r\n` or `\n---` at EOF.
4. Extract substring between delimiters; pass to `yaml.safe_load`.
5. Handle edge cases:
   - Empty frontmatter (`---\n---`) → empty dict `{}`
   - Multiple `---` blocks → only first is frontmatter
   - No closing `---` → treat entire file as body, no frontmatter
6. If YAML parsing fails, raise `FrontmatterError(path, line_number, message)`.
7. Remainder of document (after closing delimiter and optional newline) is body.

### 5.2 Rendering & Injection
- `render_frontmatter(data: dict) -> str` produces `---\n<yaml>---\n` without trailing blank lines.
- For repo files lacking frontmatter during push:
  - Build dict: `{"expose": True, "project": config.project_name}` (omit `project` when `match_project` disabled).
  - Prepend rendered block plus single newline to document body.
  - Mark document status as `metadata_injected` for reporting.

### 5.3 Validation Checks
- Ensure `expose` is boolean; if not, treat as invalid and skip with warning.
- When `match_project` enabled, ensure `project` field matches `config.project_name` (case-sensitive by default).
- Provide actionable warning messages aggregated and printed once per run.

## 6. Document Enumeration & Selection

### 6.1 Workspace Enumeration (Pull)
- Walk `config.workspace_specs_dir` recursively using `Path.rglob("*.md")`.
- Skip directories starting with `.` by default.
- Apply security checks:
  - Resolve all paths to absolute and verify they stay within `workspace_specs_dir`
  - Skip and warn on symlinks (security: prevent directory traversal)
- For each candidate, parse frontmatter, apply filters, create `SpecDocument` with resolved repo path (`config.repo_specs_dir / relative_path`).

### 6.2 Repo Enumeration (Push)
- Walk `config.repo_specs_dir` recursively for `*.md`.
- Apply same security checks as workspace enumeration.
- Parse frontmatter if present; if absent, mark status `missing_metadata` to trigger injection.
- Map to workspace path (`config.workspace_specs_dir / relative_path`).

### 6.3 SpecDocument Structure
```python
@dataclass
class SpecDocument:
    relative_path: Path
    workspace_path: Path
    repo_path: Path
    frontmatter: dict | None
    body: str
    metadata_status: Literal[
        "valid",
        "invalid",
        "missing",
        "metadata_injected",
    ]
```

## 7. Sync Planning

### 7.1 Hashing & Modification Detection
- `fs.hash_file(path)` returns SHA-256 hex digest of canonical content.
- When file missing on one side → state `new_source` or `new_target`.
- When both exist and hashes differ → state `conflict` (requires prompt unless `--force`).
- When hashes equal → skip copy.

### 7.2 SyncPlan Model
```python
@dataclass
class PlanEntry:
    document: SpecDocument
    source_path: Path
    target_path: Path
    state: Literal["create", "update", "conflict", "skip"]
    reason: str | None

@dataclass
class SyncPlan:
    direction: Literal["pull", "push"]
    entries: list[PlanEntry]
    warnings: list[str]
```

### 7.3 Execution Flow
1. Build plan (`SyncPlanner.build_pull_plan(config)` / `build_push_plan`).
2. Print summary (counts per state) unless `--quiet`.
3. If `dry_run`, display table (relative path, action, notes) and exit 0.
4. Iterate entries:
   - `skip`: log and continue.
   - `create` or `update`: if `--force`, proceed; otherwise call `PromptEngine.confirm(entry)` when file already exists.
   - On user selection:
     - `overwrite`: perform copy.
     - `skip`: skip entry.
     - `diff`: show diff via `difflib.unified_diff`, then re-prompt.
     - `all`: mark global action for remaining conflicts.
5. Copy operations use `fs.write_file_atomic(target_path, content)` to avoid partial writes.
6. Track results (created/updated/skipped/conflicts). At end, print summary.

## 8. File Operations & Security

### 8.1 Path Security
- All paths must be validated before operations:
  - Resolve to absolute paths using `Path.resolve()`
  - Verify path stays within allowed boundaries (no `../` escapes)
  - Reject symlinks that point outside workspace or repo
- Use `fs.validate_path_security(path, allowed_root)` before all operations.

### 8.2 File Operations
- `fs.ensure_dir(path)` creates parent directories with `exist_ok=True`.
- `fs.write_file_atomic` writes to temp file (`path.with_suffix('.tmp')`), flushes, renames.
- Handle concurrent access: use file locking or retry logic for busy files.
- Preserve file permissions when copying (use `shutil.copy2`).

### 8.3 Gitignore Handling
- `fs.append_gitignore(repo_root, pattern)` appends pattern if not already present.
- Check for pattern variations (`/specs/`, `specs/`, `/specs`) to avoid duplicates.
- Add comment line before pattern: `# Added by specsync`.

## 9. Interactive Prompt Engine
- If `sys.stdin.isatty()` false and entry requires confirmation, exit with code `2` unless `--force` true.
- Prompt text example: `File differs: repo/specs/foo.md`
  - `[o]verwrite, [s]kip, [d]iff, [A]ll-overwrite, [S]kip-all, [q]uit?`
- Accept case-sensitive shortcuts:
  - `o`: overwrite this file
  - `s`: skip this file
  - `d`: show diff then re-prompt
  - `A`: overwrite all remaining conflicts
  - `S`: skip all remaining conflicts
  - `q`: quit immediately (exit code 2)
- Remember "all" decisions for session via `PromptState.overwrite_all` and `skip_all` booleans.
- Diff view limited to 200 lines; show `[... diff truncated, X more lines ...]` if needed.
- Show file modification times when prompting to help user decide.

## 10. Logging & Output
- Use simple tagged format: `[INFO] message`, `[WARN] message`, `[ERROR] message`.
- `--quiet` suppresses `[INFO]`; `[WARN]` and `[ERROR]` always shown.
- Summary example after sync:
  - `Created: 3, Updated: 2, Skipped: 1 (user), Skipped: 4 (filters)`
- For dry-run, show ASCII table with columns `Action | Path | Reason`.

## 11. Error Handling Strategy

### 11.1 Error Categories
- **Configuration Errors**: Missing workspace, invalid project name
  - Example: `[ERROR] Workspace not found: ~/Documents/Obsidian/specs`
  - Remedy: `Set SPECSYNC_WORKSPACE_ROOT or create the directory`

- **Frontmatter Errors**: Invalid YAML, missing required fields
  - Example: `[ERROR] Invalid frontmatter in specs/api.md: expected 'expose' to be boolean`
  - Remedy: `Fix the frontmatter: expose: true (not "true")`

- **Permission Errors**: Cannot read/write files
  - Example: `[ERROR] Permission denied: cannot write to /protected/path`
  - Remedy: `Check file permissions or run with appropriate privileges`

### 11.2 Error Collection
- Collect all validation errors before aborting (don't fail on first error).
- Display errors grouped by type with actionable remediation.
- Exit with appropriate code based on error type.

### 11.3 Unexpected Errors
- Wrap in user-friendly message: `[ERROR] Unexpected failure. Run with SPECSYNC_DEBUG=1 for details`
- Log full traceback only when debug mode enabled.
- Suggest filing issue at GitHub repo with debug output.

## 12. Testing Strategy

### 12.1 Unit Tests
- **Frontmatter Module**
  - Empty frontmatter blocks (`---\n---`)
  - Windows line endings (`\r\n`)
  - Multiple `---` delimiters in content
  - Invalid YAML syntax
  - Unicode content handling

- **Config Module**
  - Precedence: CLI > ENV > pyproject.toml > defaults
  - Project name detection fallback chain
  - Path resolution and normalization
  - Git remote URL parsing (SSH, HTTPS, various formats)

- **Security Tests**
  - Path traversal attempts (`../../etc`)
  - Symlink escape attempts
  - Invalid Unicode in filenames

### 12.2 Integration Tests
- **Pull Operations**
  - New files from vault
  - Updates with conflicts (mock stdin for prompts)
  - Filter behavior (expose, project matching)
  - Missing workspace handling

- **Push Operations**
  - Metadata injection for new files
  - Conflict resolution with all prompt options
  - Workspace directory creation

- **Cross-platform**
  - Path separators on macOS/Linux
  - Case sensitivity handling
  - Unicode filenames

### 12.3 Test Infrastructure
- Use `pytest` with fixtures for workspace/repo setup
- `tmp_path` fixture for isolated file operations
- `monkeypatch` for stdin/env manipulation
- Snapshot testing for CLI output formatting
- Coverage target: 90%+

## 13. Packaging & Distribution
- `pyproject.toml` includes project metadata:
  - Required dependencies: `pyyaml>=6.0`
  - No other external dependencies (stdlib only)
- `[project.scripts] specsync = "specsync.cli:main"`.
- Package name: `specsync-cli` on PyPI.
- Installation methods:
  - `uv tool install specsync-cli`
  - `pipx install specsync-cli`
  - `uvx specsync-cli` (for one-off usage)

## 14. Observability & Debugging
- No network calls or telemetry.
- Debug mode via `SPECSYNC_DEBUG=1` environment variable:
  - Show configuration resolution steps
  - Log path calculations
  - Display git detection attempts
- Use Python's logging module with appropriate levels.

## 15. Example Workflows

### 15.1 Initial Setup
```bash
# In your repo
specsync init
# Creates specs/ directory, updates .gitignore, adds config to pyproject.toml

# Set your workspace location (use direnv, shell profile, etc.)
export SPECSYNC_WORKSPACE_ROOT="~/Documents/Obsidian/Vault"

# For direnv users, add to .envrc:
echo 'export SPECSYNC_WORKSPACE_ROOT="~/Documents/Obsidian/Vault"' >> .envrc
direnv allow
```

### 15.2 Typical Development Flow
```bash
# 1. Pull specs you want to work on (marked with expose: true in vault)
specsync pull --dry-run  # See what would be pulled
specsync pull            # Pull specs to repo

# 2. Work with AI tools (Claude Code, Codex, etc.)
# ... specs get modified in repo/specs/ ...

# 3. Push changes back to vault
specsync push --dry-run  # See what would be pushed
specsync push            # Push with interactive prompts for conflicts
```

### 15.3 Frontmatter Example
```yaml
---
expose: true
project: myapp
status: draft
tags: [api, authentication]
---

# Authentication API Specification
...
```

## 16. Future Enhancements (Out of Scope for MVP)
- Maintain `.specsync/state.json` to cache hashes for faster runs.
- Support additional metadata-based selection (tags, status).
- Add watch mode for continuous sync.
- Provide plugin interface for custom filters or copy hooks.
- Add conflict resolution strategies (three-way merge, git-based diff).
- Bidirectional sync with automatic conflict resolution.

