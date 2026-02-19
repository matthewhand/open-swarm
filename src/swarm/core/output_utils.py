"""
Output utilities for Swarm blueprints.
"""

import json
import logging
import os
import sys
import time
from typing import Any

# Optional import for markdown rendering
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import display_operation_box for compatibility
try:
    from swarm.blueprints.common.operation_box_utils import display_operation_box
except ImportError:
    display_operation_box = None

# Define JeevesSpinner for test compatibility
class JeevesSpinner:
    SPINNER_STATES = ["Polishing the silver", "Generating.", "Generating..", "Generating...", "Running..."]
    LONG_WAIT_MSG = "Generating... Taking longer than expected"
    SLOW_THRESHOLD = 10

    def __init__(self):
        self._idx = 0
        self._start_time = None
        self._last_frame = self.SPINNER_STATES[0]
        self._running = False

    def start(self):
        self._start_time = time.time()
        self._idx = 0
        self._last_frame = self.SPINNER_STATES[0]
        self._running = True

    def _spin(self):
        self._idx = (self._idx + 1) % len(self.SPINNER_STATES)
        self._last_frame = self.SPINNER_STATES[self._idx]

    @property
    def _current_frame(self):
        return self._idx

    @_current_frame.setter
    def _current_frame(self, value):
        self._idx = value % len(self.SPINNER_STATES)
        self._last_frame = self.SPINNER_STATES[self._idx]

    def current_spinner_state(self):
        if self._start_time and (time.time() - self._start_time) > self.SLOW_THRESHOLD:
            return self.LONG_WAIT_MSG
        return self._last_frame

    def stop(self):
        """Stop the spinner (no-op)."""
        self._running = False

logger = logging.getLogger(__name__)

def render_markdown(content: str) -> None:
    """Render markdown content using rich, if available."""
    if not RICH_AVAILABLE:
        print(content, flush=True)
        return
    console = Console()
    md = Markdown(content)
    console.print(md)

def ansi_box(title: str, content: str, color: str = "94", emoji: str = "🔎", border: str = "─", width: int = 70) -> str:
    """Return a string or Panel with ANSI box formatting for search/analysis results using Rich if available."""
    if RICH_AVAILABLE:
        console = Console()
        # Rich supports color names or hex, map color code to name
        color_map = {
            "94": "bright_blue",
            "96": "bright_cyan",
            "92": "bright_green",
            "93": "bright_yellow",
            "91": "bright_red",
            "95": "bright_magenta",
            "90": "grey82",
        }
        style = color_map.get(color, "bright_blue")
        panel = Panel(
            content,
            title=f"{emoji} {title} {emoji}",
            border_style=style,
            width=width
        )
        # Return the rendered panel as a string for testability
        with console.capture() as capture:
            console.print(panel)
        return capture.get()
    # Fallback: legacy manual ANSI box
    top = f"\033[{color}m{emoji} {border * (width - 4)} {emoji}\033[0m"
    mid_title = f"\033[{color}m│ {title.center(width - 6)} │\033[0m"
    lines = content.splitlines()
    boxed = [top, mid_title, top]
    for line in lines:
        boxed.append(f"\033[{color}m│\033[0m {line.ljust(width - 6)} \033[{color}m│\033[0m")
    boxed.append(top)
    return "\n".join(boxed)

def print_search_box(title: str, content: str, color: str = "94", emoji: str = "🔎"):
    print(ansi_box(title, content, color=color, emoji=emoji))

def print_search_progress_box(*args, **kwargs):
    """
    Backwards-compatible search/progress box renderer.
    Supports both the legacy (title, content) signature and the structured
    kwargs used across blueprints (results, params, progress_line, etc.).
    """
    simple_keys = {"color", "emoji"}
    if len(args) >= 2 and all(k in simple_keys for k in kwargs):
        title = args[0]
        content = args[1]
        color = kwargs.get("color", "94")
        emoji = kwargs.get("emoji", "🔎")
        return print_search_box(title, content, color=color, emoji=emoji)

    title = kwargs.get("operation_type") or kwargs.get("op_type") or (args[0] if args else "Search")
    results = kwargs.get("results")
    if results is None and len(args) >= 2:
        content = str(args[1])
    elif isinstance(results, list):
        content = "\n".join(str(r) for r in results)
    elif results is None:
        content = ""
    else:
        content = str(results)

    summary = kwargs.get("summary")
    if summary and summary not in content:
        content = f"{content}\n{summary}" if content else summary

    params = kwargs.get("params")
    if not isinstance(params, dict):
        params = None

    progress_line = kwargs.get("progress_line")
    total_lines = kwargs.get("total_lines")
    spinner_state = kwargs.get("spinner_state")
    emoji = kwargs.get("emoji", "🔎")

    style_op_type = kwargs.get("op_type")
    search_mode = kwargs.get("search_mode")
    if search_mode == "semantic":
        style_op_type = "semantic_search"
    elif search_mode == "code":
        style_op_type = "code_search"
    elif style_op_type is None:
        style_op_type = kwargs.get("operation_type")

    if display_operation_box:
        try:
            return display_operation_box(
                title=title,
                content=content or "",
                result_count=kwargs.get("result_count"),
                params=params,
                op_type=style_op_type,
                progress_line=progress_line,
                total_lines=total_lines,
                spinner_state=spinner_state,
                emoji=emoji
            )
        except Exception:
            pass

    return print_search_box(title, content or "", emoji=emoji)

