"""Exercise export failure and advisory failure propagation without network."""

from pathlib import Path
import runpy
import subprocess

import pytest

MODULE = runpy.run_path(
    str(Path(__file__).parents[1] / "scripts/audit_dependencies.py")
)


def test_failed_export_never_audits(monkeypatch):
    calls = []

    def fail_export(command, **kwargs):
        calls.append(command)
        assert kwargs["check"]
        raise subprocess.CalledProcessError(2, command)

    monkeypatch.setattr(subprocess, "run", fail_export)
    with pytest.raises(subprocess.CalledProcessError):
        MODULE["main"]()
    assert len(calls) == 1


@pytest.mark.parametrize("audit_result", [0, 1, 2])
def test_audit_result_propagates(monkeypatch, audit_result):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if command[1] == "export":
            assert "--frozen" in command and "--all-groups" in command
            assert "--no-emit-project" in command
            Path(command[-1]).write_text("requests==2.32.5\n")
            return subprocess.CompletedProcess(command, 0)
        assert command[1:3] == ["tool", "run"]
        assert MODULE["AUDITOR"] in command
        assert Path(command[-1]).read_text() == "requests==2.32.5\n"
        assert "--no-deps" in command and "--disable-pip" in command
        return subprocess.CompletedProcess(command, audit_result)

    monkeypatch.setattr(subprocess, "run", run)
    assert MODULE["main"]() == audit_result
    assert len(calls) == 2
