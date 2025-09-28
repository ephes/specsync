"""Command-line interface for Specsync."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config, validate_paths
from .exceptions import ConfigError, FrontmatterError, InteractiveError, SpecsyncError
from .fs import append_gitignore, ensure_dir, find_repo_root
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
    parser = argparse.ArgumentParser(prog="specsync", description="Synchronize specifications between vault and repo")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workspace-root", dest="workspace_root")
    common.add_argument("--repo-specs-dir", dest="repo_specs_dir")
    common.add_argument("--project-name", dest="project_name")
    common.add_argument("--quiet", action="store_true", dest="quiet")

    op_parent = argparse.ArgumentParser(add_help=False, parents=[common])
    op_parent.add_argument("--dry-run", action="store_true", dest="dry_run")
    op_parent.add_argument("--force", action="store_true", dest="force")

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("pull", parents=[op_parent], help="Pull specs from workspace to repo")
    subparsers.add_parser("push", parents=[op_parent], help="Push specs from repo to workspace")
    subparsers.add_parser("info", parents=[common], help="Show resolved configuration")
    init_parser = subparsers.add_parser("init", parents=[common], help="Initialize specsync in this repo")
    init_parser.add_argument("--include-sample", action="store_true", dest="include_sample")

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
    stats = execute_plan(plan, config, prompt_engine=prompt_engine)
    info(
        f"Created: {stats.created}, Updated: {stats.updated}, Skipped: {stats.skipped}",
        quiet=config.quiet,
    )
    return 0


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
        f"Created: {stats.created}, Updated: {stats.updated}, Skipped: {stats.skipped}",
        quiet=config.quiet,
    )
    return 0


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
        raise ConfigError("Unable to locate git repository root. Run specsync init inside a git repo.")

    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.exists():
        raise ConfigError("pyproject.toml not found; initialize a project first.")

    _ensure_specs_dir(repo_root, args)
    _ensure_pyproject_block(pyproject_path)

    info("specsync initialization complete")
    return 0


def _ensure_specs_dir(repo_root: Path, args) -> None:
    repo_specs_dir = Path(args.repo_specs_dir or "specs")
    target = (repo_root / repo_specs_dir).resolve()
    ensure_dir(target)
    append_gitignore(repo_root, str(repo_specs_dir), comment="Added by specsync")
    if getattr(args, "include_sample", False):
        sample = target / "sample-spec.md"
        if not sample.exists():
            sample.write_text("---\nexpose: true\n---\n\n# Sample Specification\n", encoding="utf-8")


def _ensure_pyproject_block(path: Path) -> None:
    data = path.read_text(encoding="utf-8")
    if "[tool.specsync]" in data:
        return
    block = "\n[tool.specsync]\nworkspace_subdir = \"specs\"\nrepo_specs_dir = \"specs\"\n\n[tool.specsync.filter]\nrequire_expose = true\nmatch_project = true\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(block)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
