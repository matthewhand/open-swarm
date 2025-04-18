"""
Output utilities for Swarm blueprints.
"""

import json
import logging
import os
import sys
from typing import List, Dict, Any

# Optional import for markdown rendering
try:
    from rich.markdown import Markdown
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.rule import Rule
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)

def render_markdown(content: str) -> None:
    """Render markdown content using rich, if available."""
    # --- DEBUG PRINT ---
    print(f"\n[DEBUG render_markdown called with rich={RICH_AVAILABLE}]", flush=True)
    if not RICH_AVAILABLE:
        print(content, flush=True) # Fallback print with flush
        return
    console = Console()
    md = Markdown(content)
    console.print(md) # Rich handles flushing

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

def pretty_print_response(messages: List[Dict[str, Any]], use_markdown: bool = False, spinner=None) -> None:
    """Format and print messages, optionally rendering assistant content as markdown."""
    # --- DEBUG PRINT ---
    print(f"\n[DEBUG pretty_print_response called with {len(messages)} messages, use_markdown={use_markdown}]", flush=True)

    if spinner:
        spinner.stop()
        sys.stdout.write("\r\033[K") # Clear spinner line
        sys.stdout.flush()

    if not messages:
        logger.debug("No messages to print in pretty_print_response.")
        return

    for i, msg in enumerate(messages):
         # --- DEBUG PRINT ---
        print(f"\n[DEBUG Processing message {i}: type={type(msg)}]", flush=True)
        if not isinstance(msg, dict):
            print(f"[DEBUG Skipping non-dict message {i}]", flush=True)
            continue

        role = msg.get("role")
        sender = msg.get("sender", role if role else "Unknown")
        msg_content = msg.get("content")
        tool_calls = msg.get("tool_calls")
        # --- DEBUG PRINT ---
        print(f"[DEBUG Message {i}: role={role}, sender={sender}, has_content={bool(msg_content)}, has_tools={bool(tool_calls)}]", flush=True)


        if role == "assistant":
            print(f"\033[94m{sender}\033[0m: ", end="", flush=True)
            if msg_content:
                 # --- DEBUG PRINT ---
                print(f"\n[DEBUG Assistant content found, printing/rendering... Rich={RICH_AVAILABLE}, Markdown={use_markdown}]", flush=True)
                if use_markdown and RICH_AVAILABLE:
                    render_markdown(msg_content)
                else:
                    # --- DEBUG PRINT ---
                    print(f"\n[DEBUG Using standard print for content:]", flush=True)
                    print(msg_content, flush=True) # Added flush
            elif not tool_calls:
                print(flush=True) # Flush newline if no content/tools

            if tool_calls and isinstance(tool_calls, list):
                print("  \033[92mTool Calls:\033[0m", flush=True)
                for tc in tool_calls:
                    if not isinstance(tc, dict): continue
                    func = tc.get("function", {})
                    tool_name = func.get("name", "Unnamed Tool")
                    args_str = func.get("arguments", "{}")
                    try: args_obj = json.loads(args_str); args_pretty = ", ".join(f"{k}={v!r}" for k, v in args_obj.items())
                    except json.JSONDecodeError: args_pretty = args_str
                    print(f"    \033[95m{tool_name}\033[0m({args_pretty})", flush=True)

        elif role == "tool":
            tool_name = msg.get("tool_name", msg.get("name", "tool"))
            tool_id = msg.get("tool_call_id", "N/A")
            try: content_obj = json.loads(msg_content); pretty_content = json.dumps(content_obj, indent=2)
            except (json.JSONDecodeError, TypeError): pretty_content = msg_content
            print(f"  \033[93m[{tool_name} Result ID: {tool_id}]\033[0m:\n    {pretty_content.replace(chr(10), chr(10) + '    ')}", flush=True)
        else:
            # --- DEBUG PRINT ---
            print(f"[DEBUG Skipping message {i} with role '{role}']", flush=True)

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
