import shutil

ANSI_COLORS = {
    'cyan': '\033[96m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'magenta': '\033[95m',
    'blue': '\033[94m',
    'red': '\033[91m',
    'white': '\033[97m',
    'grey': '\033[90m',
    'reset': '\033[0m',
}


def ansi_box(text, color='cyan', emoji='🤖', width=None):
    """
    Draw a fancy ANSI box around the given text, with color and emoji.
    """
    lines = [line.rstrip() for line in text.strip('\n').split('\n')]
    max_len = max(len(line) for line in lines)
    if width is None:
        try:
            width = min(shutil.get_terminal_size((80, 20)).columns, max_len + 6)
        except Exception:
            width = max_len + 6
    box_width = max(width, max_len + 6)
    color_code = ANSI_COLORS.get(color, ANSI_COLORS['cyan'])
    reset = ANSI_COLORS['reset']
    top = f"{color_code}╔{'═' * (box_width-2)}╗{reset}"
    title = f"{color_code}║ {emoji} {' ' * (box_width-6)}║{reset}"
    content = [f"{color_code}║ {line.ljust(box_width-4)} ║{reset}" for line in lines]
    bottom = f"{color_code}╚{'═' * (box_width-2)}╝{reset}"
    return '\n'.join([top, title] + content + [bottom])
