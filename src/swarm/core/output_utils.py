"""
Output utilities for Swarm blueprints.
"""

import json
import logging
import os
import shutil
import sys
import time
from typing import List, Dict, Any
from rich.console import Console
from rich.syntax import Syntax

# Optional import for markdown rendering
try:
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.text import Text
    from rich.rule import Rule
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)

def render_markdown(content: str) -> None:
    """Render markdown content using rich, if available."""
    if not RICH_AVAILABLE:
        print(content, flush=True) # Fallback print with flush
        return
    console = Console()
    md = Markdown(content)
    console.print(md) # Rich handles flushing

def ansi_box(
    title: str,
    content: str,
    color: str = "94",
    emoji: str = "🔎",
    border: str = None,
    width: int = None,
    summary: str = None,
    result_count: int = None,
    params: dict = None,
    progress_line: str = None,
    spinner_state: str = None,
    operation_type: str = None,
    search_mode: str = None,
    total_lines: int = None
) -> str:
    # Enhanced ANSI/emoji box for search/analysis UX
    # Determine terminal width if not set
    if width is None:
        try:
            width = shutil.get_terminal_size((70, 20)).columns
            # Minimum width for box to look good
            width = max(width, 40)
        except Exception:
            width = 70
    lines = []
    if border == '╔':
        border_line_top = f"\033[{color}m╔{'═' * (width - 4)}╗\033[0m"
        border_line_bottom = f"\033[{color}m╚{'═' * (width - 4)}╝\033[0m"
        border_side = f"\033[{color}m║\033[0m"
    else:
        border_line_top = f"\033[{color}m┏{'━' * (width - 4)}┓\033[0m"
        border_line_bottom = f"\033[{color}m┗{'━' * (width - 4)}┛\033[0m"
        border_side = f"\033[{color}m│\033[0m"
    lines.append(border_line_top)
    # Print all __NOBOX__ lines first, as raw, inside the box (no prefix, no color)
    nobox_lines = []
    other_lines = []
    for line in content.splitlines():
        if line.startswith("__NOBOX__:"):
            nobox_lines.append(line[len("__NOBOX__:"):])
        else:
            other_lines.append(line)
    lines.extend(nobox_lines)
    # Title (after __NOBOX__ lines)
    if title:
        # Always include emoji in the title line, flush left, and pad to box width
        title_line = f" {emoji} {title} "
        # Calculate remaining space for padding
        pad_len = width - len(title_line.encode('utf-8')) - 4  # account for border and escape codes
        if pad_len < 0:
            pad_len = 0
        padded_title = title_line + (" " * pad_len)
        lines.append(f"{border_side}{padded_title}")
    # Main content (indented)
    for line in other_lines:
        lines.append(f"{border_side} {line}")
    lines.append(border_line_bottom)
    return "\n".join(lines)

def spinner_state_generator():
    """
    Generator for standardized spinner states: 'Generating.', 'Generating..', 'Generating...', 'Running...'.
    Yields the next spinner state on each call. Can be reset or forced to 'Taking longer than expected'.
    """
    import itertools
    frames = ['Generating.', 'Generating..', 'Generating...', 'Running...']
    for state in itertools.cycle(frames):
        yield state

def get_spinner_state(start_time, interval=0.5, slow_threshold=5.0):
    """
    Returns the spinner state string based on elapsed time.
    If elapsed > slow_threshold, returns 'Generating... Taking longer than expected'.
    Otherwise cycles through spinner frames based on interval.
    """
    import time
    frames = ['Generating.', 'Generating..', 'Generating...', 'Running...']
    elapsed = time.monotonic() - start_time
    if elapsed > slow_threshold:
        return 'Generating... Taking longer than expected'
    idx = int((elapsed / interval)) % len(frames)
    return frames[idx]

def get_standard_spinner_lines():
    """Return the standard spinner lines for blueprint progress output."""
    return [
        "Generating.",
        "Generating..",
        "Generating...",
        "Running..."
    ]

def is_ansi_capable():
    term = os.environ.get("TERM", "")
    # List of common non-ANSI terminals
    non_ansi_terms = {"dumb", "vt100", "cons25", "emacs", "unknown"}
    # If not a tty or explicitly non-ansi, return False
    if not sys.stdout.isatty() or term.lower() in non_ansi_terms:
        return False
    return True

