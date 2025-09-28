"""Filesystem utilities used by Specsync."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Iterable

from .exceptions import SecurityError


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_file_atomic(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_within(base: Path, target: Path) -> bool:
    """Check if target path is within base directory."""
    try:
        # Resolve both paths to handle .. and symlinks
        base_resolved = base.resolve()
        target_resolved = target.resolve()
        target_resolved.relative_to(base_resolved)
        return True
    except ValueError:
        return False


def validate_path_security(path: Path, root: Path, follow_symlinks: bool = False) -> None:
    """Validate that a path is safe to access within the given root.

    Args:
        path: Path to validate
        root: Root directory that path must be within
        follow_symlinks: If False, symlinks are not allowed

    Raises:
        SecurityError: If path is outside root or violates security rules
    """
    # Check for symlinks if not allowed
    if not follow_symlinks and path.is_symlink():
        raise SecurityError(f"Symlink not allowed: {path}")

    # Resolve the path to handle .. and symlinks
    try:
        resolved_path = path.resolve()
        resolved_root = root.resolve()
    except (OSError, RuntimeError) as e:
        raise SecurityError(f"Cannot resolve path {path}: {e}")

    # Check if path is within root
    if not is_within(resolved_root, resolved_path):
        raise SecurityError(f"Path {path} is outside allowed root {root}")


def copy_file(source: Path, target: Path) -> None:
    ensure_dir(target.parent)
    shutil.copy2(source, target)


def append_gitignore(repo_root: Path, entry: str, comment: str = "Added by specsync") -> None:
    """Append an entry to .gitignore if not already present.

    Args:
        repo_root: Repository root directory
        entry: Pattern to add to gitignore
        comment: Comment to add before the entry
    """
    gitignore = repo_root / ".gitignore"

    # Normalize the entry for comparison
    normalized_entry = entry.rstrip("/")

    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Check for existing entry (with variations)
        for line in lines:
            cleaned = line.strip().rstrip("/")
            # Remove leading / for comparison
            if cleaned.lstrip("/") == normalized_entry.lstrip("/"):
                return  # Already present

    else:
        ensure_dir(gitignore.parent)
        content = ""

    # Add entry with comment
    with gitignore.open("a", encoding="utf-8") as handle:
        if content and not content.endswith("\n"):
            handle.write("\n")
        handle.write(f"# {comment}\n")
        handle.write(f"{entry}\n")


def iter_markdown_files(root: Path) -> Iterable[Path]:
    """Iterate over markdown files in directory, skipping hidden directories."""
    for path in root.rglob("*.md"):
        # Skip files in hidden directories
        if any(part.startswith(".") for part in path.relative_to(root).parts[:-1]):
            continue
        if path.is_file():
            yield path


def find_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None
