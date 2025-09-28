"""Tests for filesystem utilities."""


import pytest

from specsync.fs import (
    ensure_dir,
    is_within,
    validate_path_security,
    iter_markdown_files,
    append_gitignore,
    write_file_atomic,
    hash_file,
)
from specsync.exceptions import SecurityError


class TestPathSecurity:
    """Test path security validation."""

    def test_validate_path_within_root(self, tmp_path):
        """Test that paths within root are allowed."""
        root = tmp_path / "root"
        root.mkdir()
        target = root / "subdir" / "file.md"

        # Should not raise
        validate_path_security(target, root)

    def test_validate_path_traversal_blocked(self, tmp_path):
        """Test that path traversal attempts are blocked."""
        root = tmp_path / "root"
        root.mkdir()
        target = root / ".." / "outside" / "file.md"

        with pytest.raises(SecurityError) as exc_info:
            validate_path_security(target, root)
        assert "outside allowed root" in str(exc_info.value)

    def test_validate_absolute_path_outside_root(self, tmp_path):
        """Test that absolute paths outside root are blocked."""
        root = tmp_path / "root"
        root.mkdir()
        target = tmp_path / "other" / "file.md"

        with pytest.raises(SecurityError) as exc_info:
            validate_path_security(target, root)
        assert "outside allowed root" in str(exc_info.value)

    def test_validate_symlink_escaping_root(self, tmp_path):
        """Test that symlinks escaping root are blocked."""
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        outside_file = outside / "secret.md"
        outside_file.write_text("secret")

        # Create symlink pointing outside
        link = root / "link.md"
        link.symlink_to(outside_file)

        with pytest.raises(SecurityError) as exc_info:
            validate_path_security(link, root, follow_symlinks=False)
        assert "Symlink not allowed" in str(exc_info.value)

    def test_validate_symlink_within_root_allowed(self, tmp_path):
        """Test that symlinks within root are allowed when configured."""
        root = tmp_path / "root"
        root.mkdir()
        target_file = root / "target.md"
        target_file.write_text("content")

        link = root / "link.md"
        link.symlink_to(target_file)

        # Should not raise when symlinks are allowed and point within root
        validate_path_security(link, root, follow_symlinks=True)

    def test_is_within_basic(self, tmp_path):
        """Test basic is_within functionality."""
        root = tmp_path / "root"
        root.mkdir()

        assert is_within(root, root / "file.md")
        assert is_within(root, root / "sub" / "file.md")
        assert not is_within(root, tmp_path / "other" / "file.md")
        assert not is_within(root, root / ".." / "file.md")


class TestFileOperations:
    """Test file operation utilities."""

    def test_ensure_dir_creates_nested(self, tmp_path):
        """Test that ensure_dir creates nested directories."""
        target = tmp_path / "a" / "b" / "c"
        ensure_dir(target)
        assert target.exists()
        assert target.is_dir()

    def test_ensure_dir_idempotent(self, tmp_path):
        """Test that ensure_dir is idempotent."""
        target = tmp_path / "dir"
        ensure_dir(target)
        ensure_dir(target)  # Should not raise
        assert target.exists()

    def test_write_file_atomic(self, tmp_path):
        """Test atomic file writing."""
        target = tmp_path / "file.txt"
        content = "test content\n"

        write_file_atomic(target, content)

        assert target.exists()
        assert target.read_text() == content

        # No temp files should remain
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_hash_file_consistency(self, tmp_path):
        """Test that file hashing is consistent."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        content = "same content\n"

        file1.write_text(content)
        file2.write_text(content)

        hash1 = hash_file(file1)
        hash2 = hash_file(file2)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_hash_file_different_content(self, tmp_path):
        """Test that different content produces different hashes."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("content 1")
        file2.write_text("content 2")

        assert hash_file(file1) != hash_file(file2)


class TestGitignore:
    """Test gitignore manipulation."""

    def test_append_gitignore_new_file(self, tmp_path):
        """Test appending to non-existent gitignore."""
        repo = tmp_path / "repo"
        repo.mkdir()

        append_gitignore(repo, "specs/", comment="Added by specsync")

        gitignore = repo / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "# Added by specsync" in content
        assert "specs/" in content

    def test_append_gitignore_existing_file(self, tmp_path):
        """Test appending to existing gitignore."""
        repo = tmp_path / "repo"
        repo.mkdir()
        gitignore = repo / ".gitignore"
        gitignore.write_text("*.pyc\n*.pyo\n")

        append_gitignore(repo, "specs/", comment="Added by specsync")

        content = gitignore.read_text()
        assert "*.pyc" in content
        assert "# Added by specsync" in content
        assert "specs/" in content

    def test_append_gitignore_idempotent(self, tmp_path):
        """Test that append_gitignore is idempotent."""
        repo = tmp_path / "repo"
        repo.mkdir()

        append_gitignore(repo, "specs/", comment="Added by specsync")
        append_gitignore(repo, "specs/", comment="Added by specsync")

        content = (repo / ".gitignore").read_text()
        # Should only appear once
        assert content.count("specs/") == 1
        assert content.count("# Added by specsync") == 1

    def test_append_gitignore_pattern_variations(self, tmp_path):
        """Test that pattern variations are detected."""
        repo = tmp_path / "repo"
        repo.mkdir()
        gitignore = repo / ".gitignore"
        gitignore.write_text("/specs/\n")

        append_gitignore(repo, "specs/")

        content = gitignore.read_text()
        # Should not add duplicate even with slight variation
        assert content.count("specs") == 1


class TestMarkdownFiles:
    """Test markdown file iteration."""

    def test_iter_markdown_files(self, tmp_path):
        """Test finding markdown files recursively."""
        root = tmp_path / "root"
        root.mkdir()

        # Create some markdown files
        (root / "file1.md").write_text("content")
        (root / "sub").mkdir()
        (root / "sub" / "file2.md").write_text("content")

        # Create non-markdown files
        (root / "other.txt").write_text("content")
        (root / "README").write_text("content")

        # Create hidden directory (should be skipped)
        (root / ".hidden").mkdir()
        (root / ".hidden" / "hidden.md").write_text("content")

        files = list(iter_markdown_files(root))
        paths = [f.name for f in files]

        assert "file1.md" in paths
        assert "file2.md" in paths
        assert "other.txt" not in paths
        assert "hidden.md" not in paths  # Hidden directories should be skipped