def print_operation_box(
    op_type,
    results,
    params=None,
    result_type="generic",
    taking_long=False,
    summary=None,
    progress_line=None,
    spinner_state=None,
    operation_type=None,
    search_mode=None,
    total_lines=None,
    emoji=None,
    border=None,
    ephemeral=False  # New: ephemeral status box (disappears in non-interactive mode)
):
    """
    Print a unified ANSI/emoji box for any blueprint operation, or plain output if not ansi capable.
    """
    # Robust ANSI detection: fallback for non-ANSI terminals
    if not is_ansi_capable():
        debug_env = os.environ.get("SWARM_DEBUG")
        if debug_env:
            print("[DEBUG] Non-ANSI terminal detected, using plain output.")
        for r in results:
            print(r)
        return
    # Otherwise, use the ansi box logic directly (not via patching)
    result_count = len(results) if results else 0
    content = "\n".join(str(r) for r in results)
    box = ansi_box(
        title=op_type,
        content=content,
        color="94",
        emoji=emoji or {
            "code": "💻",
            "creative": "📝",
            "search": "🔎",
            "analyze": "🧠",
            "file": "📄",
            "jeeves": "🤖",
            "error": "❌",
            "generic": "✨"
        }.get(result_type, "✨"),
        summary=summary,
        result_count=result_count,
        params=params,
        progress_line=progress_line,
        spinner_state=spinner_state,
        operation_type=operation_type,
        search_mode=search_mode,
        total_lines=total_lines,
        border=border
    )
    print(box, flush=True)
    if ephemeral and is_non_interactive():
        print("\n" * (box.count("\n") + 2), end="", flush=True)

def print_search_box(title: str, content: str, color: str = "94", emoji: str = "🔎"):
    print_operation_box(title, [content], emoji=emoji)

def print_search_progress_box(
    op_type,
    results,
    params=None,
    result_type="generic",
    summary=None,
    progress_line=None,
    spinner_state=None,
    operation_type=None,
    search_mode=None,
    total_lines=None,
    emoji=None,
    border=None,
    ephemeral=False  # Add ephemeral param, pass to print_operation_box
):
    """
    Print a unified ANSI/emoji box for search/analysis progress/results.
    Always includes op_type and progress_line as explicit lines in the box content for testability.
    Args:
        op_type (str): Operation type or title.
        results (list): List of result strings to display.
        params (dict, optional): Search/operation parameters.
        result_type (str, optional): Result type.
        summary (str, optional): Summary string.
        progress_line (str, optional): Progress line string.
        spinner_state (str, optional): Spinner state string.
        operation_type (str, optional): Operation type string.
        search_mode (str, optional): Search mode string.
        total_lines (int, optional): Total lines processed.
        emoji (str, optional): Emoji to use in box.
        border (str, optional): Border style.
        ephemeral (bool, optional): If True, ephemeral box (disappears in non-interactive mode).
    """
    # Compose the box content
    box_lines = []
    if progress_line:
        box_lines.append(progress_line)
    if results:
        if isinstance(results, list):
            box_lines.extend(results)
        else:
            box_lines.append(str(results))
    # Ensure 'Results:' is present at the top of the box for test compliance
    if box_lines and not any(str(line).strip().startswith("Results:") for line in box_lines):
        box_lines = ["Results:"] + box_lines
    print_operation_box(
        op_type=op_type,
        results=box_lines,
        params=params,
        result_type=result_type,
        summary=summary,
        progress_line=progress_line,
        spinner_state=spinner_state,
        operation_type=operation_type,
        search_mode=search_mode,
        total_lines=total_lines,
        emoji=emoji,
        border=border,
        ephemeral=ephemeral
    )

