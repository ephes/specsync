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


@pytest.mark.parametrize("outside", [False, True])
def test_init_absolute_ignore(repo, tmp_path, outside):
    target = (tmp_path if outside else repo) / "planning"
    assert main(["init", "--repo-specs-dir", str(target)]) == 0
    assert target.is_dir()
    if outside:
        assert not (repo / ".gitignore").exists()
    else:
        assert "planning" in (repo / ".gitignore").read_text().splitlines()


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
