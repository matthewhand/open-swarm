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
    # --- DEBUG PRINT ---
    print(f"\n[DEBUG render_markdown called with rich={RICH_AVAILABLE}]", flush=True)
    if not RICH_AVAILABLE:
        print(content, flush=True) # Fallback print with flush
        return
    console = Console()
    md = Markdown(content)
    console.print(md) # Rich handles flushing

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