def pretty_print_response(messages: list[dict[str, Any]], use_markdown: bool = False, spinner=None, agent_name: str = None) -> None:
    """Format and print messages, optionally rendering assistant content as markdown, and always prefixing agent responses with the agent's name."""
    if spinner:
        spinner.stop()
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    if not messages:
        logger.debug("No messages to print in pretty_print_response.")
        return

    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            logger.debug(f"Skipping non-dict message {i}")
            continue

        role = msg.get("role")
        sender = msg.get("sender", role if role else "Unknown")
        msg_content = msg.get("content")
        tool_calls = msg.get("tool_calls")

        if role == "assistant":
            display_name = agent_name or sender or "assistant"
            print(f"\033[95m[{display_name}]\033[0m: ", end="", flush=True)
            if msg_content:
                if RICH_AVAILABLE and '```' in msg_content:
                    import re
                    code_fence_pattern = r"```([\w\d]*)\n([\s\S]*?)```"
                    matches = re.findall(code_fence_pattern, msg_content)
                    if matches:
                        from rich.console import Console
                        from rich.syntax import Syntax
                        console = Console()
                        for lang, code in matches:
                            syntax = Syntax(code, lang or "python", theme="monokai", line_numbers=False)
                            console.print(syntax)
                        non_code = re.split(code_fence_pattern, msg_content)
                        for i, part in enumerate(non_code):
                            if i % 3 == 0 and part.strip():
                                print(part.strip(), flush=True)
                    else:
                        print(msg_content, flush=True)
                elif use_markdown and RICH_AVAILABLE:
                    render_markdown(msg_content)
                else:
                    print(msg_content, flush=True)
            elif not tool_calls:
                print(flush=True)

            if tool_calls and isinstance(tool_calls, list):
                print("  \033[92mTool Calls:\033[0m", flush=True)
                for tc in tool_calls:
                    if not isinstance(tc, dict):
                        continue
                    func = tc.get("function", {})
                    tool_name = func.get("name", "Unnamed Tool")
                    args_str = func.get("arguments", "{}")
                    try:
                        args_obj = json.loads(args_str)
                        args_pretty = ", ".join(f"{k}={v!r}" for k, v in args_obj.items())
                    except json.JSONDecodeError:
                        args_pretty = args_str
                    print(f"    \033[95m{tool_name}\033[0m({args_pretty})", flush=True)

        elif role == "tool":
            tool_name = msg.get("tool_name", msg.get("name", "tool"))
            tool_id = msg.get("tool_call_id", "N/A")
            try:
                content_obj = json.loads(msg_content)
                pretty_content = json.dumps(content_obj, indent=2)
            except (json.JSONDecodeError, TypeError):
                pretty_content = msg_content
            print(f"  \033[93m[{tool_name} Result ID: {tool_id}]\033[0m:\n    {pretty_content.replace(chr(10), chr(10) + '    ')}", flush=True)
        else:
            logger.debug(f"Skipping message {i} with role '{role}'")

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

    console = Console()
    cwd_base = os.path.basename(result['cwd'])
    header = Text("🐚 Ran terminal command", style="bold yellow")
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

# Add stubs for missing utility functions to satisfy imports

def get_spinner_state(spinner):
    """Return the current spinner state, or None if unavailable."""
    return spinner.current_spinner_state() if hasattr(spinner, 'current_spinner_state') else None


def print_operation_box(*args, **kwargs):
    """Display an operation box with title, content, and optional parameters."""
    # Extract console parameter if present
    console = kwargs.pop('console', None)

    # Map style names to actual color values
    style_mapping = {
        "info": "blue",
        "warning": "yellow",
        "error": "red",
        "success": "green"
    }

    # Replace style if it's in our mapping
    if 'style' in kwargs and kwargs['style'] in style_mapping:
        kwargs['style'] = style_mapping[kwargs['style']]

    try:
        from swarm.blueprints.common.operation_box_utils import display_operation_box

        # If console is provided, we need to handle it specially
        if console:
            # Create a custom implementation that uses the provided console
            # Extract arguments properly
            if len(args) >= 2:
                title = args[0]
                content = args[1]
            elif len(args) == 1:
                title = args[0]
                content = kwargs.get('content', '')
            else:
                title = kwargs.get('title', 'No Title')
                content = kwargs.get('content', '')
            
            style = kwargs.get('style', 'blue')
            result_count = kwargs.get('result_count')
            params = kwargs.get('params')
            op_type = kwargs.get('op_type')
            progress_line = kwargs.get('progress_line')
            total_lines = kwargs.get('total_lines')
            spinner_state = kwargs.get('spinner_state')
            emoji = kwargs.get('emoji')

            # Build box content
            box_content = f"{content}\n"
            if result_count is not None:
                box_content += f"Results: {result_count}\n"
            if params:
                for k, v in params.items():
                    box_content += f"Parameters: {k}={v}\n"
            if progress_line is not None and total_lines is not None:
                box_content += f"Progress: {progress_line}/{total_lines}\n"
            if spinner_state:
                box_content += f"[{spinner_state}]\n"
            if emoji:
                box_content = f"{emoji} {box_content}"

            # Use the provided console to print the panel
            from rich.panel import Panel
            from rich import box as rich_box
            console.print(Panel(box_content, title=title, style=style, box=rich_box.ROUNDED))
        else:
            display_operation_box(*args, **kwargs)
    except ImportError:
        # Fallback to basic print if operation_box_utils is not available
        print(f"Operation Box: {args[0] if args else 'No title'}")


def setup_rotating_httpx_log(*args, **kwargs):
    """Stub for rotating HTTPX log setup."""
    return None
