"""Unit tests for swarm.utils.color_utils.color_text.

color_text is a small pure helper (color name -> ANSI-wrapped string) that had
no test coverage. These pin its mapping, case-insensitivity, and unknown-color
fallback without touching a terminal.
"""

import pytest
from colorama import Fore, Style

from swarm.utils.color_utils import color_text


@pytest.mark.parametrize(
    "name,code",
    [
        ("red", Fore.RED),
        ("green", Fore.GREEN),
        ("yellow", Fore.YELLOW),
        ("blue", Fore.BLUE),
        ("magenta", Fore.MAGENTA),
        ("cyan", Fore.CYAN),
        ("white", Fore.WHITE),
    ],
)
def test_color_text_maps_each_supported_color(name, code):
    assert color_text("hello", name) == f"{code}hello{Style.RESET_ALL}"


def test_color_text_is_case_insensitive():
    assert color_text("hi", "GREEN") == color_text("hi", "green")
    assert color_text("hi", "Green") == f"{Fore.GREEN}hi{Style.RESET_ALL}"


def test_color_text_unknown_color_falls_back_to_white():
    assert color_text("x", "chartreuse") == f"{Fore.WHITE}x{Style.RESET_ALL}"
    assert color_text("x", "") == f"{Fore.WHITE}x{Style.RESET_ALL}"


def test_color_text_always_resets_and_preserves_text():
    out = color_text("multi\nline text", "cyan")
    assert out.startswith(Fore.CYAN)
    assert out.endswith(Style.RESET_ALL)
    assert "multi\nline text" in out


def test_color_text_handles_empty_text():
    assert color_text("", "red") == f"{Fore.RED}{Style.RESET_ALL}"
