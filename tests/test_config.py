"""Tests for configuration management."""

import tempfile
from pathlib import Path

import pytest

from specsync.config import Config


def test_default_config():
    """Test default configuration values."""
    config = Config()
    
    assert config.include_patterns == ["**/*.md"]
    assert config.exclude_patterns == []
    assert config.frontmatter_filter == {}
    assert config.preserve_structure is True
    assert config.watch_debounce_seconds == 1.0


def test_config_with_parameters():
    """Test configuration with custom parameters."""
    config = Config(
        include_patterns=["*.md", "docs/**/*.md"],
        exclude_patterns=["**/draft-*.md"],
        frontmatter_filter={"published": True},
        preserve_structure=False,
        watch_debounce_seconds=2.0,
    )
    
    assert config.include_patterns == ["*.md", "docs/**/*.md"]
    assert config.exclude_patterns == ["**/draft-*.md"]
    assert config.frontmatter_filter == {"published": True}
    assert config.preserve_structure is False
    assert config.watch_debounce_seconds == 2.0


def test_config_save_load():
    """Test saving and loading configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "specsync.yaml"
        
        # Create and save config
        original_config = Config(
            include_patterns=["*.md"],
            exclude_patterns=["draft-*.md"],
            frontmatter_filter={"status": "published"},
        )
        original_config.save(config_path)
        
        # Load config
        loaded_config = Config.load(config_path)
        
        assert loaded_config.include_patterns == original_config.include_patterns
        assert loaded_config.exclude_patterns == original_config.exclude_patterns
        assert loaded_config.frontmatter_filter == original_config.frontmatter_filter


def test_should_include_file():
    """Test file inclusion logic."""
    config = Config(
        include_patterns=["**/*.md"],
        exclude_patterns=["**/draft-*.md"],
        frontmatter_filter={"published": True},
    )
    
    # Should include markdown files
    assert config.should_include_file(Path("test.md"))
    assert config.should_include_file(Path("docs/test.md"))
    
    # Should exclude draft files
    assert not config.should_include_file(Path("draft-test.md"))
    assert not config.should_include_file(Path("docs/draft-test.md"))
    
    # Should exclude non-markdown files
    assert not config.should_include_file(Path("test.txt"))
    
    # Test frontmatter filtering
    assert config.should_include_file(Path("test.md"), {"published": True})
    assert not config.should_include_file(Path("test.md"), {"published": False})
    assert not config.should_include_file(Path("test.md"), {})


def test_frontmatter_filter_types():
    """Test different frontmatter filter value types."""
    config = Config(frontmatter_filter={"tags": ["spec", "docs"]})
    
    # Should include if tag is in the list
    assert config.should_include_file(Path("test.md"), {"tags": "spec"})
    assert config.should_include_file(Path("test.md"), {"tags": "docs"})
    
    # Should exclude if tag is not in the list
    assert not config.should_include_file(Path("test.md"), {"tags": "other"})