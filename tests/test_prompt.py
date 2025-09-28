"""Tests for interactive prompt handling."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from specsync.exceptions import InteractiveError
from specsync.prompt import PromptEngine


class TestPromptEngine:
    """Test the PromptEngine class."""

    def test_non_interactive_raises_error(self):
        """Test that non-interactive mode raises an error."""
        engine = PromptEngine(quiet=False)

        with patch.object(sys.stdin, 'isatty', return_value=False):
            with pytest.raises(InteractiveError) as exc_info:
                engine.confirm(Path("test.md"), Path("other.md"))
            assert "rerun with --force" in str(exc_info.value)

    def test_overwrite_all_state(self):
        """Test that 'all-overwrite' sets persistent state."""
        engine = PromptEngine(quiet=False)

        with patch.object(sys.stdin, 'isatty', return_value=True):
            with patch('builtins.input', return_value='A'):
                choice = engine.confirm(Path("test.md"), Path("other.md"))
                assert choice == "overwrite"
                assert engine.state.overwrite_all is True

            # Second call should return immediately
            choice = engine.confirm(Path("test2.md"), Path("other2.md"))
            assert choice == "overwrite"

    def test_skip_all_state(self):
        """Test that 'skip-all' sets persistent state."""
        engine = PromptEngine(quiet=False)

        with patch.object(sys.stdin, 'isatty', return_value=True):
            with patch('builtins.input', return_value='S'):
                choice = engine.confirm(Path("test.md"), Path("other.md"))
                assert choice == "skip"
                assert engine.state.skip_all is True

            # Second call should return immediately
            choice = engine.confirm(Path("test2.md"), Path("other2.md"))
            assert choice == "skip"

    def test_quit_option(self):
        """Test that 'quit' raises InteractiveError."""
        engine = PromptEngine(quiet=False)

        with patch.object(sys.stdin, 'isatty', return_value=True):
            with patch('builtins.input', return_value='q'):
                with pytest.raises(InteractiveError) as exc_info:
                    engine.confirm(Path("test.md"), Path("other.md"))
                assert "User quit" in str(exc_info.value)

    def test_diff_option(self):
        """Test that 'diff' returns the correct choice."""
        engine = PromptEngine(quiet=False)

        with patch.object(sys.stdin, 'isatty', return_value=True):
            with patch('builtins.input', return_value='d'):
                choice = engine.confirm(Path("test.md"), Path("other.md"))
                assert choice == "diff"

    def test_overwrite_option(self):
        """Test that 'o' returns overwrite."""
        engine = PromptEngine(quiet=False)

        with patch.object(sys.stdin, 'isatty', return_value=True):
            with patch('builtins.input', return_value='o'):
                choice = engine.confirm(Path("test.md"), Path("other.md"))
                assert choice == "overwrite"

    def test_skip_option(self):
        """Test that 's' returns skip."""
        engine = PromptEngine(quiet=False)

        with patch.object(sys.stdin, 'isatty', return_value=True):
            with patch('builtins.input', return_value='s'):
                choice = engine.confirm(Path("test.md"), Path("other.md"))
                assert choice == "skip"

    def test_invalid_input_reprompts(self):
        """Test that invalid input causes a reprompt."""
        engine = PromptEngine(quiet=False)

        with patch.object(sys.stdin, 'isatty', return_value=True):
            with patch('builtins.input', side_effect=['x', 'invalid', 'o']):
                with patch('specsync.prompt.info') as mock_info:
                    choice = engine.confirm(Path("test.md"), Path("other.md"))
                    assert choice == "overwrite"
                    # Should have prompted for invalid inputs
                    assert any("Please enter" in str(call) for call in mock_info.call_args_list)

    def test_shows_modification_times(self, tmp_path):
        """Test that modification times are displayed when available."""
        engine = PromptEngine(quiet=False)

        # Create actual files with known modification times
        source = tmp_path / "source.md"
        target = tmp_path / "target.md"
        source.write_text("source content")
        target.write_text("target content")

        with patch.object(sys.stdin, 'isatty', return_value=True):
            with patch('builtins.input', return_value='s'):
                with patch('specsync.prompt.info') as mock_info:
                    engine.confirm(source, target)

                    # Should show modification times in the prompt
                    info_calls = [call[0][0] for call in mock_info.call_args_list]
                    assert any("modified:" in call.lower() for call in info_calls)

    def test_eof_error_handling(self):
        """Test that EOFError is handled gracefully."""
        engine = PromptEngine(quiet=False)

        with patch.object(sys.stdin, 'isatty', return_value=True):
            with patch('builtins.input', side_effect=EOFError):
                with pytest.raises(InteractiveError) as exc_info:
                    engine.confirm(Path("test.md"), Path("other.md"))
                assert "No input available" in str(exc_info.value)

    def test_case_sensitivity(self):
        """Test that options are case-sensitive (capital letters for 'all' options)."""
        engine = PromptEngine(quiet=False)

        with patch.object(sys.stdin, 'isatty', return_value=True):
            # Lowercase 'a' should not trigger all-overwrite
            with patch('builtins.input', side_effect=['a', 'o']):
                with patch('specsync.prompt.info'):
                    choice = engine.confirm(Path("test.md"), Path("other.md"))
                    assert choice == "overwrite"
                    assert engine.state.overwrite_all is False