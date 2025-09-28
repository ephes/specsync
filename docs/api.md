# API Reference

```{note}
Comprehensive API documentation will be added in a future release. The public API is still stabilizing.
```

## Module Overview

The SpecSync package consists of the following primary modules:

### Core Modules

- **`specsync.cli`** - Command-line interface and command handlers
- **`specsync.config`** - Configuration management and validation
- **`specsync.sync`** - Core synchronization logic for push/pull operations
- **`specsync.models`** - Data models and type definitions

### Supporting Modules

- **`specsync.frontmatter`** - YAML frontmatter parsing and manipulation
- **`specsync.selector`** - File selection and filtering logic
- **`specsync.fs`** - File system operations and Git integration
- **`specsync.prompt`** - Interactive user prompts for conflict resolution
- **`specsync.logging`** - Logging utilities
- **`specsync.exceptions`** - Custom exception types

## Command-Line Interface

The primary entry point is through the command-line:

```python
from specsync.cli import main

# Run with custom arguments
main(["push", "--dry-run"])
```

## Configuration API

```python
from specsync.config import load_config

# Load configuration with defaults
config = load_config(args=None, command="push")
```

## Future Development

The following enhancements are planned:

- Stable public Python API for programmatic use
- Plugin system for custom filters and transformations
- Webhook support for automated synchronization
- REST API for integration with other tools

For the latest updates, see the [project repository](https://github.com/username/specsync).
