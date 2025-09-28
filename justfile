#!/usr/bin/env just --justfile

# Show available commands by default
default: help

# Run all tests
test:
    uv run pytest tests/

# Run tests with verbose output
test-verbose:
    uv run pytest tests/ -xvs

# Run tests with coverage
test-coverage:
    uv run pytest tests/ --cov=src/specsync --cov-report=term-missing

# Run linter
lint:
    uv run ruff check src/ tests/

# Fix linting issues
lint-fix:
    uv run ruff check src/ tests/ --fix

# Format code
format:
    uv run ruff format src/ tests/

# Check formatting
format-check:
    uv run ruff format --check src/ tests/

# Run all checks (lint + format + tests)
check: lint format-check test

# Install development dependencies
install:
    uv sync --all-groups

# Build the package
build:
    uv build

# Clean build artifacts
clean:
    rm -rf dist/ build/ *.egg-info
    find src tests -type d -name "__pycache__" -prune -exec rm -rf {} +
    find src tests -type f -name "*.pyc" -delete

# Initialize specsync in current directory
init:
    uv run specsync init

# Show specsync info
info:
    uv run specsync info

# Pull specs from vault (dry-run)
pull-dry:
    uv run specsync pull --dry-run

# Pull specs from vault
pull:
    uv run specsync pull

# Push specs to vault (dry-run)
push-dry:
    uv run specsync push --dry-run

# Push specs to vault
push:
    uv run specsync push

alias specfile-pull := pull
alias specfile-push := push

# Run specsync with custom arguments
run *args:
    uv run specsync {{args}}

# Build documentation
docs-build:
    uv run sphinx-build -b html docs docs/_build/html

# View documentation locally
docs-serve:
    uv run python -m http.server 8000 --directory docs/_build/html

# Clean documentation build artifacts
docs-clean:
    rm -rf docs/_build

# Check documentation for broken links
docs-check:
    uv run sphinx-build -b linkcheck docs docs/_build/linkcheck

# Watch mode for documentation with auto rebuild
docs-watch:
    uv run sphinx-autobuild docs docs/_build/html

# Show this help
help:
    @just --list
