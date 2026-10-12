"""Command-line interface for Specsync."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

import tomlkit

from .config import load_config, resolve_repo_specs_dir, validate_paths
from .exceptions import ConfigError, FrontmatterError, InteractiveError, SpecsyncError
from .fs import append_gitignore, ensure_dir, find_repo_root, write_file_atomic
from .logging import error, info
from .prompt import PromptEngine
from .sync import (
    build_pull_plan,
    build_push_plan,
    display_plan,
    execute_plan,
    log_plan,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="specsync", description="Synchronize specifications between vault and repo"
    )

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workspace-root", dest="workspace_root")
    common.add_argument("--repo-specs-dir", dest="repo_specs_dir")
    common.add_argument("--project-name", dest="project_name")
    common.add_argument("--quiet", action="store_true", dest="quiet")

    op_parent = argparse.ArgumentParser(add_help=False, parents=[common])
    op_parent.add_argument("--dry-run", action="store_true", dest="dry_run")
    op_parent.add_argument("--force", action="store_true", dest="force")

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "pull", parents=[op_parent], help="Pull specs from workspace to repo"
    )
    subparsers.add_parser(
        "push", parents=[op_parent], help="Push specs from repo to workspace"
    )
    subparsers.add_parser("info", parents=[common], help="Show resolved configuration")
    init_parser = subparsers.add_parser(
        "init", parents=[common], help="Initialize specsync in this repo"
    )
    init_parser.add_argument(
        "--include-sample", action="store_true", dest="include_sample"
    )

    parser.add_argument("--version", action="version", version="specsync 0.1.0")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "pull":
            return _cmd_pull(args)
        if args.command == "push":
            return _cmd_push(args)
        if args.command == "info":
            return _cmd_info(args)
        if args.command == "init":
            return _cmd_init(args)
        parser.error(f"Unknown command: {args.command}")
    except ConfigError as err:
        error(str(err))
        return 1
    except FrontmatterError as err:
        error(str(err))
        return 1
    except InteractiveError as err:
        error(str(err))
        return 2
    except SpecsyncError as err:
        error(str(err))
        return 1
    except Exception as err:  # pragma: no cover - catch-all safeguard
        error(f"Unexpected failure: {err}")
        return 3
    return 0


def _cmd_pull(args) -> int:
    config = load_config(args, command="pull")
    validate_paths(config, command="pull")

    plan = build_pull_plan(config)
    log_plan(plan, config)
    if config.dry_run:
        display_plan(plan)
        return 0

    prompt_engine = None if config.force else PromptEngine(quiet=config.quiet)
    ensure_dir(config.repo_specs_dir)
    stats = execute_plan(plan, config, prompt_engine=prompt_engine)
    info(
        f"Created: {stats.created}, Updated: {stats.updated}, Skipped: {stats.skipped}, Refused: {stats.refused}",
        quiet=config.quiet,
    )
    return 1 if stats.refused else 0


def _cmd_push(args) -> int:
    config = load_config(args, command="push")
    validate_paths(config, command="push")

    plan = build_push_plan(config)
    log_plan(plan, config)
    if config.dry_run:
        display_plan(plan)
        return 0

    prompt_engine = None if config.force else PromptEngine(quiet=config.quiet)
    ensure_dir(config.workspace_specs_dir)
    stats = execute_plan(plan, config, prompt_engine=prompt_engine)
    info(
        f"Created: {stats.created}, Updated: {stats.updated}, Skipped: {stats.skipped}, Refused: {stats.refused}",
        quiet=config.quiet,
    )
    return 1 if stats.refused else 0


def _cmd_info(args) -> int:
    config = load_config(args, command="info")
    info(f"Repo root: {config.repo_root}")
    info(f"Workspace root: {config.workspace_root}")
    info(f"Workspace specs dir: {config.workspace_specs_dir}")
    info(f"Repo specs dir: {config.repo_specs_dir}")
    info(f"Project name: {config.project_name}")
    info(f"Filters: {config.filter_summary}")
    return 0


def _cmd_init(args) -> int:
    repo_root = find_repo_root(Path.cwd())
    if repo_root is None:
        raise ConfigError(
            "Unable to locate git repository root. Run specsync init inside a git repo."
        )

    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.exists():
        raise ConfigError("pyproject.toml not found; initialize a project first.")

    _ensure_pyproject_block(pyproject_path, args)
    _ensure_specs_dir(repo_root, args)

    info("specsync initialization complete")
    return 0


def _ensure_specs_dir(repo_root: Path, args) -> None:
    data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    repo_specs_dir = resolve_repo_specs_dir(
        args, data.get("tool", {}).get("specsync", {})
    )
    target = (repo_root / repo_specs_dir).resolve()
    ensure_dir(target)
    try:
        ignore_entry = target.relative_to(repo_root).as_posix()
    except ValueError:
        info(
            f"Specs directory {target} is outside the repository; no gitignore entry added."
        )
    else:
        append_gitignore(repo_root, ignore_entry, comment="Added by specsync")
    if getattr(args, "include_sample", False):
        sample = target / "sample-spec.md"
        if not sample.exists():
            sample.write_text(
                "---\nexpose: true\n---\n\n# Sample Specification\n", encoding="utf-8"
            )


def _ensure_pyproject_block(path: Path, args) -> None:
    if path.is_symlink():
        raise ConfigError("Refusing to replace symlinked pyproject.toml.")
    original = path.read_text(encoding="utf-8")
    try:
        tomllib.loads(original)
        document = tomlkit.parse(original)
        tool = document.setdefault("tool", tomlkit.table())
        settings = tool.setdefault("specsync", tomlkit.table())
        selected_dir = resolve_repo_specs_dir(args, settings)
        settings.setdefault("workspace_subdir", "specs")
        settings.setdefault("repo_specs_dir", str(selected_dir))
        filters = settings.setdefault("filter", tomlkit.table())
        filters.setdefault("require_expose", True)
        filters.setdefault("match_project", True)
        updated = tomlkit.dumps(document)
        tomllib.loads(updated)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ConfigError(f"Invalid specsync configuration in {path}: {exc}") from exc
    if updated != original:
        write_file_atomic(path, updated)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
