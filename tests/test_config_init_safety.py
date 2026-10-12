import tomllib

import pytest

from specsync.cli import main


def snapshot(root):
    return {
        str(p.relative_to(root)): p.read_bytes() if p.is_file() else None
        for p in root.rglob("*")
    }


@pytest.fixture
def repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "pyproject.toml").write_text('[project]\nname = "demo"\n')
    monkeypatch.chdir(repo)
    monkeypatch.delenv("SPECSYNC_REPO_SPECS_DIR", raising=False)
    monkeypatch.setenv("SPECSYNC_WORKSPACE_ROOT", str(tmp_path / "vault"))
    return repo


@pytest.mark.parametrize("command", ["pull", "push"])
@pytest.mark.parametrize("missing_workspace", [False, True])
def test_dry_run_preserves_tree(repo, tmp_path, command, missing_workspace):
    if not missing_workspace:
        vault = tmp_path / "vault" / "specs"
        vault.mkdir(parents=True)
        (vault / "note.md").write_text("---\nexpose: true\n---\n# Note\n")
    before = snapshot(tmp_path)
    assert main([command, "--dry-run"]) == 0
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "existing",
    [
        "# Configure [tool.specsync] later\n",
        '[project]\nname = "[tool.specsync]"\n',
        "[tool.specsync.filter]\nrequire_expose = false\n",
        '[tool.specsync]\nrepo_specs_dir = "planning" # retain\n',
        "[tool.specsync]\nfilter = {require_expose = false}\n",
    ],
)
def test_init_parses_and_preserves_settings(repo, existing):
    path = repo / "pyproject.toml"
    path.write_text(existing)
    assert main(["init"]) == 0
    result = tomllib.loads(path.read_text())["tool"]["specsync"]
    assert result["workspace_subdir"] == "specs"
    assert result["repo_specs_dir"] == (
        "planning" if "planning" in existing else "specs"
    )
    assert result["filter"]["require_expose"] == ("false" not in existing)
    assert result["filter"]["match_project"] is True
    if "# retain" in existing:
        assert "# retain" in path.read_text()
    before = snapshot(repo)
    assert main(["init"]) == 0
    assert snapshot(repo) == before


@pytest.mark.parametrize("command", ["init", "push", "pull"])
@pytest.mark.parametrize(
    "level,expected",
    [("cli", "cli"), ("env", "env"), ("toml", "toml"), ("default", "specs")],
)
def test_directory_precedence(repo, tmp_path, monkeypatch, command, level, expected):
    if level != "default":
        (repo / "pyproject.toml").write_text(
            '[tool.specsync]\nrepo_specs_dir = "toml"\n'
        )
    if level in ("cli", "env"):
        monkeypatch.setenv("SPECSYNC_REPO_SPECS_DIR", "env")
    vault = tmp_path / "vault" / "specs"
    vault.mkdir(parents=True)
    (vault / "note.md").write_text("---\nexpose: true\n---\n# Note\n")
    if command == "push":
        for name in ("cli", "env", "toml", "specs"):
            (repo / name).mkdir()
            (repo / name / f"{name}.md").write_text(f"# {name}\n")
    args = [command]
    if command != "init":
        args += ["--force"]
    if level == "cli":
        args += ["--repo-specs-dir", "cli"]
    assert main(args) == 0
    if command == "push":
        assert {p.name for p in vault.glob("*.md")} == {"note.md", f"{expected}.md"}
    else:
        assert (repo / expected).is_dir()
        assert all(
            not (repo / name).exists()
            for name in ("cli", "env", "toml", "specs")
            if name != expected
        )
        if command == "init":
            assert expected in (repo / ".gitignore").read_text().splitlines()


def test_init_invalid_toml_preserves_tree(repo):
    (repo / "pyproject.toml").write_text("[broken")
    before = snapshot(repo)
    assert main(["init"]) == 1
    assert snapshot(repo) == before


@pytest.mark.parametrize("source", ["cli", "env"])
def test_init_persists_missing_directory_default(repo, tmp_path, monkeypatch, source):
    args = ["init"]
    if source == "cli":
        args += ["--repo-specs-dir", "planning"]
    else:
        monkeypatch.setenv("SPECSYNC_REPO_SPECS_DIR", "planning")
    assert main(args) == 0
    monkeypatch.delenv("SPECSYNC_REPO_SPECS_DIR", raising=False)
    vault = tmp_path / "vault" / "specs"
    vault.mkdir(parents=True)
    (vault / "note.md").write_text("---\nexpose: true\n---\n# Note\n")
    assert main(["pull", "--force"]) == 0
    assert (repo / "planning" / "note.md").is_file()
    assert not (repo / "specs").exists()


def test_init_refuses_symlinked_pyproject(repo, tmp_path):
    path = repo / "pyproject.toml"
    shared = tmp_path / "shared.toml"
    path.rename(shared)
    path.symlink_to(shared)
    before = snapshot(tmp_path)
    assert main(["init"]) == 1
    assert path.is_symlink()
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("value", ["5", "[]", '""'])
def test_init_invalid_directory_preserves_tree(repo, value):
    (repo / "pyproject.toml").write_text(f"[tool.specsync]\nrepo_specs_dir = {value}\n")
    before = snapshot(repo)
    assert main(["init"]) == 1
    assert snapshot(repo) == before


@pytest.fixture
def errors(monkeypatch):
    """Collect reported errors; the logging streams are bound at import time."""
    messages = []
    monkeypatch.setattr("specsync.cli.error", messages.append)
    return messages


