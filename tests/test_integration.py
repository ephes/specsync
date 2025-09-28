"""Integration tests for specsync."""



from specsync.cli import main


class TestCLIIntegration:
    """Test CLI integration."""

    def test_info_command(self, tmp_path, monkeypatch):
        """Test the info command."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "pyproject.toml").write_text('[project]\nname = "test-project"\n')

        monkeypatch.chdir(repo)
        monkeypatch.setenv("SPECSYNC_WORKSPACE_ROOT", str(tmp_path / "workspace"))

        result = main(["info"])
        assert result == 0

    def test_init_command(self, tmp_path, monkeypatch):
        """Test the init command."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "pyproject.toml").write_text('[project]\nname = "test-project"\n')

        monkeypatch.chdir(repo)

        result = main(["init"])
        assert result == 0

        # Check that specs dir was created
        assert (repo / "specs").exists()

        # Check that .gitignore was updated
        gitignore = repo / ".gitignore"
        assert gitignore.exists()
        assert "specs" in gitignore.read_text()

        # Check that pyproject.toml was updated
        pyproject = repo / "pyproject.toml"
        content = pyproject.read_text()
        assert "[tool.specsync]" in content

    def test_pull_dry_run(self, tmp_path, monkeypatch):
        """Test pull with dry-run."""
        # Setup repo
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "specs").mkdir()
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "test-project"\n\n[tool.specsync]\nworkspace_subdir = "specs"\n'
        )

        # Setup workspace
        workspace = tmp_path / "workspace" / "specs"
        workspace.mkdir(parents=True)
        spec = workspace / "test.md"
        spec.write_text("---\nexpose: true\nproject: test-project\n---\n\n# Test Spec")

        monkeypatch.chdir(repo)
        monkeypatch.setenv("SPECSYNC_WORKSPACE_ROOT", str(tmp_path / "workspace"))

        result = main(["pull", "--dry-run"])
        assert result == 0

    def test_push_dry_run(self, tmp_path, monkeypatch):
        """Test push with dry-run."""
        # Setup repo
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        specs_dir = repo / "specs"
        specs_dir.mkdir()
        spec = specs_dir / "test.md"
        spec.write_text("# Test Spec\nContent without frontmatter")

        (repo / "pyproject.toml").write_text(
            '[project]\nname = "test-project"\n\n[tool.specsync]\nworkspace_subdir = "specs"\n'
        )

        # Setup workspace
        workspace = tmp_path / "workspace" / "specs"
        workspace.mkdir(parents=True)

        monkeypatch.chdir(repo)
        monkeypatch.setenv("SPECSYNC_WORKSPACE_ROOT", str(tmp_path / "workspace"))

        result = main(["push", "--dry-run"])
        assert result == 0