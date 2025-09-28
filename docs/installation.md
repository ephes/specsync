# Installation

SpecSync is distributed on PyPI and supports modern Python packaging workflows. Choose the approach that fits your environment.

## Prerequisites

- Python 3.11 or newer
- Git (recommended for managing specs alongside your repository)
- A method to set environment variables (e.g., direnv, shell exports, or .envrc file)

## Install with pipx

`pipx` isolates the CLI in its own environment so it stays available system-wide.

```bash
pipx install specsync
```

Upgrade when a new release becomes available:

```bash
pipx upgrade specsync
```

## Install with uv

[uv](https://github.com/astral-sh/uv) provides fast installs and tooling.

```bash
uv tool install specsync
```

To upgrade an existing install:

```bash
uv tool upgrade specsync
```

## Install from Source

Clone the repository and install from the local checkout.

```bash
git clone https://github.com/username/specsync.git
cd specsync
uv sync  # Installs package in development mode with all dependencies
```

## Development Setup

For contributing to SpecSync:

1. Clone the repository
2. Install dependencies with `uv sync` (automatically includes dev dependencies)
3. Use `just check` before submitting changes to run formatting and tests
4. Run `just docs-serve` to preview documentation locally

```{tip}
See {doc}`configuration` for details on setting environment variables required to point SpecSync at your workspace.
```
