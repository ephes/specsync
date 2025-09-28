"""Configuration resolution for Specsync."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

from .exceptions import ConfigError
from .fs import find_repo_root


@dataclass
class Config:
    repo_root: Path
    workspace_root: Path
    workspace_subdir: Path
    workspace_specs_dir: Path
    repo_specs_dir: Path
    project_name: str
    require_expose: bool
    match_project: bool
    dry_run: bool
    force: bool
    quiet: bool

    @property
    def filter_summary(self) -> str:
        project = "enabled" if self.match_project else "disabled"
        expose = "required" if self.require_expose else "optional"
        return f"expose={expose}, project={project}"


def load_config(args: Any, *, command: str) -> Config:
    repo_root = find_repo_root(Path.cwd())
    if repo_root is None:
        raise ConfigError("Unable to locate git repository root. Run specsync inside a git repo.")

    pyproject_data = _load_pyproject(repo_root / "pyproject.toml")
    tool_config = _get_tool_config(pyproject_data)

    workspace_root = _resolve_workspace_root(args, tool_config)
    workspace_subdir = Path(tool_config.get("workspace_subdir", "specs"))
    if getattr(args, "repo_specs_dir", None):
        repo_specs_dir_config = Path(getattr(args, "repo_specs_dir"))
    else:
        repo_specs_dir_config = Path(tool_config.get("repo_specs_dir", "specs"))

    repo_specs_dir = (repo_root / repo_specs_dir_config).resolve()
    workspace_specs_dir = (workspace_root / workspace_subdir).resolve()

    filter_config = tool_config.get("filter", {})
    require_expose = bool(filter_config.get("require_expose", True))
    match_project = bool(filter_config.get("match_project", True))

    project_name = _resolve_project_name(args, pyproject_data, tool_config, repo_root)

    return Config(
        repo_root=repo_root,
        workspace_root=workspace_root,
        workspace_subdir=workspace_subdir,
        workspace_specs_dir=workspace_specs_dir,
        repo_specs_dir=repo_specs_dir,
        project_name=project_name,
        require_expose=require_expose,
        match_project=match_project,
        dry_run=bool(getattr(args, "dry_run", False)),
        force=bool(getattr(args, "force", False)),
        quiet=bool(getattr(args, "quiet", False)),
    )


def validate_paths(config: Config, *, command: str) -> None:
    if command == "pull":
        if not config.workspace_root.exists() and not config.dry_run:
            raise ConfigError("Workspace root does not exist; set SPECSYNC_WORKSPACE_ROOT or create the directory.")
        if not config.workspace_specs_dir.exists() and not config.dry_run:
            raise ConfigError(
                f"Workspace specs directory {config.workspace_specs_dir} not found. Create it or adjust workspace_subdir."
            )
    if not config.repo_specs_dir.exists():
        config.repo_specs_dir.mkdir(parents=True, exist_ok=True)


def _load_pyproject(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _get_tool_config(data: dict[str, Any]) -> dict[str, Any]:
    tool = data.get("tool", {})
    return tool.get("specsync", {})


def _resolve_workspace_root(args: Any, tool_config: dict[str, Any]) -> Path:
    candidate = getattr(args, "workspace_root", None) or os.getenv("SPECSYNC_WORKSPACE_ROOT")
    if not candidate:
        raise ConfigError("Workspace root not configured. Use --workspace-root or SPECSYNC_WORKSPACE_ROOT.")
    return Path(candidate).expanduser().resolve()


def _resolve_project_name(
    args: Any,
    pyproject_data: dict[str, Any],
    tool_config: dict[str, Any],
    repo_root: Path,
) -> str:
    # 1. CLI flag
    candidate = getattr(args, "project_name", None)
    if candidate:
        return candidate

    # 2. Environment variable
    env_name = os.getenv("SPECSYNC_PROJECT_NAME")
    if env_name:
        return env_name

    # 3. [tool.specsync] project_name setting
    tool_name = tool_config.get("project_name")
    if tool_name:
        return str(tool_name)

    # 4. Use project name from pyproject.toml [project] table
    project_table = pyproject_data.get("project", {})
    if isinstance(project_table, dict) and "name" in project_table:
        return str(project_table["name"])

    # 5. Fallback to folder name
    return repo_root.name


def _project_name_from_git(repo_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:  # pragma: no cover - git missing
        return None

    if completed.returncode != 0:
        return None

    url = completed.stdout.strip()
    if not url:
        return None

    if url.endswith(".git"):
        url = url[:-4]

    if ":" in url:
        url = url.split(":", 1)[1]
    if "/" in url:
        return url.rsplit("/", 1)[-1]
    return url or None
