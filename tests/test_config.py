import argparse

import pytest

from specsync.config import load_config, validate_paths
from specsync.exceptions import ConfigError


def make_args(**overrides):
    defaults = {
        "workspace_root": None,
        "repo_specs_dir": None,
        "project_name": None,
        "dry_run": False,
        "force": False,
        "quiet": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


@pytest.fixture()
def repo_layout(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    pyproject = repo_root / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "demo-project"

[tool.specsync]
workspace_subdir = "specs"
repo_specs_dir = "specs"
project_name = "demo"

[tool.specsync.filter]
require_expose = true
match_project = true
""",
        encoding="utf-8",
    )
    return repo_root


def test_load_config_resolves_project_from_cli(monkeypatch, repo_layout, tmp_path):
    workspace = tmp_path / "vault"
    workspace.mkdir()
    args = make_args(project_name="cli-project")
    monkeypatch.setenv("SPECSYNC_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(repo_layout)
    config = load_config(args, command="pull")
    assert config.project_name == "cli-project"
    assert config.workspace_specs_dir == workspace / "specs"


def test_load_config_requires_workspace(monkeypatch, repo_layout):
    monkeypatch.delenv("SPECSYNC_WORKSPACE_ROOT", raising=False)
    monkeypatch.chdir(repo_layout)
    args = make_args()
    with pytest.raises(ConfigError):
        load_config(args, command="pull")


def test_validate_paths_creates_repo_dir(monkeypatch, repo_layout, tmp_path):
    workspace = tmp_path / "vault"
    workspace.mkdir()
    args = make_args()
    monkeypatch.setenv("SPECSYNC_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(repo_layout)
    config = load_config(args, command="push")
    specs_dir = config.repo_specs_dir
    assert not specs_dir.exists()
    validate_paths(config, command="push")
    assert specs_dir.exists()


def test_project_name_resolution_order(monkeypatch, tmp_path):
    """Test that project_name resolution follows the correct precedence order."""
    repo = tmp_path / "test-repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    workspace = tmp_path / "vault"
    workspace.mkdir()

    monkeypatch.chdir(repo)
    monkeypatch.setenv("SPECSYNC_WORKSPACE_ROOT", str(workspace))

    # Write pyproject.toml with both [project] and [tool.specsync] names
    pyproject = repo / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "from-project-table"

[tool.specsync]
project_name = "from-tool-specsync"
""")

    # Test 1: CLI flag takes precedence
    args = make_args(project_name="from-cli")
    config = load_config(args, command="info")
    assert config.project_name == "from-cli"

    # Test 2: Environment variable comes next
    args = make_args(project_name=None)
    monkeypatch.setenv("SPECSYNC_PROJECT_NAME", "from-env")
    config = load_config(args, command="info")
    assert config.project_name == "from-env"

    # Test 3: [tool.specsync] comes next
    monkeypatch.delenv("SPECSYNC_PROJECT_NAME")
    config = load_config(args, command="info")
    assert config.project_name == "from-tool-specsync"

    # Test 4: [project] table comes next
    pyproject.write_text("""
[project]
name = "from-project-table"
""")
    config = load_config(args, command="info")
    assert config.project_name == "from-project-table"

    # Test 5: Folder name as fallback
    pyproject.write_text("")  # Empty pyproject.toml
    config = load_config(args, command="info")
    assert config.project_name == repo.name
