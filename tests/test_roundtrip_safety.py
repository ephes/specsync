"""Round-trip planning and destination-safety tests (temp dirs only)."""

from __future__ import annotations

import os

import pytest

from specsync.cli import main


@pytest.fixture
def env(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "specs").mkdir()
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "proj"\n\n[tool.specsync]\nworkspace_subdir = "specs"\n'
    )
    workspace_root = tmp_path / "workspace"
    (workspace_root / "specs").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(repo)
    monkeypatch.setenv("SPECSYNC_WORKSPACE_ROOT", str(workspace_root))
    monkeypatch.delenv("SPECSYNC_PROJECT_NAME", raising=False)
    return {
        "repo_specs": repo / "specs",
        "ws_specs": workspace_root / "specs",
        "outside": outside,
    }


def _plan_lines(capsys, argv):
    capsys.readouterr()
    assert main(argv) == 0
    out = capsys.readouterr().out
    return [
        line
        for line in out.splitlines()
        if " | " in line and not line.startswith("Action")
    ]


REPO_SPEC = "# Plan\n\nBody text.\n"


def test_push_then_push_and_pull_are_skip(env, capsys):
    (env["repo_specs"] / "plan.md").write_text(REPO_SPEC)

    assert main(["push", "--force"]) == 0
    pushed = (env["ws_specs"] / "plan.md").read_text()
    assert "expose: true" in pushed
    assert "project: proj" in pushed

    assert _plan_lines(capsys, ["push", "--dry-run"]) == ["SKIP | plan.md | unchanged"]
    assert _plan_lines(capsys, ["pull", "--dry-run"]) == ["SKIP | plan.md | unchanged"]


def test_forced_pull_after_push_leaves_repo_untouched(env):
    (env["repo_specs"] / "plan.md").write_text(REPO_SPEC)
    assert main(["push", "--force"]) == 0

    assert main(["pull", "--force"]) == 0
    assert (env["repo_specs"] / "plan.md").read_text() == REPO_SPEC
    assert not (env["repo_specs"] / "plan.md.specsync-bak").exists()


def test_push_with_partial_frontmatter_round_trips(env, capsys):
    (env["repo_specs"] / "plan.md").write_text("---\ntitle: Plan\n---\n\n# Plan\n")
    assert main(["push", "--force"]) == 0
    assert _plan_lines(capsys, ["push", "--dry-run"]) == ["SKIP | plan.md | unchanged"]
    assert _plan_lines(capsys, ["pull", "--dry-run"]) == ["SKIP | plan.md | unchanged"]


def test_pull_then_push_is_skip(env, capsys):
    (env["ws_specs"] / "plan.md").write_text(
        "---\nexpose: true\nproject: proj\n---\n\n# Plan\n"
    )
    assert main(["pull", "--force"]) == 0
    assert _plan_lines(capsys, ["push", "--dry-run"]) == ["SKIP | plan.md | unchanged"]
    assert _plan_lines(capsys, ["pull", "--dry-run"]) == ["SKIP | plan.md | unchanged"]


def test_real_edit_still_conflicts_both_ways(env, capsys):
    (env["repo_specs"] / "plan.md").write_text(REPO_SPEC)
    assert main(["push", "--force"]) == 0

    (env["repo_specs"] / "plan.md").write_text(REPO_SPEC + "\nRepo edit.\n")
    assert _plan_lines(capsys, ["push", "--dry-run"]) == [
        "CONFLICT | plan.md | differs from workspace"
    ]
    assert _plan_lines(capsys, ["pull", "--dry-run"]) == [
        "CONFLICT | plan.md | differs from repo"
    ]


def test_vault_edit_conflicts_on_pull(env, capsys):
    (env["repo_specs"] / "plan.md").write_text(REPO_SPEC)
    assert main(["push", "--force"]) == 0
    ws_file = env["ws_specs"] / "plan.md"
    ws_file.write_text(ws_file.read_text() + "\nVault edit.\n")
    assert _plan_lines(capsys, ["pull", "--dry-run"]) == [
        "CONFLICT | plan.md | differs from repo"
    ]


