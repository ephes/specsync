"""Audit the frozen all-group export; never resolve or repair the project lock."""

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AUDITOR = "pip-audit==2.10.1"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="specsync-audit-") as directory:
        requirements = Path(directory) / "requirements.txt"
        subprocess.run(
            [
                "uv",
                "export",
                "--frozen",
                "--all-groups",
                "--no-emit-project",
                "--no-hashes",
                "--output-file",
                str(requirements),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        return subprocess.run(
            [
                "uv",
                "tool",
                "run",
                "--python",
                sys.executable,
                "--from",
                AUDITOR,
                "pip-audit",
                "--no-deps",
                "--disable-pip",
                "--requirement",
                str(requirements),
            ],
            cwd=ROOT,
            check=False,
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