INVALID_DIRECTORIES = [
    "/abs/specs",
    "../outside",
    "specs/../../outside",
    "..",
    ".",
    "./",
    "~/specs",
    "a\\b",
    "C:/specs",
    " ",
]


def _toml(**settings):
    lines = "".join(f"{key} = {value}\n" for key, value in settings.items())
    return f"[tool.specsync]\n{lines}"


def _quoted(value):
    return "'" + value + "'"


@pytest.mark.parametrize("command", ["init", "push", "pull", "info"])
@pytest.mark.parametrize("setting", ["repo_specs_dir", "workspace_subdir"])
@pytest.mark.parametrize("value", INVALID_DIRECTORIES)
def test_invalid_stored_directory_refused(
    repo, tmp_path, errors, command, setting, value
):
    (repo / "pyproject.toml").write_text(_toml(**{setting: _quoted(value)}))
    before = snapshot(tmp_path)
    args = [command] if command in ("init", "info") else [command, "--force"]
    assert main(args) == 1
    assert f"{setting} from [tool.specsync]" in "\n".join(errors)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("command", ["init", "push", "pull"])
@pytest.mark.parametrize("value", ["/abs/specs", "../outside", 5, "[]", "''"])
def test_cli_override_does_not_mask_invalid_stored_directory(
    repo, tmp_path, errors, command, value
):
    stored = _quoted(value) if isinstance(value, str) and "/" in value else value
    (repo / "pyproject.toml").write_text(_toml(repo_specs_dir=stored))
    before = snapshot(tmp_path)
    assert main([command, "--repo-specs-dir", "planning"]) == 1
    assert "repo_specs_dir from [tool.specsync]" in "\n".join(errors)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("command", ["init", "push", "pull"])
def test_cli_override_does_not_mask_invalid_environment_directory(
    repo, tmp_path, monkeypatch, errors, command
):
    monkeypatch.setenv("SPECSYNC_REPO_SPECS_DIR", "../outside")
    before = snapshot(tmp_path)
    assert main([command, "--repo-specs-dir", "planning"]) == 1
    assert "repo_specs_dir from SPECSYNC_REPO_SPECS_DIR" in "\n".join(errors)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("command", ["init", "push", "pull"])
@pytest.mark.parametrize("source", ["cli", "env"])
@pytest.mark.parametrize("value", INVALID_DIRECTORIES)
def test_invalid_override_directory_refused(
    repo, tmp_path, monkeypatch, errors, command, source, value
):
    args = [command]
    if source == "cli":
        args += [f"--repo-specs-dir={value}"]
        label = "--repo-specs-dir"
    else:
        monkeypatch.setenv("SPECSYNC_REPO_SPECS_DIR", value)
        label = "SPECSYNC_REPO_SPECS_DIR"
    before = snapshot(tmp_path)
    assert main(args) == 1
    assert f"repo_specs_dir from {label}" in "\n".join(errors)
    assert snapshot(tmp_path) == before


def test_all_invalid_directories_reported_together(repo, monkeypatch, errors):
    (repo / "pyproject.toml").write_text(
        _toml(repo_specs_dir="'/stored'", workspace_subdir="'../vault'")
    )
    monkeypatch.setenv("SPECSYNC_REPO_SPECS_DIR", "../env")
    assert main(["push", "--repo-specs-dir", "/cli"]) == 1
    err = "\n".join(errors)
    for label in (
        "workspace_subdir from [tool.specsync]",
        "repo_specs_dir from [tool.specsync]",
        "repo_specs_dir from SPECSYNC_REPO_SPECS_DIR",
        "repo_specs_dir from --repo-specs-dir",
    ):
        assert label in err


@pytest.mark.parametrize("command", ["init", "push", "pull"])
def test_symlinked_repo_directory_outside_repository_refused(
    repo, tmp_path, errors, command
):
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "specs").symlink_to(outside, target_is_directory=True)
    before = snapshot(tmp_path)
    assert main([command]) == 1
    assert "does not resolve to a subdirectory" in "\n".join(errors)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("command", ["push", "pull"])
def test_symlinked_workspace_subdir_outside_workspace_refused(
    repo, tmp_path, errors, command
):
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "vault").mkdir()
    (tmp_path / "vault" / "specs").symlink_to(outside, target_is_directory=True)
    (repo / "specs").mkdir()
    (repo / "specs" / "note.md").write_text("# Note\n")
    before = snapshot(tmp_path)
    assert main([command, "--force"]) == 1
    assert "workspace_subdir from default" in "\n".join(errors)
    assert snapshot(tmp_path) == before


def test_nested_relative_directories_accepted(repo, tmp_path):
    (repo / "pyproject.toml").write_text(
        _toml(repo_specs_dir="'./docs//specs/'", workspace_subdir="'notes/specs'")
    )
    vault = tmp_path / "vault" / "notes" / "specs"
    vault.mkdir(parents=True)
    (vault / "note.md").write_text("---\nexpose: true\n---\n# Note\n")
    assert main(["pull", "--force"]) == 0
    assert (repo / "docs" / "specs" / "note.md").is_file()
    assert main(["init"]) == 0
    assert "docs/specs" in (repo / ".gitignore").read_text().splitlines()


def test_empty_cli_directory_refused_and_empty_environment_is_unset(
    repo, tmp_path, monkeypatch, errors
):
    before = snapshot(tmp_path)
    assert main(["init", "--repo-specs-dir="]) == 1
    assert "repo_specs_dir from --repo-specs-dir" in "\n".join(errors)
    assert snapshot(tmp_path) == before
    monkeypatch.setenv("SPECSYNC_REPO_SPECS_DIR", "")
    assert main(["init"]) == 0
    assert (repo / "specs").is_dir()