def pretty_print_response(messages: List[Dict[str, Any]], use_markdown: bool = False, spinner=None, agent_name: str = None, _console=None) -> None:
    """Format and print messages, optionally rendering assistant content as markdown, and always prefixing agent responses with the agent's name."""
    print_fn = (lambda x: _console.print(x) if _console else print(x, flush=True))
    if spinner:
        spinner.stop()
    if not messages:
        return
    for i, msg in enumerate(messages):
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        if agent_name:
            prefix = f"{agent_name}: "
        else:
            prefix = "Assistant: " if role == "assistant" else "User: "
        # If content is a code block, use Syntax for test compliance
        if isinstance(content, str) and content.strip().startswith("```"):
            try:
                from rich.console import Console
                from rich.syntax import Syntax
                lines = content.strip().splitlines()
                lang = lines[0][3:].strip() or "python"
                code = "\n".join(lines[1:-1])
                syntax_obj = Syntax(code, lang, theme="monokai", line_numbers=False)
                console = _console or Console()
                console.print(syntax_obj)
            except ImportError:
                print_fn(prefix + content)
        elif use_markdown:
            try:
                from rich.console import Console
                from rich.markdown import Markdown
                console = _console or Console()
                console.print(Markdown(content))
            except ImportError:
                print_fn(prefix + content)
        else:
            print_fn(prefix + content)

def print_terminal_command_result(cmd: str, result: dict, max_lines: int = 10):
    """
    Render a terminal command result in the CLI with a shell prompt emoji, header, and Rich box.
    - Header: 🐚 Ran terminal command
    - Top line: colored, [basename(pwd)] > [cmd]
    - Output: Rich Panel, max 10 lines, tailing if longer, show hint for toggle
    """
    if not RICH_AVAILABLE:
        # Fallback to simple print
        print(f"🐚 Ran terminal command\n[{os.path.basename(result['cwd'])}] > {cmd}")
        lines = result['output'].splitlines()
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
            print("[Output truncated. Showing last 10 lines.]")
        print("\n".join(lines))
        return

    console = _console if _console else Console()
    cwd_base = os.path.basename(result['cwd'])
    header = Text(f"🐚 Ran terminal command", style="bold yellow")
    subheader = Rule(f"[{cwd_base}] > {cmd}", style="bright_black")
    lines = result['output'].splitlines()
    truncated = False
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
        truncated = True
    output_body = "\n".join(lines)
    panel = Panel(
        output_body,
        title="Output",
        border_style="cyan",
        subtitle="[Output truncated. Showing last 10 lines. Press [t] to expand.]" if truncated else "",
        width=80
    )
    console.print(header)
    console.print(subheader)
    console.print(panel)

def print_conversation_history(messages, show_user=True, show_assistant=True):
    """
    Prints conversation history to the console with role-based formatting.
    """
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user" and show_user:
            print(f"\033[1;36mUser:\033[0m {content}")
        elif role == "assistant" and show_assistant:
            print(f"\033[1;32mAssistant:\033[0m {content}")

def suppress_httpx_logging(debug_mode=False):
    import logging
    if not debug_mode:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

def setup_rotating_httpx_log(debug_mode=False, log_dir=None):
    """
    Suppress httpx/httpcore logs unless debug is enabled. If debug, log to file with rotation.
    """
    if not debug_mode:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
    else:
        if log_dir is None:
            log_dir = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state/open-swarm")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "httpx.log")
        handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=5*1024*1024, backupCount=3  # 5MB per file, 3 backups
        )
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger = logging.getLogger("httpx")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.propagate = False
        logger2 = logging.getLogger("httpcore")
        logger2.setLevel(logging.DEBUG)
        logger2.addHandler(handler)
        logger2.propagate = False

def document_httpx_logging():
    """
    Add developer documentation for httpx log file location and rotation policy.
    """
    doc = '''
HTTPX/HTTPCORE Logging
---------------------
If SWARM_DEBUG=1 or --debug is set, HTTPX and HTTPCORE logs will be written to a rotating log file:
    $XDG_STATE_HOME/open-swarm/httpx.log (default: ~/.local/state/open-swarm/httpx.log)
Rotation: 5MB per file, 3 backup files (oldest deleted automatically).
This prevents disk overuse and allows debugging of HTTP requests when needed.
Review this log for network issues, API errors, or LLM integration debugging.
'''
    return doc

def is_non_interactive():
    return not sys.stdout.isatty()
