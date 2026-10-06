# SpecSync

> Selective Markdown sync between your repo and any workspace folder.

SpecSync is a lightweight Python CLI that bridges your repo's ignored `specs/` folder and an external workspace (e.g. an Obsidian vault, a Hugo content directory, or any notes folder).
It lets you **pull only the Markdown files you choose** (via frontmatter), keep them in sync in both directions, and work seamlessly with AI coding tools — so your specs stay organized without cluttering your codebase.

---

## Features
- **Frontmatter filtering** – pull only notes with `expose: true` (and matching `project:` if set).
- **Two-way sync** – pull specs from workspace → repo or push changes back from repo → workspace.
- **Safe by default** – interactive prompts for conflicts, `--force` to skip prompts.
- **Flexible** – works with any folder structure, not tied to Obsidian.
- **Git-like workflow** – familiar `pull` and `push` commands.

---

## Documentation

📚 **[Read the full documentation](https://specsync.readthedocs.io/en/latest/)**

- [Installation Guide](https://specsync.readthedocs.io/en/latest/installation.html)
- [Usage Guide](https://specsync.readthedocs.io/en/latest/usage.html)
- [Configuration Reference](https://specsync.readthedocs.io/en/latest/configuration.html)
- [Architecture Overview](https://specsync.readthedocs.io/en/latest/architecture.html)

---

## Quick Start

Install with [pipx](https://pypa.github.io/pipx/) or [uv](https://github.com/astral-sh/uv):

```bash
pipx install specsync
# or
uv tool install specsync
```

Set your workspace location using environment variables or [direnv](https://direnv.net/):

```bash
# Option 1: Direct export (temporary, current session only)
export SPECSYNC_WORKSPACE_ROOT="~/Documents/Obsidian"

# Option 2: Using direnv (recommended for project-specific config)
# Copy the example file and customize:
cp .envrc.example .envrc
# Edit .envrc with your workspace path, then:
direnv allow
```

Initialize in a repo (creates `specs/` folder and updates `pyproject.toml`):

```bash
specsync init
```

Pull specs from your workspace into the repo's `specs/` folder:

```bash
specsync pull
```

Push changes from the repo back to your workspace:

```bash
specsync push
```

Show current configuration:

```bash
specsync info
```

---

## Configuration

SpecSync looks for configuration in this order:
1. Command-line flags
2. Environment variables (e.g., `SPECSYNC_WORKSPACE_ROOT`)
3. `pyproject.toml` under `[tool.specsync]`

### Using direnv for Local Configuration

For project-specific environment variables, create a `.envrc` file in your repo root:

```bash
# .envrc
export SPECSYNC_WORKSPACE_ROOT="/Users/you/Library/Mobile Documents/iCloud~md~obsidian/Documents/YourVault"
export SPECSYNC_REPO_SPECS_DIR="specs"
export SPECSYNC_PROJECT_NAME="my-project"
```

Then activate it:
```bash
direnv allow
```

Add `.envrc` to your `.gitignore` to keep local paths private:
```bash
echo ".envrc" >> .gitignore
```

### Project Configuration

Example `pyproject.toml`:
```toml
[tool.specsync]
workspace_subdir = "specs"    # Subdirectory in workspace
repo_specs_dir = "specs"      # Directory in repo (git-ignored)
project_name = "my-project"   # Optional, auto-detected if not set

[tool.specsync.filter]
require_expose = true         # Only sync files with expose: true
match_project = true          # Only sync files matching project name
```

## Example Frontmatter

Mark specs for syncing with frontmatter:

```yaml
---
expose: true                  # Required for syncing
project: my-project          # Optional, must match if match_project is true
title: GPU Crash Fix
status: draft
---

# GPU Crash Investigation
...
```

Only notes with `expose: true` (and matching `project` when configured) are synced.

---

## Conflicts and Safety

- **Injected metadata is not a change.** `push` adds `expose: true` (and `project`, or removes it when
  `match_project = false`) to the workspace copy. Planning compares against exactly what push would
  write, so a repo spec and its pushed copy count as `unchanged` in both directions. A forced `pull`
  right after a `push` therefore leaves the repo file untouched.
- **Real edits still conflict.** Any other difference is a `CONFLICT`, prompted for interactively or
  overwritten with `--force`.
- **Backups.** Before overwriting an existing file, SpecSync copies it to `<file>.specsync-bak` next to
  it (replacing an older backup). Backups do not end in `.md`, so they are never synced.
- **Destinations are never followed through symlinks.** If the destination file, any directory between
  the specs root and the file, or the `.specsync-bak` path is a symlink (or not a regular file/directory),
  the entry is shown as `UNSAFE` and refused. If the backup cannot be written (for example because its name
  exceeds the filesystem's limit), the file is not overwritten either. The checks are repeated right before each write. A run that refuses any entry exits with status 1.

---

## License

MIT
