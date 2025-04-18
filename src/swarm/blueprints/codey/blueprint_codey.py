import os
from dotenv import load_dotenv

# Load user-level env first if present
user_env = os.path.expanduser('~/.config/swarm/.env')
if os.path.isfile(user_env):
    load_dotenv(dotenv_path=user_env, override=False)
# Then load project env, allowing override
load_dotenv(override=True)

import logging
from swarm.core.blueprint_base import BlueprintBase
from typing import List, Dict, Any, Optional, AsyncGenerator
import sys
import itertools
import threading
import time
from rich.console import Console
import os
from swarm.core.blueprint_runner import BlueprintRunner
from rich.style import Style
from rich.text import Text

# --- Spinner UX enhancement: Codex-style spinner ---
class CodeySpinner:
    # Codex-style Unicode/emoji spinner frames (for user enhancement TODO)
    FRAMES = [
        "Generating.",
        "Generating..",
        "Generating...",
        "Running...",
        "⠋ Generating...",
        "⠙ Generating...",
        "⠹ Generating...",
        "⠸ Generating...",
        "⠼ Generating...",
        "⠴ Generating...",
        "⠦ Generating...",
        "⠧ Generating...",
        "⠇ Generating...",
        "⠏ Generating...",
        "🤖 Generating...",
        "💡 Generating...",
        "✨ Generating..."
    ]
    SLOW_FRAME = "⏳ Generating... Taking longer than expected"
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10  # seconds

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._start_time = None
        self.console = Console()

    def start(self):
        self._stop_event.clear()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin)
        self._thread.start()

    def _spin(self):
        idx = 0
        while not self._stop_event.is_set():
            elapsed = time.time() - self._start_time
            if elapsed > self.SLOW_THRESHOLD:
                txt = Text(self.SLOW_FRAME, style=Style(color="yellow", bold=True))
            else:
                frame = self.FRAMES[idx % len(self.FRAMES)]
                txt = Text(frame, style=Style(color="cyan", bold=True))
            self.console.print(txt, end="\r", soft_wrap=True, highlight=False)
            time.sleep(self.INTERVAL)
            idx += 1
        self.console.print(" " * 40, end="\r")  # Clear line

    def stop(self, final_message="Done!"):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self.console.print(Text(final_message, style=Style(color="green", bold=True)))

# --- CLI Entry Point for codey script ---
def _cli_main():
    import argparse
    import sys
    import asyncio
    import os
    parser = argparse.ArgumentParser(
        description="Codey: Swarm-powered, Codex-compatible coding agent. Accepts Codex CLI arguments.",
        add_help=False)
    parser.add_argument("prompt", nargs="?", help="Prompt or task description (quoted)")
    parser.add_argument("-m", "--model", help="Model name (hf-qwen2.5-coder-32b, etc.)", default=os.getenv("LITELLM_MODEL"))
    parser.add_argument("-q", "--quiet", action="store_true", help="Non-interactive mode (only final output)")
    parser.add_argument("-o", "--output", help="Output file", default=None)
    parser.add_argument("--project-doc", help="Markdown file to include as context", default=None)
    parser.add_argument("--full-context", action="store_true", help="Load all project files as context")
    parser.add_argument("--approval", action="store_true", help="Require approval before executing actions")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    parser.add_argument("-h", "--help", action="store_true", help="Show usage and exit")
    args = parser.parse_args()

    if args.help:
        print_codey_help()
        sys.exit(0)

    if not args.prompt:
        print_codey_help()
        sys.exit(1)

    # Prepare messages and context
    messages = [{"role": "user", "content": args.prompt}]
    if args.project_doc:
        try:
            with open(args.project_doc, "r") as f:
                doc_content = f.read()
            messages.append({"role": "system", "content": f"Project doc: {doc_content}"})
        except Exception as e:
            print(f"Error reading project doc: {e}")
            sys.exit(1)
    if args.full_context:
        import os
        project_files = []
        for root, dirs, files in os.walk("."):
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.tsx', '.md', '.txt')) and not file.startswith('.'):
                    try:
                        with open(os.path.join(root, file), "r") as f:
                            content = f.read()
                        messages.append({
                            "role": "system",
                            "content": f"Project file {os.path.join(root, file)}: {content[:1000]}"
                        })
                    except Exception as e:
                        print(f"Warning: Could not read {os.path.join(root, file)}: {e}")
        print(f"Loaded {len(messages)-1} project files into context.")

    # Set model if specified
    blueprint = CodeyBlueprint(blueprint_id="cli", approval_required=args.approval)
    blueprint.coordinator.model = args.model

    def get_codey_agent_name():
        # Prefer Fiona, Sammy, Linus, else fallback
        try:
            if hasattr(blueprint, 'coordinator') and hasattr(blueprint.coordinator, 'name'):
                return blueprint.coordinator.name
            if hasattr(blueprint, 'name'):
                return blueprint.name
        except Exception:
            pass
        return "Codey"

    async def run_and_print():
        result_lines = []
        agent_name = get_codey_agent_name()
        from swarm.core.output_utils import pretty_print_response
        async for chunk in blueprint.run(messages):
            if args.quiet:
                last = None
                for c in blueprint.run(messages):
                    last = c
                if last:
                    if isinstance(last, dict) and 'content' in last:
                        print(last['content'])
                    else:
                        print(last)
                break
            else:
                # Always use pretty_print_response with agent_name for assistant output
                if isinstance(chunk, dict) and ('content' in chunk or chunk.get('role') == 'assistant'):
                    pretty_print_response([chunk], use_markdown=True, agent_name=agent_name)
                    if 'content' in chunk:
                        result_lines.append(chunk['content'])
                else:
                    print(chunk, end="")
                    result_lines.append(str(chunk))
        return ''.join(result_lines)

    if args.output:
        try:
            output = asyncio.run(run_and_print())
            with open(args.output, "w") as f:
                f.write(output)
            print(f"\nOutput written to {args.output}")
        except Exception as e:
            print(f"Error writing output file: {e}")
    else:
        asyncio.run(run_and_print())

if __name__ == "__main__":
    # Call CLI main
    sys.exit(_cli_main())
