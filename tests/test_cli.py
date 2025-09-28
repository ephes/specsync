"""Tests for CLI interface."""

import tempfile
from pathlib import Path

from click.testing import CliRunner

from specsync.cli import cli


def test_cli_help():
    """Test CLI help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    
    assert result.exit_code == 0
    assert "SpecSync" in result.output
    assert "Selective Markdown sync" in result.output


def test_init_command():
    """Test init command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        runner = CliRunner()
        result = runner.invoke(cli, ["init"], cwd=temp_dir)
        
        assert result.exit_code == 0
        assert "Created configuration file" in result.output
        
        config_path = Path(temp_dir) / "specsync.yaml"
        assert config_path.exists()


def test_sync_dry_run():
    """Test sync command with dry run."""
    with tempfile.TemporaryDirectory() as temp_dir:
        specs_dir = Path(temp_dir) / "specs"
        workspace_dir = Path(temp_dir) / "workspace"
        
        # Create a test markdown file
        specs_dir.mkdir()
        test_file = specs_dir / "test.md"
        test_file.write_text("# Test\n\nThis is a test.")
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "sync",
            str(workspace_dir),
            "--specs-dir", str(specs_dir),
            "--dry-run"
        ])
        
        assert result.exit_code == 0
        assert "Dry run mode" in result.output
        assert "Would sync: test.md" in result.output or "Would sync:" in result.output