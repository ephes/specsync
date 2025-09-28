"""Dataclasses describing Specsync entities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


MetadataStatus = Literal["valid", "invalid", "missing", "metadata_injected"]
PlanState = Literal["create", "update", "conflict", "skip"]
SyncDirection = Literal["pull", "push"]


@dataclass
class SpecDocument:
    relative_path: Path
    workspace_path: Path
    repo_path: Path
    frontmatter: dict | None
    body: str
    metadata_status: MetadataStatus
    raw_text: str


@dataclass
class PlanEntry:
    document: SpecDocument
    source_path: Path
    target_path: Path
    state: PlanState
    reason: str | None = None


@dataclass
class SyncPlan:
    direction: SyncDirection
    entries: list[PlanEntry]
    warnings: list[str]


@dataclass
class ExecutionStats:
    created: int = 0
    updated: int = 0
    skipped: int = 0

    def add_created(self) -> None:
        self.created += 1

    def add_updated(self) -> None:
        self.updated += 1

    def add_skipped(self) -> None:
        self.skipped += 1
