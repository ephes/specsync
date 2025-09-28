# Configuration

SpecSync reads configuration from several sources so you can tailor the workflow to each repository and workstation.

## Configuration Hierarchy

From highest to lowest precedence:

1. Command-line arguments
2. Environment variables (e.g., `SPECSYNC_WORKSPACE_ROOT`)
3. `pyproject.toml` entries under `[tool.specsync]`

The first source that defines a setting wins. For example, a CLI flag overrides the environment, which overrides the project configuration file.

## Environment Variables

| Variable | Description |
| --- | --- |
| `SPECSYNC_WORKSPACE_ROOT` | Base directory of your external workspace or vault. |
| `SPECSYNC_REPO_SPECS_DIR` | Directory within the repository that stores synchronized specs. Defaults to `specs`. |
| `SPECSYNC_PROJECT_NAME` | Optional name used to filter specs by frontmatter `project`. |

Use these variables for per-machine overrides or integrate them into automation.

## Project Configuration (`pyproject.toml`)

Add a section similar to the following inside your repository:

```toml
[tool.specsync]
workspace_subdir = "specs"
repo_specs_dir = "specs"
project_name = "my-project"

[tool.specsync.filter]
require_expose = true
match_project = true
```

- `workspace_subdir`: Subdirectory inside the workspace root containing synced files.
- `repo_specs_dir`: Repository directory where SpecSync writes the synced files.
- `project_name`: Optional default project filter applied when pulling or pushing.
- `require_expose`: Enforces `expose: true` in frontmatter before syncing.
- `match_project`: Sync only specs whose `project` matches `project_name`.

## Setting Environment Variables

You have several options for configuring environment variables:

### Option 1: direnv (Automatic per-directory)

[direnv](https://direnv.net/) automatically loads environment variables when you enter a directory:

```bash
# Create .envrc in repository root
export SPECSYNC_WORKSPACE_ROOT="/Users/you/Documents/SpecsVault"
export SPECSYNC_REPO_SPECS_DIR="specs"
export SPECSYNC_PROJECT_NAME="specsync"
```

Run `direnv allow` to activate. Remember to add `.envrc` to `.gitignore`.

### Option 2: Shell Export (Session-only)

```bash
export SPECSYNC_WORKSPACE_ROOT="/Users/you/Documents/SpecsVault"
```

### Option 3: Shell Configuration (Permanent)

Add exports to your shell configuration file (`~/.bashrc`, `~/.zshrc`, etc.) for persistent settings across all projects.

## Frontmatter Format

SpecSync relies on YAML frontmatter to decide which notes to synchronize. Example:

```yaml
---
expose: true
project: specsync
status: draft
title: Documentation Plan
---
```

- `expose` controls visibility; only files with `true` are eligible for syncing when `require_expose` is enabled.
- `project` lets you scope synchronization to a specific initiative.
- Additional metadata is preserved but not interpreted directly by SpecSync.
