# SpecSync

Selective Markdown sync between your repo and any workspace folder.

SpecSync is a lightweight Python CLI that bridges your repo's ignored `specs/` folder and an external workspace (e.g. Obsidian vault, Hugo content dir). 

It lets you expose only the Markdown files you choose (via frontmatter or patterns), keep them in sync in both directions, and optionally watch for changes — so your specs stay organized without cluttering your codebase.

## Features

- **Selective Syncing**: Choose which files to sync using glob patterns and frontmatter filtering
- **Bidirectional Sync**: Sync from specs to workspace and back
- **Frontmatter Filtering**: Filter files based on YAML frontmatter fields
- **Directory Structure**: Preserve or flatten directory structure in workspace
- **Watch Mode**: Automatically sync changes as they happen
- **Dry Run**: Preview what would be synced without making changes

## Installation

```bash
pip install specsync
```

## Quick Start

1. **Initialize a configuration file:**
   ```bash
   specsync init
   ```

2. **Sync your specs to a workspace:**
   ```bash
   specsync sync /path/to/workspace --specs-dir specs
   ```

3. **Sync changes back from workspace:**
   ```bash
   specsync sync-back /path/to/workspace --specs-dir specs
   ```

4. **Watch for changes and auto-sync:**
   ```bash
   specsync watch /path/to/workspace --specs-dir specs
   ```

## Configuration

Create a `specsync.yaml` file to customize behavior:

```yaml
# File patterns to include (supports glob patterns)
include_patterns:
  - "*.md"
  - "docs/**/*.md"

# File patterns to exclude
exclude_patterns:
  - "**/draft-*.md"
  - "private/**"

# Filter files based on frontmatter
frontmatter_filter:
  published: true
  status: "ready"

# Preserve directory structure in workspace
preserve_structure: true

# Debounce time for watch mode (seconds)
watch_debounce_seconds: 1.0
```

## Usage Examples

### Basic Sync
```bash
# Sync all markdown files to workspace
specsync sync /path/to/obsidian-vault

# Use custom specs directory
specsync sync /path/to/workspace --specs-dir documentation

# Preview what would be synced
specsync sync /path/to/workspace --dry-run
```

### With Patterns
```bash
# Only sync specific patterns
specsync sync /path/to/workspace --pattern "*.md" --pattern "docs/**/*.md"

# Exclude drafts
specsync sync /path/to/workspace --exclude-pattern "**/draft-*.md"
```

### Frontmatter Filtering

Files with frontmatter like this will be included when `published: true` is in your config:

```markdown
---
title: My Specification
published: true
tags: [spec, important]
---

# My Specification

Content here...
```

### Watch Mode
```bash
# Watch both directories and sync automatically
specsync watch /path/to/workspace --specs-dir specs
```

## CLI Commands

- `specsync init` - Initialize configuration file
- `specsync sync WORKSPACE` - Sync specs to workspace
- `specsync sync-back WORKSPACE` - Sync changes back from workspace
- `specsync watch WORKSPACE` - Watch for changes and auto-sync

## Use Cases

- **Documentation Workflow**: Keep specs in your repo but edit them in Obsidian
- **Hugo Sites**: Sync selected content to Hugo content directory
- **Team Collaboration**: Share only published specs while keeping drafts private
- **Multi-Platform**: Work with specs across different tools and editors

## License

MIT