def test_forced_overwrite_leaves_backup(env):
    (env["repo_specs"] / "plan.md").write_text(REPO_SPEC)
    assert main(["push", "--force"]) == 0
    ws_file = env["ws_specs"] / "plan.md"
    vault_version = ws_file.read_text() + "\nVault edit.\n"
    ws_file.write_text(vault_version)

    assert main(["push", "--force"]) == 0
    assert (env["ws_specs"] / "plan.md.specsync-bak").read_text() == vault_version
    assert "Vault edit." not in ws_file.read_text()

    (env["repo_specs"] / "plan.md").write_text(REPO_SPEC + "\nRepo edit.\n")
    repo_version = (env["repo_specs"] / "plan.md").read_text()
    assert main(["pull", "--force"]) == 0
    assert (env["repo_specs"] / "plan.md.specsync-bak").read_text() == repo_version


def test_push_refuses_symlinked_destination_file(env, capsys):
    (env["repo_specs"] / "plan.md").write_text(REPO_SPEC)
    victim = env["outside"] / "victim.md"
    victim.write_text("precious\n")
    os.symlink(victim, env["ws_specs"] / "plan.md")

    lines = _plan_lines(capsys, ["push", "--dry-run"])
    assert len(lines) == 1 and lines[0].startswith("UNSAFE | plan.md")

    assert main(["push", "--force"]) == 1
    assert victim.read_text() == "precious\n"
    assert (env["ws_specs"] / "plan.md").is_symlink()
    assert not (env["outside"] / "victim.md.specsync-bak").exists()


def test_push_refuses_symlinked_destination_directory(env):
    sub = env["repo_specs"] / "sub"
    sub.mkdir()
    (sub / "plan.md").write_text(REPO_SPEC)
    os.symlink(env["outside"], env["ws_specs"] / "sub")

    assert main(["push", "--force"]) == 1
    assert list(env["outside"].iterdir()) == []


def test_pull_refuses_symlinked_destination_file(env):
    (env["ws_specs"] / "plan.md").write_text(
        "---\nexpose: true\nproject: proj\n---\n\n# Plan\n"
    )
    victim = env["outside"] / "victim.md"
    victim.write_text("precious\n")
    os.symlink(victim, env["repo_specs"] / "plan.md")

    assert main(["pull", "--force"]) == 1
    assert victim.read_text() == "precious\n"
    assert (env["repo_specs"] / "plan.md").is_symlink()


def test_pull_refuses_symlinked_destination_directory(env):
    sub = env["ws_specs"] / "sub"
    sub.mkdir()
    (sub / "plan.md").write_text("---\nexpose: true\nproject: proj\n---\n\n# Plan\n")
    os.symlink(env["outside"], env["repo_specs"] / "sub")

    assert main(["pull", "--force"]) == 1
    assert list(env["outside"].iterdir()) == []


def test_symlinked_temp_file_is_not_followed(env):
    (env["repo_specs"] / "plan.md").write_text(REPO_SPEC)
    victim = env["outside"] / "victim"
    victim.write_text("precious\n")
    os.symlink(victim, env["ws_specs"] / "plan.md.tmp")

    assert main(["push", "--force"]) == 0
    assert victim.read_text() == "precious\n"
    assert "Body text." in (env["ws_specs"] / "plan.md").read_text()


def test_symlinked_backup_path_is_not_followed(env):
    (env["repo_specs"] / "plan.md").write_text(REPO_SPEC)
    (env["ws_specs"] / "plan.md").write_text(
        "---\nexpose: true\nproject: proj\n---\n\nOther\n"
    )
    victim = env["outside"] / "victim"
    victim.write_text("precious\n")
    os.symlink(victim, env["ws_specs"] / "plan.md.specsync-bak")

    assert main(["push", "--force"]) == 1
    assert victim.read_text() == "precious\n"
    assert (env["ws_specs"] / "plan.md.specsync-bak").is_symlink()
    assert "Other" in (env["ws_specs"] / "plan.md").read_text()


