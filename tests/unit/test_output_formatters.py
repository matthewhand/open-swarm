"""
Unit tests for output_formatters.py module
"""
import pytest
from src.swarm.blueprints.common.output_formatters import DiffFormatter, StatusFormatter


class TestDiffFormatter:
    """Test suite for DiffFormatter class."""

    def test_format_diff_lines_empty(self):
        """Test formatting empty list of lines."""
        result = DiffFormatter.format_diff_lines([])
        assert result == []

    def test_format_diff_lines_added(self):
        """Test formatting lines starting with '+' (added)."""
        lines = ["+ This is an added line", "+ Another addition"]
        result = DiffFormatter.format_diff_lines(lines)
        assert len(result) == 2
        assert "\033[32m" in result[0]  # Green color
        assert "\033[0m" in result[0]  # Reset
        assert "This is an added line" in result[0]

    def test_format_diff_lines_removed(self):
        """Test formatting lines starting with '-' (removed)."""
        lines = ["- This is a removed line", "- Another removal"]
        result = DiffFormatter.format_diff_lines(lines)
        assert len(result) == 2
        assert "\033[31m" in result[0]  # Red color
        assert "\033[0m" in result[0]  # Reset
        assert "This is a removed line" in result[0]

    def test_format_diff_lines_unchanged(self):
        """Test formatting lines that don't start with + or -."""
        lines = ["  This is unchanged", "  Another unchanged line"]
        result = DiffFormatter.format_diff_lines(lines)
        assert len(result) == 2
        assert "\033[" not in result[0]  # No color codes
        assert "This is unchanged" in result[0]

    def test_format_diff_lines_mixed(self):
        """Test formatting mixed diff lines."""
        lines = [
            "+ Added line",
            "- Removed line",
            "  Unchanged line",
            "+ Another added"
        ]
        result = DiffFormatter.format_diff_lines(lines)
        assert len(result) == 4
        assert "\033[32m" in result[0]  # Green
        assert "\033[31m" in result[1]  # Red
        assert "\033[" not in result[2]  # No color
        assert "\033[32m" in result[3]  # Green


class TestStatusFormatter:
    """Test suite for StatusFormatter class."""

    def test_format_status_line_basic(self):
        """Test basic status line formatting."""
        result = StatusFormatter.format_status_line("Test message", 5, 100)
        assert "Test message" in result
        assert "5s waited" in result
        assert "100 tokens" in result

    def test_format_status_line_colors(self):
        """Test that status line has correct ANSI colors."""
        result = StatusFormatter.format_status_line("Test", 1, 50)
        # Should have color codes for message and timing/tokens
        assert "\033[38;5;183m" in result  # Message color
        assert "\033[38;5;240m" in result  # Timing/tokens color
        assert result.count("\033[0m") == 2  # Two resets

    def test_format_status_line_zero_values(self):
        """Test status line with zero elapsed time and tokens."""
        result = StatusFormatter.format_status_line("Instant", 0, 0)
        assert "Instant" in result
        assert "0s waited" in result
        assert "0 tokens" in result

    def test_format_status_line_long_message(self):
        """Test status line with long message."""
        long_message = "This is a very long status message " * 5
        result = StatusFormatter.format_status_line(long_message, 10, 500)
        assert long_message in result
        assert "10s waited" in result
        assert "500 tokens" in result
