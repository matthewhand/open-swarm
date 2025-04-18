import os
from dotenv import load_dotenv; load_dotenv(override=True)

import logging
from swarm.core.blueprint_base import BlueprintBase
from agents import Agent, Tool, function_tool, Runner
from agents.mcp import MCPServer
from typing import List, Dict, Any, Optional, AsyncGenerator
import sys
import itertools
import threading
import time
from rich.console import Console
import os
from swarm.core.blueprint_runner import BlueprintRunner
from swarm.core.spinner import Spinner as TerminalSpinner

# --- Tool Logic Definitions ---
def git_status() -> str:
    return "OK: git status placeholder"
def git_diff() -> str:
    return "OK: git diff placeholder"
def git_add() -> str:
    return "OK: git add placeholder"
def git_commit(message: str) -> str:
    return f"OK: git commit '{message}' placeholder"
def git_push() -> str:
    return "OK: git push placeholder"
def run_npm_test(args: str = "") -> str:
    return "OK: npm test placeholder"
def run_pytest(args: str = "") -> str:
    return "OK: pytest placeholder"

git_status_tool = function_tool(git_status)
git_diff_tool = function_tool(git_diff)
git_add_tool = function_tool(git_add)
git_commit_tool = function_tool(git_commit)
git_push_tool = function_tool(git_push)
run_npm_test_tool = function_tool(run_npm_test)
run_pytest_tool = function_tool(run_pytest)

linus_corvalds_instructions = """
You are Linus Corvalds, the resolute leader of the Codey creative team.

Respond directly and naturally to any user prompt that is creative, general, or conversational (for example, if the user asks you to write a poem, haiku, or answer a question, reply in plain language—do NOT invoke any tools or functions).

Only use your available tools (git_status, git_diff, git_add, git_commit, git_push) if the user specifically requests a git/code operation, or if the request cannot be fulfilled without a tool.

If you are unsure, prefer a direct response. Never output tool schema, argument names, or placeholders to the user.
"""

fiona_instructions = """
You are Fiona Flame, the diligent git ops specialist for the Codey team.

Respond directly and naturally to creative or conversational prompts. Only use your tools (git_status, git_diff, git_add, git_commit, git_push) for explicit git/code requests.
"""

sammy_instructions = """
You are SammyScript, the test runner and automation specialist.

For creative or general prompts, reply in natural language. Only use your tools (run_npm_test, run_pytest) for explicit test/code requests.
"""

# --- ANSI/Emoji Box Output Helpers ---
def ansi_box(title, content, emoji=None, count=None, params=None):
    box_lines = []
    header = f"\033[1;36m┏━ {emoji+' ' if emoji else ''}{title} ━{'━'*max(0, 40-len(title))}\033[0m"
    box_lines.append(header)
    if params:
        box_lines.append(f"\033[1;34m┃ Params: {params}\033[0m")
    if count is not None:
        box_lines.append(f"\033[1;33m┃ Results: {count}\033[0m")
    for line in content.split('\n'):
        box_lines.append(f"┃ {line}")
    box_lines.append("┗"+"━"*44)
    return "\n".join(box_lines)

