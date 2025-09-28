from pathlib import Path

from specsync.config import Config
from specsync.selector import collect_workspace_documents


def make_config(repo_root: Path, workspace_root: Path) -> Config:
    workspace_subdir = Path("specs")
    workspace_specs_dir = workspace_root / workspace_subdir
    repo_specs_dir = repo_root / "specs"
    return Config(
        repo_root=repo_root,
        workspace_root=workspace_root,
        workspace_subdir=workspace_subdir,
        workspace_specs_dir=workspace_specs_dir,
        repo_specs_dir=repo_specs_dir,
        project_name="demo",
        require_expose=True,
        match_project=True,
        dry_run=False,
        force=False,
        quiet=False,
    )


def test_collect_workspace_documents_filters(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    workspace_root = tmp_path / "vault"
    workspace_specs_dir = workspace_root / "specs"
    workspace_specs_dir.mkdir(parents=True)

    good = workspace_specs_dir / "keep.md"
    good.write_text("---\nexpose: true\nproject: demo\n---\n", encoding="utf-8")

    bad = workspace_specs_dir / "skip.md"
    bad.write_text("---\nexpose: false\nproject: other\n---\n", encoding="utf-8")

    config = make_config(repo_root, workspace_root)
    documents, warnings = collect_workspace_documents(config)

    assert [doc.relative_path.as_posix() for doc in documents] == ["keep.md"]
    assert any("expose" in msg for msg in warnings)
