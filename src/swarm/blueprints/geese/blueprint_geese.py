import os
from dotenv import load_dotenv; load_dotenv(override=True)

import logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')
import sys

def force_info_logging():
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    loglevel = os.environ.get('LOGLEVEL', None)
    debug_env = os.environ.get('SWARM_DEBUG', '0') == '1'
    debug_arg = '--debug' in sys.argv
    if debug_arg or debug_env or (loglevel and loglevel.upper() == 'DEBUG'):
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level, format='[%(levelname)s] %(name)s: %(message)s')
    root.setLevel(level)

force_info_logging()

import argparse
from typing import List, Dict, Any, Optional, ClassVar

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

from typing import Optional
from pathlib import Path
try:
    from agents import Agent, Tool, function_tool, Runner
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    from swarm.core.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed in blueprint_geese: {e}. Check 'openai-agents' install and project structure.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

import argparse

def setup_logging():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args, _ = parser.parse_known_args()
    loglevel = os.environ.get('LOGLEVEL', None)
    if args.debug or os.environ.get('SWARM_DEBUG', '0') == '1' or (loglevel and loglevel.upper() == 'DEBUG'):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    return args

args = setup_logging()

logger = logging.getLogger(__name__)

# --- Tools ---
def _create_story_outline(topic: str) -> str:
    logger.info(f"Tool: Generating outline for: {topic}")
    outline = f"Story Outline for '{topic}':\n1. Beginning: Introduce characters and setting.\n2. Middle: Develop conflict and rising action.\n3. Climax: The peak of the conflict.\n4. End: Resolution and aftermath."
    logger.debug(f"Generated outline: {outline}")
    return outline

@function_tool
def create_story_outline(topic: str) -> str:
    """Generates a basic story outline based on a topic."""
    return _create_story_outline(topic)

def _write_story_part(part_name: str, outline: str, previous_parts: str) -> str:
    logger.info(f"Tool: Writing story part: {part_name}")
    content = f"## {part_name}\n\nThis is the draft content for the '{part_name}' section. It follows:\n'{previous_parts[:100]}...' \nIt should align with the outline:\n'{outline}'"
    logger.debug(f"Generated content for {part_name}: {content[:100]}...")
    return content

@function_tool
def write_story_part(part_name: str, outline: str, previous_parts: str) -> str:
    """Writes a specific part of the story using the outline and previous context."""
    return _write_story_part(part_name, outline, previous_parts)

def _edit_story(full_story: str, edit_instructions: str) -> str:
    logger.info(f"Tool: Editing story with instructions: {edit_instructions}")
    edited_content = f"*** Edited Story Draft ***\n(Based on instructions: '{edit_instructions}')\n\n{full_story}\n\n[Editor's Notes: Minor tweaks applied for flow.]"
    logger.debug("Editing complete.")
    return edited_content

@function_tool
def edit_story(full_story: str, edit_instructions: str) -> str:
    """Edits the complete story based on instructions."""
    return _edit_story(full_story, edit_instructions)

from rich.console import Console
from rich.panel import Panel
from swarm.blueprints.common.spinner import SwarmSpinner
from swarm.core.output_utils import print_operation_box, get_spinner_state