class CodeyBlueprint(BlueprintBase):
    def __init__(self, blueprint_id: str, config_path: Optional[str] = None, **kwargs):
        super().__init__(blueprint_id, config_path, **kwargs)
        self.logger = logging.getLogger(__name__)
        self._model_instance_cache = {}
        self._openai_client_cache = {}

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        linus_corvalds = self.make_agent(
            name="Linus_Corvalds",
            instructions=linus_corvalds_instructions,
            tools=[git_status_tool, git_diff_tool],
            mcp_servers=mcp_servers
        )
        fiona_flame = self.make_agent(
            name="Fiona_Flame",
            instructions=fiona_instructions,
            tools=[git_status_tool, git_diff_tool, git_add_tool, git_commit_tool, git_push_tool],
            mcp_servers=mcp_servers
        )
        sammy_script = self.make_agent(
            name="SammyScript",
            instructions=sammy_instructions,
            tools=[run_npm_test_tool, run_pytest_tool],
            mcp_servers=mcp_servers
        )
        linus_corvalds.tools.append(fiona_flame.as_tool(tool_name="Fiona_Flame", tool_description="Delegate git actions to Fiona."))
        linus_corvalds.tools.append(sammy_script.as_tool(tool_name="SammyScript", tool_description="Delegate testing tasks to Sammy."))
        return linus_corvalds

    async def run(self, messages: List[dict], **kwargs):
        self.logger.info("CodeyBlueprint run method called.")
        instruction = messages[-1].get("content", "") if messages else ""
        try:
            mcp_servers = kwargs.get("mcp_servers", [])
            starting_agent = self.create_starting_agent(mcp_servers=mcp_servers)
            model_name = os.getenv("LITELLM_MODEL") or os.getenv("DEFAULT_LLM") or "gpt-3.5-turbo"
            if not starting_agent.model:
                yield {"messages": [{"role": "assistant", "content": f"Error: No model instance available for Codey agent. Check your LITELLM_MODEL, OPENAI_API_KEY, or DEFAULT_LLM config."}]}
                return
            if not starting_agent.tools:
                yield {"messages": [{"role": "assistant", "content": f"Warning: No tools registered for Codey agent. Only direct LLM output is possible."}]}
            required_mcps = []
            if hasattr(self, 'metadata') and self.metadata.get('required_mcp_servers'):
                required_mcps = self.metadata['required_mcp_servers']
                missing_mcps = [m for m in required_mcps if m not in [s.name for s in mcp_servers]]
                if missing_mcps:
                    yield {"messages": [{"role": "assistant", "content": f"Warning: Missing required MCP servers: {', '.join(missing_mcps)}. Some features may not work."}]}
            show_intermediate = kwargs.get("show_intermediate", False)
            spinner = None
            if show_intermediate:
                spinner = TerminalSpinner(interactive=True, custom_sequence="generating")
                spinner.start()
            try:
                async for chunk in BlueprintRunner.run_agent(starting_agent, instruction):
                    if show_intermediate:
                        for msg in chunk["messages"]:
                            print(msg["content"])
                    yield chunk
            finally:
                if spinner:
                    spinner.stop()
        except Exception as e:
            yield {"messages": [{"role": "assistant", "content": f"Error: {e}"}]}

if __name__ == "__main__":
    import argparse
    import asyncio
    parser = argparse.ArgumentParser(description="Run the Codey blueprint.")
    parser.add_argument('instruction', nargs=argparse.REMAINDER, help='Instruction for Codey to process (all args after -- are joined as the prompt)')
    parser.add_argument('--show-intermediate', action='store_true', help='Show all intermediate outputs (verbose mode)')
    args = parser.parse_args()
    # Join all positional arguments as the instruction
    instruction_args = args.instruction
    if instruction_args and instruction_args[0] == '--':
        instruction_args = instruction_args[1:]
    instruction = ' '.join(instruction_args).strip() if instruction_args else None
    show_intermediate = args.show_intermediate
    blueprint = CodeyBlueprint(blueprint_id="codey")
    if instruction:
        # Non-interactive mode: run once and exit
        async def main():
            messages = [{"role": "user", "content": instruction}]
            last_assistant_msg = None
            async for resp in blueprint.run(messages, show_intermediate=show_intermediate):
                for msg in resp["messages"]:
                    if show_intermediate:
                        print(msg["content"])
                    elif msg["role"] == "assistant":
                        last_assistant_msg = msg["content"]
            if not show_intermediate and last_assistant_msg is not None:
                print(last_assistant_msg)
        asyncio.run(main())
    else:
        # Interactive mode: loop and accept follow-ups
        async def interactive_loop():
            messages = []
            while True:
                try:
                    user_input = input("User: ").strip()
                except EOFError:
                    print("Exiting interactive mode.")
                    break
                if not user_input:
                    print("No input. Exiting.")
                    break
                messages.append({"role": "user", "content": user_input})
                async for resp in blueprint.run(messages):
                    for msg in resp["messages"]:
                        print(msg["content"])
        asyncio.run(interactive_loop())
