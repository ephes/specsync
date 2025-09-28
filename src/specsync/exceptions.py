"""Custom exception types for Specsync."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class SpecsyncError(Exception):
    """Base exception for Specsync-specific failures."""


class ConfigError(SpecsyncError):
    """Raised when configuration cannot be resolved."""


class InteractiveError(SpecsyncError):
    """Raised when interactive input is required but unavailable."""


class SecurityError(SpecsyncError):
    """Raised when a security violation is detected."""


@dataclass
class FrontmatterError(SpecsyncError):
    """Raised when a markdown file has invalid frontmatter."""

    path: Path
    message: str
    line: int | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        location = f"{self.path}"
        if self.line is not None:
            location = f"{location}:{self.line}"
        return f"Frontmatter error in {location}: {self.message}"
