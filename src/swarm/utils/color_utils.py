# src/swarm/utils/color_utils.py

from colorama import Fore, Style
from colorama import init as colorama_init


def initialize_colorama():
    """
    Initialize colorama for colored terminal outputs.

    This function should be called at the start of your application to ensure
    that ANSI color codes are interpreted correctly across different platforms.
    """
    colorama_init(autoreset=True)

def color_text(text: str, color: str) -> str:
    """
    Return the text string wrapped in the specified color codes.

    Args:
        text (str): The text to color.
        color (str): The color name. Supported colors: red, green, yellow, blue, magenta, cyan, white.

    Returns:
        str: Colored text string.

    Example:
        >>> print(color_text("Hello, World!", "green"))
        Hello, World!  # (in green color)
    """
    color_mapping = {
        "red": Fore.RED,
        "green": Fore.GREEN,
        "yellow": Fore.YELLOW,
        "blue": Fore.BLUE,
        "magenta": Fore.MAGENTA,
        "cyan": Fore.CYAN,
        "white": Fore.WHITE,
    }

    color_code = color_mapping.get(color.lower(), Fore.WHITE)
    return f"{color_code}{text}{Style.RESET_ALL}"
