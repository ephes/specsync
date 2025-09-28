"""Interactive prompt handling."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from .exceptions import InteractiveError
from .logging import info

PromptChoice = Literal["overwrite", "skip", "diff", "quit"]


@dataclass
class PromptState:
    overwrite_all: bool = False
    skip_all: bool = False


class PromptEngine:
    def __init__(self, *, quiet: bool) -> None:
        self.quiet = quiet
        self.state = PromptState()

    def confirm(self, source_path: Path, target_path: Path) -> PromptChoice:
        """Prompt for confirmation with file information.

        Args:
            source_path: The source file path
            target_path: The target file path that would be overwritten

        Returns:
            The user's choice
        """
        if self.state.overwrite_all:
            return "overwrite"
        if self.state.skip_all:
            return "skip"

        if not sys.stdin.isatty():
            raise InteractiveError("Interactive confirmation required; rerun with --force to proceed")

        # Show file information with modification times
        self._show_file_info(source_path, target_path)

        options = "[o]verwrite, [s]kip, [d]iff, [A]ll-overwrite, [S]kip-all, [q]uit?"
        while True:
            info(f"File differs: {target_path}", quiet=self.quiet)
            info(options, quiet=self.quiet)
            try:
                choice = input().strip()
            except EOFError as exc:
                raise InteractiveError("No input available for confirmation; rerun with --force") from exc

            # Case-sensitive options
            if choice == "o":
                return "overwrite"
            if choice == "s":
                return "skip"
            if choice == "d":
                return "diff"
            if choice == "A":  # Capital A for all-overwrite
                self.state.overwrite_all = True
                return "overwrite"
            if choice == "S":  # Capital S for skip-all
                self.state.skip_all = True
                return "skip"
            if choice == "q":
                raise InteractiveError("User quit the operation")

            info("Please enter o, s, d, A, S, or q", quiet=self.quiet)

    def _show_file_info(self, source_path: Path, target_path: Path) -> None:
        """Show modification times for the files being compared."""
        try:
            source_mtime = source_path.stat().st_mtime
            source_time = datetime.fromtimestamp(source_mtime).strftime("%Y-%m-%d %H:%M:%S")
            info(f"  Source modified: {source_time}", quiet=self.quiet)
        except (OSError, FileNotFoundError):
            pass

        try:
            target_mtime = target_path.stat().st_mtime
            target_time = datetime.fromtimestamp(target_mtime).strftime("%Y-%m-%d %H:%M:%S")
            info(f"  Target modified: {target_time}", quiet=self.quiet)
        except (OSError, FileNotFoundError):
            pass
