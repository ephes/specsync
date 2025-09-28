# Usage

This guide walks through the SpecSync command-line interface and typical workflows for keeping documentation synchronized.

## Basic Commands

| Command | Purpose |
| --- | --- |
| `specsync init` | Scaffold the repository configuration and create the `specs/` directory. |
| `specsync pull` | Copy exposed specs from the workspace into the repository. |
| `specsync push` | Publish repository changes back to the workspace. |
| `specsync info` | Display the active configuration and workspace paths. |

Run `specsync --help` to view global flags and `specsync <command> --help` for per-command options.

## Command-line Options

- `--workspace-root`: Override the workspace root directory discovered from configuration files.
- `--project`: Limit synchronization to a specific project name (overrides `tool.specsync.project_name`).
- `--force`: Skip interactive prompts when applying changes.
- `--dry-run`: Preview changes without writing to disk.

```{warning}
Use `--force` with care. Forcing a push can overwrite workspace changes if you are not careful about conflicts.
```

## Common Workflows

### Daily Sync Loop

1. Pull exposed notes to make sure the repository copy is up to date.
2. Edit the Markdown files inside `specs/` alongside your code changes.
3. Push the updated specs back to the workspace when you are satisfied.

### Working with Specs

**Typical workflow (repo-first):**
1. AI tools (Claude, Copilot, etc.) or developers create specs directly in the `specs/` folder
2. Edit and refine specs as needed in your editor
3. Run `specsync push` to sync refined specs to your workspace for long-term storage
4. Commit the specs alongside related code changes

**Alternative workflow (workspace-first):**
1. Author specs in your workspace with `expose: true` in frontmatter
2. Run `specsync pull` to bring them into the repository
3. Edit as needed and push changes back

### Working with Drafts

Keep drafts private by leaving `expose: false` (or omitting the field). Only exposed specs are synchronized.

## Setting Environment Variables

SpecSync needs to know where your workspace is located. You can set this in several ways:

**Option 1: Direct export (session-only)**
```bash
export SPECSYNC_WORKSPACE_ROOT="/path/to/workspace"
```

**Option 2: Using direnv (automatic per-directory)**
```bash
# Create .envrc in repo root
echo 'export SPECSYNC_WORKSPACE_ROOT="/path/to/workspace"' > .envrc
direnv allow
```

**Option 3: Shell configuration (permanent)**
```bash
# Add to ~/.bashrc, ~/.zshrc, etc.
export SPECSYNC_WORKSPACE_ROOT="/path/to/workspace"
```

See {doc}`configuration` for all available environment variables.
