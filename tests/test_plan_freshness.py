"""Synthetic races between planning, prompts and publication."""

import errno
import os

import pytest

from specsync.config import Config
from specsync.fs import write_file_atomic
from specsync.sync import build_pull_plan, build_push_plan, execute_plan


@pytest.fixture(params=["push", "pull"])
def planned(tmp_path, request):
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    repo.mkdir()
    workspace.mkdir()
    config = Config(
        repo,
        workspace,
        workspace,
        workspace,
        repo,
        "proj",
        True,
        True,
        False,
        False,
        True,
    )
    source, target = (repo / "note.md", workspace / "note.md")
    if request.param == "pull":
        source, target = target, source
    source.write_text("---\nexpose: true\nproject: proj\n---\n\nOriginal\n")
    build = build_push_plan if request.param == "push" else build_pull_plan
    return config, source, target, build


@pytest.mark.parametrize("change", ["edit", "replace", "remove"])
@pytest.mark.parametrize("during_prompt", [False, True])
def test_source_changes_refused(planned, change, during_prompt):
    config, source, target, build = planned
    if during_prompt:
        target.write_text("Destination\n")
    plan = build(config)

    def mutate():
        if change == "edit":
            source.write_text("New content\n")
        elif change == "replace":
            replacement = source.with_suffix(".replacement")
            replacement.write_bytes(source.read_bytes())
            replacement.replace(source)
        else:
            source.unlink()

    class Prompt:
        calls = 0

        def confirm(self, *_):
            self.calls += 1
            if self.calls == 1:
                return "diff"
            mutate()
            return "overwrite"

    if not during_prompt:
        mutate()
    stats = execute_plan(plan, config, prompt_engine=Prompt())
    assert stats.refused == 1
    assert stats.created == stats.updated == 0
    if during_prompt:
        assert target.read_text() == "Destination\n"
    else:
        assert not target.exists()
    assert not target.with_suffix(".md.specsync-bak").exists()


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("force", [False, True])
def test_destination_changes_preserve_file_and_backup(planned, existing, force):
    config, _, target, build = planned
    config.force = force
    if existing:
        target.write_text("Old target\n")
    backup = target.with_suffix(".md.specsync-bak")
    backup.write_text("Prior backup\n")
    plan = build(config)

    class Prompt:
        def confirm(self, *_):
            target.write_text("Concurrent edit\n")
            return "overwrite"

    if force or not existing:
        target.write_text("Concurrent edit\n")
    stats = execute_plan(plan, config, prompt_engine=Prompt())
    assert stats.refused == 1
    assert target.read_text() == "Concurrent edit\n"
    assert backup.read_text() == "Prior backup\n"


def test_exclusive_publication_race(tmp_path, monkeypatch):
    target = tmp_path / "target.md"
    original_link = os.link

    def raced_link(source, destination):
        target.write_text("Concurrent creation\n")
        return original_link(source, destination)

    monkeypatch.setattr(os, "link", raced_link)
    with pytest.raises(FileExistsError):
        write_file_atomic(target, "Planned\n", exclusive=True)
    assert target.read_text() == "Concurrent creation\n"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("collision", [False, True])
def test_exclusive_publication_without_hardlinks(tmp_path, monkeypatch, collision):
    target = tmp_path / "target.md"

    def unsupported_link(*_):
        if collision:
            target.write_text("Concurrent creation\n")
        raise OSError(errno.ENOTSUP, "No hard links")

    monkeypatch.setattr(os, "link", unsupported_link)
    if collision:
        with pytest.raises(FileExistsError):
            write_file_atomic(target, "Planned\n", exclusive=True)
        assert target.read_text() == "Concurrent creation\n"
    else:
        write_file_atomic(target, "Planned\n", exclusive=True)
        assert target.read_text() == "Planned\n"
    assert list(tmp_path.iterdir()) == [target]


def test_diff_uses_snapshot(planned, monkeypatch):
    from specsync.sync import _show_diff

    lines = []
    monkeypatch.setattr("specsync.sync.info", lambda line, **_: lines.append(line))

    config, source, target, build = planned
    config.quiet = False
    target.write_text("Destination\n")
    plan = build(config)
    source.write_text("New content\n")
    _show_diff(plan.entries[0], plan.direction, config)
    output = "\n".join(lines)
    assert "+Original" in output
    assert "New content" not in output


def test_pull_preserves_source_stat(planned):
    config, source, target, build = planned
    if build is build_push_plan:
        return
    source.chmod(0o640)
    os.utime(source, ns=(1_600_000_000_000_000_000, 1_600_000_000_000_000_000))
    source_stat = source.stat()
    assert execute_plan(build(config), config).created == 1
    assert target.stat().st_mode == source_stat.st_mode
    assert target.stat().st_mtime_ns == source_stat.st_mtime_ns


@pytest.mark.parametrize("failure", ["write", "metadata", "replacement"])
def test_exclusive_fallback_cleans_failed_creation(tmp_path, monkeypatch, failure):
    from pathlib import Path

    target = tmp_path / "target.md"
    original_open = Path.open

    def unsupported_link(*_):
        raise OSError(errno.ENOTSUP, "No hard links")

    class FailedWriter:
        def __enter__(self):
            self.handle = original_open(target, "xb")
            return self

        def fileno(self):
            return self.handle.fileno()

        def write(self, data):
            self.handle.write(data[:3])
            if failure == "replacement":
                replacement = tmp_path / "replacement"
                replacement.write_text("Another editor\n")
                replacement.replace(target)
            raise OSError(errno.ENOSPC, "Synthetic write failure")

        def __exit__(self, *_):
            self.handle.close()

    def fail_open(path, mode="r", *args, **kwargs):
        if path == target and mode == "xb":
            return FailedWriter()
        return original_open(path, mode, *args, **kwargs)

    def fail_stat(*_):
        raise OSError(errno.EPERM, "Synthetic metadata failure")

    monkeypatch.setattr(os, "link", unsupported_link)
    if failure == "metadata":
        monkeypatch.setattr("specsync.fs.shutil.copystat", fail_stat)
    else:
        monkeypatch.setattr(Path, "open", fail_open)
    with pytest.raises(OSError) as caught:
        write_file_atomic(target, "Planned\n", exclusive=True)
    assert caught.value.errno == (
        errno.EPERM if failure == "metadata" else errno.ENOSPC
    )
    if failure == "replacement":
        assert target.read_text() == "Another editor\n"
        assert list(tmp_path.iterdir()) == [target]
    else:
        assert not target.exists()
        assert list(tmp_path.iterdir()) == []