class GeeseBlueprint(BlueprintBase):
    def __init__(self, blueprint_id: str, config_path: Optional[str] = None, **kwargs):
        super().__init__(blueprint_id, config_path, **kwargs)
        from agents import Agent
        # --- Specialized Agents ---
        self.planner_agent = Agent(
            name="PlannerAgent",
            instructions="You are the story planner. Break down the story into sections and assign tasks.",
            tools=[],
            model="gpt-3.5-turbo"
        ).as_tool("Planner", "Plan and outline stories.")
        self.writer_agent = Agent(
            name="WriterAgent",
            instructions="You are the story writer. Write and elaborate on story sections as assigned.",
            tools=[],
            model="gpt-3.5-turbo"
        ).as_tool("Writer", "Write story content.")
        self.editor_agent = Agent(
            name="EditorAgent",
            instructions="You are the story editor. Edit, proofread, and improve story sections.",
            tools=[],
            model="gpt-3.5-turbo"
        ).as_tool("Editor", "Edit and improve stories.")
        # --- Coordinator Agent ---
        self.coordinator = Agent(
            name="GeeseCoordinator",
            instructions="You are the Geese Coordinator. Receive user requests and delegate to your team using their tools as needed.",
            tools=[self.planner_agent, self.writer_agent, self.editor_agent],
            model="gpt-3.5-turbo"
        )
        self.logger = logging.getLogger(__name__)
        self._model_instance_cache = {}
        self._openai_client_cache = {}

    async def run(self, messages: List[dict], **kwargs):
        import time
        op_start = time.monotonic()
        from swarm.core.output_utils import print_operation_box, get_spinner_state
        instruction = messages[-1].get("content", "") if messages else ""
        if not instruction:
            import os
            border = '╔' if os.environ.get('SWARM_TEST_MODE') else None
            spinner_state = get_spinner_state(op_start)
            print_operation_box(
                op_type="Geese Error",
                results=["I need a user message to proceed."],
                params=None,
                result_type="creative",
                summary="No user message provided",
                progress_line=None,
                spinner_state=spinner_state,
                operation_type="Geese Run",
                search_mode=None,
                total_lines=None,
                border=border
            )
            yield {"messages": [{"role": "assistant", "content": "I need a user message to proceed."}]}
            return
        spinner_state = get_spinner_state(op_start)
        print_operation_box(
            op_type="Geese Input",
            results=[instruction],
            params=None,
            result_type="creative",
            summary="User instruction received",
            progress_line=None,
            spinner_state=spinner_state,
            operation_type="Geese Run",
            search_mode=None,
            total_lines=None
        )
        try:
            async for chunk in self._run_non_interactive(instruction, **kwargs):
                content = chunk["messages"][0]["content"] if (isinstance(chunk, dict) and "messages" in chunk and chunk["messages"]) else str(chunk)
                spinner_state = get_spinner_state(op_start)
                print_operation_box(
                    op_type="Geese Result",
                    results=[content],
                    params=None,
                    result_type="creative",
                    summary="Geese agent response",
                    progress_line=None,
                    spinner_state=spinner_state,
                    operation_type="Geese Run",
                    search_mode=None,
                    total_lines=None
                )
                yield chunk
        except Exception as e:
            import os
            border = '╔' if os.environ.get('SWARM_TEST_MODE') else None
            spinner_state = get_spinner_state(op_start)
            print_operation_box(
                op_type="Geese Error",
                results=[f"An error occurred: {e}"],
                params=None,
                result_type="creative",
                summary="Geese agent error",
                progress_line=None,
                spinner_state=spinner_state,
                operation_type="Geese Run",
                search_mode=None,
                total_lines=None,
                border=border
            )
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}

    def display_splash_screen(self, animated: bool = False):
        console = Console()
        splash = r'''
[bold magenta]
   ____                   _      _      ____  _             _
  / ___| __ _ _ __   __ _| | ___| |__  / ___|| |_ __ _ _ __| |_ ___
 | |  _ / _` | '_ \ / _` | |/ _ \ '_ \ \___ \| __/ _` | '__| __/ _ \
 | |_| | (_| | | | | (_| | |  __/ | | | ___) | || (_| | |  | ||  __/
  \____|\__,_|_| |_|\__, |_|\___|_| |_|____/ \__\__,_|_|   \__\___|
                   |___/
[/bold magenta]
[white]Collaborative Story Writing Blueprint[/white]
'''
        panel = Panel(splash, title="[bold magenta]Geese Blueprint[/]", border_style="magenta", expand=False)
        console.print(panel)
        console.print() # Blank line for spacing

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Returns the coordinator agent for GeeseBlueprint."""
        # mcp_servers not used in this blueprint
        return self.coordinator

def main():
    import argparse
    import sys
    import asyncio
    parser = argparse.ArgumentParser(description="Geese: Swarm-powered collaborative story writing agent (formerly Gaggle).")
    parser.add_argument("prompt", nargs="?", help="Prompt or story topic (quoted)")
    parser.add_argument("-i", "--input", help="Input file or directory", default=None)
    parser.add_argument("-o", "--output", help="Output file", default=None)
    parser.add_argument("--model", help="Model name (codex, gpt, etc.)", default=None)
    parser.add_argument("--temperature", type=float, help="Sampling temperature", default=0.1)
    parser.add_argument("--max-tokens", type=int, help="Max tokens", default=2048)
    parser.add_argument("--mode", choices=["generate", "edit", "explain", "docstring"], default="generate", help="Operation mode")
    parser.add_argument("--language", help="Programming language", default=None)
    parser.add_argument("--stop", help="Stop sequence", default=None)
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--version", action="version", version="geese 1.0.0")
    args = parser.parse_args()

    # Print help if no prompt and no input
    if not args.prompt and not args.input:
        parser.print_help()
        sys.exit(1)

    blueprint = GeeseBlueprint(blueprint_id="cli")
    messages = []
    if args.prompt:
        messages.append({"role": "user", "content": args.prompt})
    if args.input:
        try:
            with open(args.input, "r") as f:
                file_content = f.read()
            messages.append({"role": "user", "content": file_content})
        except Exception as e:
            print(f"Error reading input file: {e}")
            sys.exit(1)

    async def run_and_print():
        result_lines = []
        async for chunk in blueprint.run(messages):
            if isinstance(chunk, dict) and 'content' in chunk:
                print(chunk['content'], end="")
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
    main()
