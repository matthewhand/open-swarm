"""
Unit tests for ansi_box.py module
"""
import pytest
from unittest.mock import patch
from src.swarm.ux.ansi_box import ansi_box


class TestAnsiBox:
    """Test suite for ansi_box function."""

    def test_ansi_box_basic(self):
        """Test basic ansi_box with minimal parameters."""
        with patch('builtins.print') as mock_print:
            ansi_box("Test Title", "Test Content")
            
            # Should be called once with the box output
            assert mock_print.call_count == 1
            output = mock_print.call_args[0][0]
            assert "Test Title" in output
            assert "Test Content" in output

    def test_ansi_box_with_count(self):
        """Test ansi_box with count parameter."""
        with patch('builtins.print') as mock_print:
            ansi_box("Test Title", "Content", count=5)
            
            output = mock_print.call_args[0][0]
            assert "Results: 5" in output

    def test_ansi_box_with_params(self):
        """Test ansi_box with params parameter."""
        with patch('builtins.print') as mock_print:
            params = {"key1": "value1", "key2": "value2"}
            ansi_box("Test Title", "Content", params=params)
            
            output = mock_print.call_args[0][0]
            assert "Params:" in output
            assert "key1" in output
            assert "value1" in output

    def test_ansi_box_with_emoji(self):
        """Test ansi_box with emoji parameter."""
        with patch('builtins.print') as mock_print:
            ansi_box("Test Title", "Content", emoji="🎯")
            
            output = mock_print.call_args[0][0]
            assert "🎯" in output

    def test_ansi_box_with_style(self):
        """Test ansi_box with different styles."""
        styles = ['default', 'success', 'warning', 'unknown']
        
        for style in styles:
            with patch('builtins.print') as mock_print:
                ansi_box("Test Title", "Content", style=style)
                
                output = mock_print.call_args[0][0]
                assert "Test Title" in output
                assert "Content" in output

    def test_ansi_box_with_list_content(self):
        """Test ansi_box with list content."""
        content = ["Line 1", "Line 2", "Line 3"]
        
        with patch('builtins.print') as mock_print:
            ansi_box("Test Title", content)
            
            output = mock_print.call_args[0][0]
            assert "Line 1" in output
            assert "Line 2" in output
            assert "Line 3" in output

    def test_ansi_box_with_multiline_content(self):
        """Test ansi_box with multiline string content."""
        content = "Line 1\nLine 2\nLine 3"
        
        with patch('builtins.print') as mock_print:
            ansi_box("Test Title", content)
            
            output = mock_print.call_args[0][0]
            assert "Line 1" in output
            assert "Line 2" in output
            assert "Line 3" in output

    def test_ansi_box_truncates_long_lines(self):
        """Test that ansi_box truncates lines longer than box_width."""
        long_title = "A" * 100
        long_content = "B" * 100
        
        with patch('builtins.print') as mock_print:
            ansi_box(long_title, long_content)
            
            output = mock_print.call_args[0][0]
            lines = output.split('\n')
            
            # Check that no line exceeds box width (80 chars)
            for line in lines:
                # Remove ANSI color codes for length check
                clean_line = line.replace('\033[36m', '').replace('\033[0m', '')
                assert len(clean_line) <= 80

    def test_ansi_box_includes_ansi_colors(self):
        """Test that ansi_box output includes ANSI color codes."""
        with patch('builtins.print') as mock_print:
            ansi_box("Test Title", "Content", style='success')
            
            output = mock_print.call_args[0][0]
            # Should have ANSI color codes
            assert '\033[' in output
            assert '\033[0m' in output  # Reset code

    def test_ansi_box_default_style_uses_cyan(self):
        """Test that default style uses cyan color."""
        with patch('builtins.print') as mock_print:
            ansi_box("Test Title", "Content", style='default')
            
            output = mock_print.call_args[0][0]
            assert '\033[36m' in output  # Cyan color code

    def test_ansi_box_success_style_uses_green(self):
        """Test that success style uses green color."""
        with patch('builtins.print') as mock_print:
            ansi_box("Test Title", "Content", style='success')
            
            output = mock_print.call_args[0][0]
            assert '\033[32m' in output  # Green color code

    def test_ansi_box_warning_style_uses_yellow(self):
        """Test that warning style uses yellow color."""
        with patch('builtins.print') as mock_print:
            ansi_box("Test Title", "Content", style='warning')
            
            output = mock_print.call_args[0][0]
            assert '\033[33m' in output  # Yellow color code
