"""Sync planning and execution."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .exceptions import ConfigError, SpecsyncError
from .frontmatter import render_frontmatter
from .fs import copy_file, hash_file, write_file_atomic
from .logging import info, warn
from .models import ExecutionStats, PlanEntry, SyncPlan
from .prompt import PromptEngine
from .selector import collect_repo_documents, collect_workspace_documents


@dataclass
class PlanSummary:
    create: int
    update: int
    conflicts: int
    skip: int


def build_pull_plan(config: Config) -> SyncPlan:
    documents, warnings = collect_workspace_documents(config)
    entries: list[PlanEntry] = []

    for doc in documents:
        source = doc.workspace_path
        target = doc.repo_path
        if not target.exists():
            state = "create"
            reason = "missing in repo"
        else:
            if hash_file(source) == hash_file(target):
                state = "skip"
                reason = "unchanged"
            else:
                state = "conflict"
                reason = "differs from repo"
        entries.append(PlanEntry(document=doc, source_path=source, target_path=target, state=state, reason=reason))

    return SyncPlan(direction="pull", entries=entries, warnings=warnings)


def build_push_plan(config: Config) -> SyncPlan:
    documents, warnings = collect_repo_documents(config)
    entries: list[PlanEntry] = []

    for doc in documents:
        source = doc.repo_path
        target = doc.workspace_path
        if not target.exists():
            state = "create"
            reason = "missing in workspace"
        else:
            if hash_file(source) == hash_file(target):
                state = "skip"
                reason = "unchanged"
            else:
                state = "conflict"
                reason = "differs from workspace"
        entries.append(PlanEntry(document=doc, source_path=source, target_path=target, state=state, reason=reason))

    return SyncPlan(direction="push", entries=entries, warnings=warnings)


def summarize_plan(plan: SyncPlan) -> PlanSummary:
    create = sum(1 for e in plan.entries if e.state == "create")
    update = sum(1 for e in plan.entries if e.state == "conflict")
    skip = sum(1 for e in plan.entries if e.state == "skip")
    conflicts = update
    return PlanSummary(create=create, update=update, conflicts=conflicts, skip=skip)


def execute_plan(plan: SyncPlan, config: Config, *, prompt_engine: PromptEngine | None = None) -> ExecutionStats:
    stats = ExecutionStats()
    for entry in plan.entries:
        if entry.state == "skip":
            stats.add_skipped()
            continue

        if entry.state == "create":
            _copy(entry.source_path, entry.target_path, plan.direction, entry.document, config)
            stats.add_created()
            continue

        if entry.state == "conflict":
            action = "overwrite"
            if not config.force:
                if prompt_engine is None:
                    raise SpecsyncError("Prompt engine required for interactive runs")
                while True:
                    choice = prompt_engine.confirm(entry.source_path, entry.target_path)
                    if choice == "diff":
                        _show_diff(entry.source_path, entry.target_path, config)
                        continue
                    action = "overwrite" if choice == "overwrite" else "skip"
                    break
            if action == "skip":
                stats.add_skipped()
                continue
            _copy(entry.source_path, entry.target_path, plan.direction, entry.document, config)
            stats.add_updated()
    return stats


def _copy(source: Path, target: Path, direction: str, doc, config: Config) -> None:
    if direction == "pull":
        copy_file(source, target)
        return

    if direction == "push":
        payload = _prepare_push_payload(doc, config)
        write_file_atomic(target, payload)
        return

    raise ConfigError(f"Unknown direction: {direction}")


def _prepare_push_payload(doc, config: Config) -> str:
    if doc.frontmatter is None or doc.metadata_status in {"missing", "invalid"}:
        metadata = dict(doc.frontmatter or {})
        metadata["expose"] = True
        if config.match_project:
            metadata["project"] = config.project_name
        else:
            metadata.pop("project", None)
        body = doc.body
        prefix = render_frontmatter(metadata)
        doc.metadata_status = "metadata_injected"
        return prefix + ("\n" + body if body else "")

    metadata = dict(doc.frontmatter)
    changed = False
    if metadata.get("expose") is not True:
        metadata["expose"] = True
        changed = True
    if config.match_project:
        if metadata.get("project") != config.project_name:
            metadata["project"] = config.project_name
            changed = True
    else:
        if "project" in metadata:
            metadata.pop("project")
            changed = True

    if not changed:
        return doc.raw_text

    prefix = render_frontmatter(metadata)
    body = doc.body
    doc.metadata_status = "metadata_injected"
    return prefix + ("\n" + body if body else "")


def _show_diff(source: Path, target: Path, config: Config) -> None:
    """Display diff between source and target files."""
    source_text = source.read_text(encoding="utf-8") if source.exists() else ""
    target_text = target.read_text(encoding="utf-8") if target.exists() else ""
    diff = difflib.unified_diff(
        target_text.splitlines(),
        source_text.splitlines(),
        fromfile=str(target),
        tofile=str(source),
        lineterm="",
    )
    count = 0
    for line in diff:
        info(line, quiet=config.quiet)
        count += 1
        if count >= 200:
            info("[... diff truncated, 200+ lines ...]", quiet=config.quiet)
            break


def log_plan(plan: SyncPlan, config: Config) -> None:
    summary = summarize_plan(plan)
    info(
        f"Plan: {summary.create} create, {summary.update} update/conflicts, {summary.skip} skip", quiet=config.quiet
    )
    for warning in plan.warnings:
        warn(warning)


def display_plan(plan: SyncPlan) -> None:
    print("Action | Path | Reason")
    print("------------------------")
    for entry in plan.entries:
        rel = entry.document.relative_path.as_posix()
        print(f"{entry.state.upper()} | {rel} | {entry.reason or ''}")
