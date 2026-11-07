"""Build and smoke-test wheel and sdist installations away from the checkout."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def tree_state(root: Path) -> dict[str, bytes | None]:
    """Include directories so dry-run mkdirs are detected too."""
    return {
        path.relative_to(root).as_posix(): None if path.is_dir() else path.read_bytes()
        for path in root.rglob("*")
    }


def smoke_artifact(artifact: Path, directory: Path, version: str) -> None:
    directory.mkdir()
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SPECSYNC_")
        and key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}
    }

    def run(*command: str) -> str:
        result = subprocess.run(
            command,
            cwd=directory,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode:
            raise RuntimeError(
                f"{command!r} failed ({result.returncode}):\n{result.stdout}"
            )
        return result.stdout

    environment = directory / "venv"
    run("uv", "venv", "--python", sys.executable, str(environment))
    bin_dir = environment / ("Scripts" if os.name == "nt" else "bin")
    python = bin_dir / ("python.exe" if os.name == "nt" else "python")
    executable = bin_dir / ("specsync.exe" if os.name == "nt" else "specsync")
    run("uv", "pip", "install", "--python", str(python), str(artifact))
    run(
        str(python),
        "-I",
        "-c",
        "import pathlib, sys, specsync; "
        "assert pathlib.Path(specsync.__file__).resolve().is_relative_to("
        "pathlib.Path(sys.prefix).resolve()), specsync.__file__",
    )
    if "usage:" not in run(str(executable), "--help"):
        raise AssertionError("Installed help did not print usage")
    if run(str(executable), "--version").strip() != f"specsync {version}":
        raise AssertionError("Installed CLI version differs from package metadata")

    for direction in ("pull", "push"):
        fixture = directory / direction
        repo = fixture / "repo"
        workspace = fixture / "workspace"
        repo.mkdir(parents=True)
        workspace.mkdir()
        (repo / ".git").mkdir()
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "smoke"\n', encoding="utf-8"
        )
        source = (workspace if direction == "pull" else repo) / "specs"
        source.mkdir()
        (source / "note.md").write_text(
            "---\nexpose: true\nproject: smoke\n---\n\nSynthetic smoke\n",
            encoding="utf-8",
        )
        before = tree_state(fixture)
        result = subprocess.run(
            [
                str(executable),
                direction,
                "--workspace-root",
                str(workspace),
                "--dry-run",
            ],
            cwd=repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode or "CREATE | note.md" not in result.stdout:
            raise AssertionError(
                f"Installed {direction} dry-run failed:\n{result.stdout}"
            )
        if tree_state(fixture) != before:
            raise AssertionError(
                f"Installed {direction} dry-run changed fixture files/directories"
            )
    print(
        f"Installed {artifact.name}: imports, help, version, pull/push dry-run passed"
    )


def main() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    with tempfile.TemporaryDirectory(prefix="specsync-distributions-") as temporary:
        directory = Path(temporary)
        artifacts = directory / "artifacts"
        subprocess.run(
            ["uv", "build", "--no-sources", "--out-dir", str(artifacts)],
            cwd=ROOT,
            check=True,
        )
        for label, pattern in (("wheel", "*.whl"), ("sdist", "*.tar.gz")):
            matches = list(artifacts.glob(pattern))
            if len(matches) != 1:
                raise AssertionError(f"Expected one {label}, got {matches}")
            smoke_artifact(matches[0], directory / label, version)


if __name__ == "__main__":
    main()
