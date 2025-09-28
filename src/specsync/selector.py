"""Collect markdown documents for syncing."""

from __future__ import annotations

from pathlib import Path

from .exceptions import FrontmatterError
from .frontmatter import FrontmatterResult, parse_frontmatter
from .fs import is_within, iter_markdown_files, read_text
from .models import SpecDocument


def collect_workspace_documents(config) -> tuple[list[SpecDocument], list[str]]:
    base = config.workspace_specs_dir
    documents: list[SpecDocument] = []
    warnings: list[str] = []

    for path in iter_markdown_files(base):
        if path.is_symlink():
            warnings.append(f"Skipping symlink in workspace: {path}")
            continue
        if not is_within(base, path):
            warnings.append(f"Skipping out-of-tree file in workspace: {path}")
            continue

        text = read_text(path)
        result = _parse(path, text)
        frontmatter = result.frontmatter or {}
        metadata_status = "valid"
        if not result.had_frontmatter:
            metadata_status = "missing"
        elif not isinstance(frontmatter.get("expose"), bool):
            metadata_status = "invalid"

        if config.require_expose:
            expose = frontmatter.get("expose")
            if expose is not True:
                warnings.append(f"Filtered out (expose!=true): {path}")
                continue
        if config.match_project:
            project_val = frontmatter.get("project")
            if project_val and project_val != config.project_name:
                warnings.append(f"Filtered out (project mismatch): {path}")
                continue

        relative = path.relative_to(base)
        workspace_path = path
        repo_path = (config.repo_specs_dir / relative).resolve()

        documents.append(
            SpecDocument(
                relative_path=relative,
                workspace_path=workspace_path,
                repo_path=repo_path,
                frontmatter=frontmatter if result.had_frontmatter else None,
                body=result.body,
                metadata_status=metadata_status,
                raw_text=text,
            )
        )

    return documents, warnings


def collect_repo_documents(config) -> tuple[list[SpecDocument], list[str]]:
    base = config.repo_specs_dir
    documents: list[SpecDocument] = []
    warnings: list[str] = []

    for path in iter_markdown_files(base):
        if path.is_symlink():
            warnings.append(f"Skipping symlink in repo: {path}")
            continue
        if not is_within(base, path):
            warnings.append(f"Skipping out-of-tree file in repo: {path}")
            continue

        text = read_text(path)
        result = _parse(path, text)
        frontmatter = result.frontmatter or {}
        metadata_status = "valid"
        if not result.had_frontmatter:
            metadata_status = "missing"
        elif not isinstance(frontmatter.get("expose"), bool):
            metadata_status = "invalid"

        relative = path.relative_to(base)
        workspace_path = (config.workspace_specs_dir / relative).resolve()

        documents.append(
            SpecDocument(
                relative_path=relative,
                workspace_path=workspace_path,
                repo_path=path,
                frontmatter=frontmatter if result.had_frontmatter else None,
                body=result.body,
                metadata_status=metadata_status,
                raw_text=text,
            )
        )

    return documents, warnings


def _parse(path: Path, text: str) -> FrontmatterResult:
    try:
        return parse_frontmatter(text, path=path)
    except FrontmatterError:
        raise
