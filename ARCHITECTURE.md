# SpecSync Architecture

This high-level architecture overview is maintained alongside the codebase for quick reference. For the full documentation set, including diagrams and implementation detail, see [`docs/architecture.md`](./docs/architecture.md).

## Core Components

- **CLI Commands** — Parse user input and dispatch synchronization actions.
- **Configuration Loader** — Merges flags, environment variables, and `pyproject.toml` settings.
- **Sync Engine** — Compares files between the workspace and repository, applies filters, and resolves conflicts.
- **Frontmatter Parser** — Reads YAML metadata to determine whether a spec is eligible for syncing.

## Data Flow Snapshot

```
Workspace ──► Frontmatter Filter ──► Sync Engine ──► Repository
        ◄──────────────────────────────────────────────────────
```

Additional details, including workflow examples and design rationale, live in the dedicated documentation site.
