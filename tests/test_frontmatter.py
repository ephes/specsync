from pathlib import Path
from textwrap import dedent

import pytest

from specsync.frontmatter import FrontmatterResult, parse_frontmatter, render_frontmatter
from specsync.exceptions import FrontmatterError


def test_parse_frontmatter_success():
    text = "---\nexpose: true\nproject: demo\n---\n\n# Title\n"
    result = parse_frontmatter(text, path=Path("doc.md"))
    assert isinstance(result, FrontmatterResult)
    assert result.frontmatter == {"expose": True, "project": "demo"}
    assert result.body == "# Title\n"
    assert result.had_frontmatter is True


def test_parse_without_frontmatter():
    text = "# Just content\n"
    result = parse_frontmatter(text, path=Path("doc.md"))
    assert result.frontmatter is None
    assert result.body == text
    assert result.had_frontmatter is False


def test_render_frontmatter_roundtrip():
    data = {"expose": True, "project": "demo"}
    rendered = render_frontmatter(data)
    assert rendered.startswith("---\n")
    parsed = parse_frontmatter(rendered + "Body", path=Path("doc.md"))
    assert parsed.frontmatter == data


def test_invalid_yaml_raises():
    text = "---\n: bad\n---\n"
    with pytest.raises(FrontmatterError):
        parse_frontmatter(text, path=Path("doc.md"))


def test_empty_frontmatter_block():
    """Test that empty frontmatter blocks are handled correctly."""
    text = "---\n---\n# Content"
    result = parse_frontmatter(text, path=Path("doc.md"))
    assert result.frontmatter == {}
    assert result.body == "# Content"
    assert result.had_frontmatter is True


def test_multiple_frontmatter_blocks():
    """Test that only the first block is treated as frontmatter."""
    text = "---\nfirst: true\n---\n\nSome content\n\n---\nsecond: true\n---\n"
    result = parse_frontmatter(text, path=Path("doc.md"))
    assert result.frontmatter == {"first": True}
    assert "---\nsecond: true\n---" in result.body
    assert result.had_frontmatter is True


def test_windows_line_endings():
    """Test that Windows line endings are normalized."""
    text = "---\r\nexpose: true\r\n---\r\n\r\n# Title\r\n"
    result = parse_frontmatter(text, path=Path("doc.md"))
    assert result.frontmatter == {"expose": True}
    assert result.body == "# Title\n"  # Should be normalized to Unix endings


def test_no_closing_delimiter():
    """Test that missing closing delimiter means no frontmatter."""
    text = "---\nexpose: true\n# No closing delimiter"
    result = parse_frontmatter(text, path=Path("doc.md"))
    assert result.frontmatter is None
    assert result.body == text
    assert result.had_frontmatter is False


def test_frontmatter_at_eof():
    """Test frontmatter block ending at EOF without newline."""
    text = "---\nexpose: true\n---"
    result = parse_frontmatter(text, path=Path("doc.md"))
    assert result.frontmatter == {"expose": True}
    assert result.body == ""
    assert result.had_frontmatter is True


def test_frontmatter_literal_with_horizontal_rule():
    """Frontmatter should allow literal blocks containing --- lines."""
    text = dedent(
        """\
        ---
        description: |
          Intro
          ---
          Outro
        ---
        Body
        """
    )
    result = parse_frontmatter(text, path=Path("doc.md"))
    assert result.frontmatter == {"description": "Intro\n---\nOutro\n"}
    assert result.body == "Body\n"
    assert result.had_frontmatter is True
