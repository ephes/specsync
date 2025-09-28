"""Lightweight logging helpers."""

from __future__ import annotations

import sys
from typing import Final


_LEVELS: Final = {
    "info": ("[INFO]", sys.stdout),
    "warn": ("[WARN]", sys.stderr),
    "error": ("[ERROR]", sys.stderr),
}


def log(level: str, message: str, *, quiet: bool = False) -> None:
    tag, stream = _LEVELS[level]
    if quiet and level == "info":
        return
    stream.write(f"{tag} {message}\n")


def info(message: str, *, quiet: bool = False) -> None:
    log("info", message, quiet=quiet)


def warn(message: str) -> None:
    log("warn", message)


def error(message: str) -> None:
    log("error", message)
