"""Configuration resolution for Specsync."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

import tomllib

from .exceptions import ConfigError
from .fs import find_repo_root
from .logging import info


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
        raise ConfigError(
            "Unable to locate git repository root. Run specsync inside a git repo."
        )

    pyproject_data = _load_pyproject(repo_root / "pyproject.toml")
    tool_config = _get_tool_config(pyproject_data)

    workspace_root = _resolve_workspace_root(args, tool_config)
    workspace_subdir, repo_specs_dir_config = resolve_directories(
        args, tool_config, repo_root=repo_root, workspace_root=workspace_root
    )

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
            raise ConfigError(
                "Workspace root does not exist; set SPECSYNC_WORKSPACE_ROOT or create the directory."
            )
        if not config.workspace_specs_dir.exists() and not config.dry_run:
            raise ConfigError(
                f"Workspace specs directory {config.workspace_specs_dir} not found. Create it or adjust workspace_subdir."
            )
    source = config.workspace_specs_dir if command == "pull" else config.repo_specs_dir
    if config.dry_run and not source.exists():
        info(
            f"Source specs directory {source} not found; dry-run plan is empty.",
            quiet=config.quiet,
        )


def validate_directory_setting(
    value: Any, *, setting: str, source: str, root: Path | None = None
) -> Path:
    """Validate one configured directory value and return it as a relative path.

    Every directory value, whatever its source, names a subdirectory of the
    repository or the workspace root: a non-empty relative path without ``..``
    components. With ``root`` the resolved directory must also stay inside it,
    which refuses symlinks that lead elsewhere.
    """
    label = f"{setting} from {source}"
    if not isinstance(value, str):
        raise ConfigError(f"{label} must be a string, not {type(value).__name__}.")
    if not value.strip():
        raise ConfigError(f"{label} must not be empty.")
    if "\x00" in value or "\\" in value:
        raise ConfigError(
            f"{label} must use '/' separators and no NUL characters: {value!r}."
        )
    if value.startswith(("/", "~")) or PureWindowsPath(value).anchor:
        raise ConfigError(
            f"{label} must be a relative subdirectory, not an absolute or home path: {value!r}."
        )
    parts = [part for part in value.split("/") if part not in ("", ".")]
    if ".." in parts:
        raise ConfigError(f"{label} must not contain '..': {value!r}.")
    if not parts:
        raise ConfigError(f"{label} must name a subdirectory: {value!r}.")
    relative = Path(*parts)
    if root is not None:
        resolved_root = root.resolve()
        resolved = (resolved_root / relative).resolve()
        if resolved == resolved_root or not resolved.is_relative_to(resolved_root):
            raise ConfigError(
                f"{label} does not resolve to a subdirectory of {resolved_root} (symlink?): {value!r}."
            )
    return relative


def resolve_directories(
    args: Any,
    tool_config: Any,
    *,
    repo_root: Path | None = None,
    workspace_root: Path | None = None,
) -> tuple[Path, Path]:
    """Resolve ``(workspace_subdir, repo_specs_dir)`` for init and synchronization.

    Every configured value is validated, including a stored or environment
    value that a higher-precedence source overrides, so an invalid stored
    setting is reported instead of being masked by a command-line override.
    """
    if not hasattr(tool_config, "get"):
        raise ConfigError("[tool.specsync] must be a table.")
    errors: list[str] = []

    def check(value: Any, setting: str, source: str, root: Path | None) -> Path | None:
        try:
            return validate_directory_setting(
                value, setting=setting, source=source, root=root
            )
        except ConfigError as exc:
            errors.append(str(exc))
            return None

    if "workspace_subdir" in tool_config:
        stored, source = tool_config["workspace_subdir"], "[tool.specsync]"
    else:
        stored, source = "specs", "default"
    workspace_subdir = check(stored, "workspace_subdir", source, workspace_root)

    # Lowest precedence first; a later valid candidate replaces an earlier one.
    candidates: list[tuple[Any, str]] = [("specs", "default")]
    if "repo_specs_dir" in tool_config:
        candidates.append((tool_config["repo_specs_dir"], "[tool.specsync]"))
    env_value = os.getenv("SPECSYNC_REPO_SPECS_DIR")
    if env_value:
        candidates.append((env_value, "SPECSYNC_REPO_SPECS_DIR"))
    cli_value = getattr(args, "repo_specs_dir", None)
    if cli_value is not None:
        candidates.append((cli_value, "--repo-specs-dir"))
    repo_specs_dir: Path | None = None
    for value, source in candidates:
        repo_specs_dir = check(value, "repo_specs_dir", source, repo_root)

    if errors or workspace_subdir is None or repo_specs_dir is None:
        raise ConfigError(" ".join(errors))
    return workspace_subdir, repo_specs_dir


def _load_pyproject(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _get_tool_config(data: dict[str, Any]) -> dict[str, Any]:
    tool = data.get("tool", {})
    return tool.get("specsync", {})


def configured_workspace_root(args: Any) -> Path | None:
    """Return the workspace root from the CLI or environment, if configured."""
    candidate = getattr(args, "workspace_root", None) or os.getenv(
        "SPECSYNC_WORKSPACE_ROOT"
    )
    if not candidate:
        return None
    return Path(candidate).expanduser().resolve()


def _resolve_workspace_root(args: Any, tool_config: dict[str, Any]) -> Path:
    workspace_root = configured_workspace_root(args)
    if workspace_root is None:
        raise ConfigError(
            "Workspace root not configured. Use --workspace-root or SPECSYNC_WORKSPACE_ROOT."
        )
    return workspace_root


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
