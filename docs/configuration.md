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

- `workspace_subdir`: Relative subdirectory inside the workspace root containing synced files.
- `repo_specs_dir`: Relative subdirectory of the repository where SpecSync writes the synced files.
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

## Repository directory resolution

For both init and synchronization, `--repo-specs-dir` overrides
`SPECSYNC_REPO_SPECS_DIR`, then `[tool.specsync].repo_specs_dir`, then the
`specs` default. Init creates the selected directory and adds a repo-relative
gitignore entry. When the TOML directory setting is missing, init records the
selected directory as its default; existing settings remain unchanged. Init
refuses symlinked pyproject files.

## Directory validation

`repo_specs_dir` names a subdirectory of the Git repository root and
`workspace_subdir` a subdirectory of the workspace root. Every configured value
— the stored TOML setting, `SPECSYNC_REPO_SPECS_DIR`, and `--repo-specs-dir` —
passes the same check before any command reads or writes files:

- a non-empty string using `/` separators;
- relative: no leading `/`, drive prefix, or `~`;
- no `..` component, and not just `.`;
- the resolved directory stays inside its root, so a symlinked directory that
  leads outside the repository or workspace is refused.

Init applies the same checks; the workspace containment check runs when a
workspace root is configured through `--workspace-root` or
`SPECSYNC_WORKSPACE_ROOT`. Init also adds missing defaults to inline-table
configurations such as `specsync = {repo_specs_dir = "planning"}`.

All configured values are checked, not only the one that takes effect. An
invalid stored or environment value is reported even when `--repo-specs-dir`
overrides it; fix or remove the invalid value. Absolute directories are no
longer accepted for these settings.

Init parses TOML and adds only missing settings, retaining existing values and
comments. Comments or strings mentioning table names do not count as configuration.
The resulting TOML is validated before atomic replacement; repeated init is idempotent.
