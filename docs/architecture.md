# Architecture

This document outlines how SpecSync coordinates data between a repository and an external workspace.

## System Design

SpecSync is a command-line tool that orchestrates synchronization operations. It uses the local filesystem as the transport layer and respects Git workflows by keeping synced specs inside the repository.

The tool is built on a modular Python codebase located under `src/specsync`:

- **CLI layer** (`specsync.cli`): Parses user input and wiring for commands.
- **Configuration** (`specsync.config`): Aggregates settings from flags, environment variables, and `pyproject.toml`.
- **Synchronization core** (`specsync.sync`): Implements pulling and pushing logic, file diffing, and conflict handling.
- **Frontmatter utilities** (`specsync.frontmatter`): Parses YAML metadata and filters eligible files.

## Component Overview

```{mermaid}
graph TD
    CLI["CLI Commands<br/>specsync.cli"] --> Config["Configuration Loader<br/>specsync.config"]
    Config --> Sync["Sync Engine<br/>specsync.sync"]

    Sync --> FMP["Frontmatter Parser<br/>specsync.frontmatter"]
    Sync --> FS["File System Operations<br/>specsync.fs"]
    Sync --> Selector["File Selector<br/>specsync.selector"]

    FMP --> Models["Data Models<br/>specsync.models"]
    Selector --> Models

    Config -.-> Env["Environment Variables<br/>SPECSYNC_*"]
    Config -.-> TOML["pyproject.toml<br/>tool.specsync"]

    FS --> Workspace[("Workspace<br/>e.g., Obsidian")]
    FS --> Repo[("Repository<br/>specs/")]

    Sync --> Prompt["Interactive Prompts<br/>specsync.prompt"]

    style CLI fill:#e1f5fe
    style Sync fill:#fff3e0
    style FMP fill:#f3e5f5
    style Workspace fill:#e8f5e9
    style Repo fill:#e8f5e9
```

### Key Components

- **CLI Layer** (`specsync.cli`): Entry point, command parsing, and orchestration
- **Configuration** (`specsync.config`): Merges settings from CLI flags, environment variables, and `pyproject.toml`
- **Sync Engine** (`specsync.sync`): Core logic for bidirectional synchronization
- **Frontmatter Parser** (`specsync.frontmatter`): YAML metadata extraction and validation
- **File Selector** (`specsync.selector`): Applies filtering rules based on frontmatter
- **File System** (`specsync.fs`): Low-level file operations and Git integration
- **Interactive Prompts** (`specsync.prompt`): Conflict resolution and user interaction
- **Data Models** (`specsync.models`): Type-safe data structures for specs and configuration

## Data Flow

1. The CLI determines intent (`pull`, `push`, etc.) and requests configuration.
2. Configuration is merged from command-line args, environment variables, and project defaults.
3. The sync engine scans the workspace and repository directories.
4. Frontmatter is parsed to select files with `expose: true` and matching `project` filters.
5. Selected files are copied in the requested direction with conflict handling.

## File Sync Algorithm

- **Scanning**: Gather candidate files from both the workspace and repository directories.
- **Filtering**: Apply frontmatter rules (exposure and project matching).
- **Diffing**: Compare file contents. Push compares the destination with the exact payload it would write
  (repo file plus injected `expose`/`project` frontmatter); pull treats the repo file as unchanged when the
  workspace file equals that push payload. A push followed by a push or pull is therefore all `skip`.
- **Destination safety**: Destination paths are built without resolving symlinks. An entry whose destination
  file, intermediate directory or `.specsync-bak` path is a symlink (or not a regular file/directory), or
  that escapes the destination root, is planned as `unsafe` and refused; the check is repeated right before writing.
- **Conflict Resolution**: When the files differ, prompt the user unless `--force` is supplied.
- **Apply Changes**: Copy the existing destination to `<file>.specsync-bak`, then write through an exclusive
  temp file and an atomic `os.replace`, preserving directory structure.

## Frontmatter Filtering Logic

SpecSync reads YAML frontmatter located at the top of each Markdown file. The following rules apply:

- Files missing `expose: true` are ignored when `require_expose` is enabled.
- When `match_project` is enabled, files must include a `project` key matching the configured project name.
- Additional metadata is preserved and can be leveraged by other tooling but does not impact synchronization decisions.

Future iterations may extend the filter to support tag-based selection and more granular include/exclude patterns.
