"""YAML frontmatter parsing utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .exceptions import FrontmatterError

_FRONTMATTER_START = "---\n"
# Pattern to match the closing --- delimiter at the start of a line
_FRONTMATTER_PATTERN = re.compile(r"^---\s*$", re.MULTILINE)


@dataclass
class FrontmatterResult:
    frontmatter: dict[str, Any] | None
    body: str
    had_frontmatter: bool


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n")


def parse_frontmatter(text: str, *, path: Path) -> FrontmatterResult:
    normalized = _normalize(text)
    if not normalized.startswith(_FRONTMATTER_START):
        return FrontmatterResult(frontmatter=None, body=text, had_frontmatter=False)

    match = _FRONTMATTER_PATTERN.search(normalized, len(_FRONTMATTER_START))
    if not match:
        return FrontmatterResult(frontmatter=None, body=text, had_frontmatter=False)

    # Extract the content between the delimiters
    raw_block = normalized[len(_FRONTMATTER_START) : match.start()]

    # Handle empty frontmatter blocks explicitly
    if raw_block.strip() == "":
        data = {}
    else:
        try:
            data = yaml.safe_load(raw_block)
            if data is None:
                data = {}
        except yaml.YAMLError as exc:
            line = getattr(exc, "problem_mark", None)
            line_num = getattr(line, "line", None)
            raise FrontmatterError(path=path, message=str(exc), line=(line_num + 1) if line_num is not None else None) from exc

    if not isinstance(data, dict):
        raise FrontmatterError(path=path, message="Frontmatter must be a mapping")

    body = normalized[match.end():]
    body = body.lstrip("\n")

    return FrontmatterResult(frontmatter=data, body=body, had_frontmatter=True)


def render_frontmatter(data: dict[str, Any]) -> str:
    yaml_text = yaml.safe_dump(data, sort_keys=False).strip()
    return f"---\n{yaml_text}\n---\n"
