"""Sync planning and execution."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .exceptions import ConfigError, FrontmatterError, SpecsyncError
from .frontmatter import render_frontmatter
from .fs import backup_file, copy_file, unsafe_destination_reason, write_file_atomic
from .logging import info, warn
from .models import ExecutionStats, PlanEntry, SpecDocument, SyncPlan
from .prompt import PromptEngine
from .selector import collect_repo_documents, collect_workspace_documents, load_document


@dataclass
class PlanSummary:
    create: int
    update: int
    conflicts: int
    skip: int
    unsafe: int = 0


def build_pull_plan(config: Config) -> SyncPlan:
    documents, warnings = collect_workspace_documents(config)
    entries: list[PlanEntry] = []

    for doc in documents:
        source = doc.workspace_path
        target = doc.repo_path
        unsafe = unsafe_destination_reason(target, config.repo_specs_dir)
        if unsafe:
            state = "unsafe"
            reason = f"refused: {unsafe}"
            warnings.append(f"Refusing unsafe destination in repo ({unsafe}): {target}")
        elif not target.exists():
            state = "create"
            reason = "missing in repo"
        elif _pull_unchanged(doc, config):
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
        unsafe = unsafe_destination_reason(target, config.workspace_specs_dir)
        if unsafe:
            state = "unsafe"
            reason = f"refused: {unsafe}"
            warnings.append(f"Refusing unsafe destination in workspace ({unsafe}): {target}")
        elif not target.exists():
            state = "create"
            reason = "missing in workspace"
        elif _push_unchanged(doc, target, config):
            state = "skip"
            reason = "unchanged"
        else:
            state = "conflict"
            reason = "differs from workspace"
        entries.append(PlanEntry(document=doc, source_path=source, target_path=target, state=state, reason=reason))

    return SyncPlan(direction="push", entries=entries, warnings=warnings)


def _push_unchanged(doc: SpecDocument, target: Path, config: Config) -> bool:
    """A workspace file is unchanged if it equals what push would write, or the raw repo file."""
    target_bytes = target.read_bytes()
    if target_bytes == _prepare_push_payload(doc, config).encode("utf-8"):
        return True
    return target_bytes == doc.repo_path.read_bytes()


def _pull_unchanged(doc: SpecDocument, config: Config) -> bool:
    """A repo file is unchanged if it equals the workspace file, or if pushing it would
    produce exactly the workspace file (i.e. the workspace only carries the metadata
    that push injects)."""
    workspace_bytes = doc.workspace_path.read_bytes()
    repo_path = doc.repo_path
    if workspace_bytes == repo_path.read_bytes():
        return True
    try:
        repo_doc = load_document(
            repo_path,
            relative=doc.relative_path,
            workspace_path=doc.workspace_path,
            repo_path=repo_path,
        )
    except (FrontmatterError, UnicodeDecodeError):
        return False
    return workspace_bytes == _prepare_push_payload(repo_doc, config).encode("utf-8")


def summarize_plan(plan: SyncPlan) -> PlanSummary:
    create = sum(1 for e in plan.entries if e.state == "create")
    update = sum(1 for e in plan.entries if e.state == "conflict")
    skip = sum(1 for e in plan.entries if e.state == "skip")
    unsafe = sum(1 for e in plan.entries if e.state == "unsafe")
    conflicts = update
    return PlanSummary(create=create, update=update, conflicts=conflicts, skip=skip, unsafe=unsafe)


def execute_plan(plan: SyncPlan, config: Config, *, prompt_engine: PromptEngine | None = None) -> ExecutionStats:
    stats = ExecutionStats()
    for entry in plan.entries:
        if entry.state == "skip":
            stats.add_skipped()
            continue

        if entry.state == "unsafe":
            stats.add_refused()
            continue

        if entry.state == "create":
            if _write(entry, plan.direction, config):
                stats.add_created()
            else:
                stats.add_refused()
            continue

        if entry.state == "conflict":
            action = "overwrite"
            if not config.force:
                if prompt_engine is None:
                    raise SpecsyncError("Prompt engine required for interactive runs")
                while True:
                    choice = prompt_engine.confirm(entry.source_path, entry.target_path)
                    if choice == "diff":
                        _show_diff(entry, plan.direction, config)
                        continue
                    action = "overwrite" if choice == "overwrite" else "skip"
                    break
            if action == "skip":
                stats.add_skipped()
                continue
            if _write(entry, plan.direction, config):
                stats.add_updated()
            else:
                stats.add_refused()
    return stats


def _destination_root(direction: str, config: Config) -> Path:
    if direction == "pull":
        return config.repo_specs_dir
    if direction == "push":
        return config.workspace_specs_dir
    raise ConfigError(f"Unknown direction: {direction}")


def _write(entry: PlanEntry, direction: str, config: Config) -> bool:
    """Write one entry; returns False if the destination became unsafe since planning."""
    target = entry.target_path
    unsafe = unsafe_destination_reason(target, _destination_root(direction, config))
    if unsafe:
        warn(f"Refusing unsafe destination ({unsafe}): {target}")
        return False
    if target.exists():
        try:
            backup = backup_file(target)
        except OSError as exc:
            # e.g. the backup name exceeds the filesystem's name limit: never
            # overwrite without a backup.
            warn(f"Refusing to overwrite {target}: cannot write backup ({exc})")
            return False
        info(f"Backed up {target} to {backup.name}", quiet=config.quiet)
    _copy(entry.source_path, target, direction, entry.document, config)
    return True


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


def _show_diff(entry: PlanEntry, direction: str, config: Config) -> None:
    """Display diff between what would be written and the current target."""
    source, target = entry.source_path, entry.target_path
    if direction == "push":
        source_text = _prepare_push_payload(entry.document, config)
    else:
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
        f"Plan: {summary.create} create, {summary.update} update/conflicts, {summary.skip} skip"
        + (f", {summary.unsafe} refused (unsafe destination)" if summary.unsafe else ""),
        quiet=config.quiet,
    )
    for warning in plan.warnings:
        warn(warning)


def display_plan(plan: SyncPlan) -> None:
    print("Action | Path | Reason")
    print("------------------------")
    for entry in plan.entries:
        rel = entry.document.relative_path.as_posix()
        print(f"{entry.state.upper()} | {rel} | {entry.reason or ''}")
