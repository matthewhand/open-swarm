"""
Output utilities for Swarm blueprints.
"""

import json
import logging
import sys
from typing import List, Dict, Any

# Optional import for markdown rendering
try:
    from rich.markdown import Markdown
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)

def render_markdown(content: str) -> None:
    """Render markdown content using rich, if available."""
    if not RICH_AVAILABLE:
        print(content)
        return
    console = Console()
    md = Markdown(content)
    console.print(md)

def pretty_print_response(messages: List[Dict[str, Any]], use_markdown: bool = False, spinner=None) -> None:
    """Format and print messages, optionally rendering assistant content as markdown."""
    if spinner:
        spinner.stop()
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    if not messages:
        logger.debug("No messages to print in pretty_print_response.")
        return

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        role = msg.get("role")
        sender = msg.get("sender", role if role else "Unknown")
        msg_content = msg.get("content")
        tool_calls = msg.get("tool_calls")

        if role == "assistant":
            print(f"\033[94m{sender}\033[0m: ", end="")
            if msg_content:
                if use_markdown and RICH_AVAILABLE:
                    render_markdown(msg_content)
                else:
                    print(msg_content)
            elif not tool_calls:
                print()

            if tool_calls and isinstance(tool_calls, list):
                print("  \033[92mTool Calls:\033[0m")
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
                    print(f"    \033[95m{tool_name}\033[0m({args_pretty})")

        elif role == "tool":
            tool_name = msg.get("tool_name", msg.get("name", "tool"))
            tool_id = msg.get("tool_call_id", "N/A")
            try:
                content_obj = json.loads(msg_content)
                pretty_content = json.dumps(content_obj, indent=2)
            except (json.JSONDecodeError, TypeError):
                pretty_content = msg_content
            print(f"  \033[93m[{tool_name} Result ID: {tool_id}]\033[0m:\n    {pretty_content.replace(chr(10), chr(10) + '    ')}")
