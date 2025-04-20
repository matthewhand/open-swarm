import sys

def ansi_box(title, content, count=None, params=None, style='default', emoji=None):
    """
    Print a visually distinct ANSI box summarizing search/analysis results.
    - title: e.g. 'Searched filesystem', 'Analyzed code'
    - content: main result string or list of strings
    - count: result count (optional)
    - params: dict of search parameters (optional)
    - style: 'default', 'success', 'warning', etc.
    - emoji: optional emoji prefix
    """
    border = {
        'default': '━',
        'success': '━',
        'warning': '━',
    }.get(style, '━')
    color = {
        'default': '\033[36m',  # Cyan
        'success': '\033[32m',  # Green
        'warning': '\033[33m',  # Yellow
    }.get(style, '\033[36m')
    reset = '\033[0m'
    box_width = 80
    lines = []
    head = f"{emoji + ' ' if emoji else ''}{title}"
    if count is not None:
        head += f" | Results: {count}"
    if params:
        head += f" | Params: {params}"
    lines.append(color + border * box_width + reset)
    lines.append(color + f"{head[:box_width]:^{box_width}}" + reset)
    lines.append(color + border * box_width + reset)
    if isinstance(content, str):
        content = [content]
    for line in content:
        for l in str(line).split('\n'):
            lines.append(f"{l[:box_width]:<{box_width}}")
    lines.append(color + border * box_width + reset)
    print("\n".join(lines))

# Example usage:
# ansi_box('Searched filesystem', 'Found 12 files', count=12, params={'pattern': '*.py'}, style='success', emoji='💾')