def test_destination_turned_symlink_after_planning_is_refused(env):
    from types import SimpleNamespace

    from specsync.config import load_config
    from specsync.sync import build_push_plan, execute_plan

    (env["repo_specs"] / "plan.md").write_text(REPO_SPEC)
    config = load_config(SimpleNamespace(force=True), command="push")
    plan = build_push_plan(config)
    assert [e.state for e in plan.entries] == ["create"]

    victim = env["outside"] / "victim.md"
    victim.write_text("precious\n")
    os.symlink(victim, env["ws_specs"] / "plan.md")

    stats = execute_plan(plan, config)
    assert stats.refused == 1 and stats.created == 0
    assert victim.read_text() == "precious\n"


def test_match_project_disabled_round_trips(env, capsys):
    pyproject = env["repo_specs"].parent / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text() + "\n[tool.specsync.filter]\nmatch_project = false\n"
    )
    (env["repo_specs"] / "plan.md").write_text("---\nproject: other\n---\n\n# Plan\n")
    assert main(["push", "--force"]) == 0
    assert "project" not in (env["ws_specs"] / "plan.md").read_text()
    assert _plan_lines(capsys, ["push", "--dry-run"]) == ["SKIP | plan.md | unchanged"]
    assert _plan_lines(capsys, ["pull", "--dry-run"]) == ["SKIP | plan.md | unchanged"]


def test_destination_root_swapped_for_symlink_after_planning_is_refused(env):
    from types import SimpleNamespace

    from specsync.config import load_config
    from specsync.sync import build_push_plan, execute_plan

    (env["repo_specs"] / "plan.md").write_text(REPO_SPEC)
    config = load_config(SimpleNamespace(force=True), command="push")
    plan = build_push_plan(config)
    assert [e.state for e in plan.entries] == ["create"]

    env["ws_specs"].rmdir()
    os.symlink(env["outside"], env["ws_specs"])

    stats = execute_plan(plan, config)
    assert stats.refused == 1 and stats.created == 0
    assert list(env["outside"].iterdir()) == []


def test_long_destination_name_is_writable_or_refused(env):
    ok = "a" * 230 + ".md"
    (env["repo_specs"] / ok).write_text(REPO_SPEC)
    assert main(["push", "--force"]) == 0
    (env["repo_specs"] / ok).write_text(REPO_SPEC + "\nedit\n")
    assert main(["push", "--force"]) == 0
    assert "edit" in (env["ws_specs"] / ok).read_text()
    assert (env["ws_specs"] / (ok + ".specsync-bak")).exists()


def test_overwrite_without_possible_backup_is_refused(env):
    name = "b" * 245 + ".md"
    (env["repo_specs"] / name).write_text(REPO_SPEC)
    assert main(["push", "--force"]) == 0  # create needs no backup
    pushed = (env["ws_specs"] / name).read_text()
    (env["repo_specs"] / name).write_text(REPO_SPEC + "\nedit\n")
    assert main(["push", "--force"]) == 1
    assert (env["ws_specs"] / name).read_text() == pushed


def test_unicode_filename_round_trips(env, capsys):
    name = "\u00e9" * 100 + ".md"  # 203 UTF-8 bytes; backup name stays under 255
    (env["repo_specs"] / name).write_text(REPO_SPEC)
    assert main(["push", "--force"]) == 0
    (env["repo_specs"] / name).write_text(REPO_SPEC + "\nedit\n")
    assert main(["push", "--force"]) == 0
    assert "edit" in (env["ws_specs"] / name).read_text()
