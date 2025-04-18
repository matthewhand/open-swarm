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

# Patch: Expose underlying fileops functions for direct testing
class PatchedFunctionTool:
    def __init__(self, func, name):
        self.func = func
        self.name = name

# --- FileOps Tool Logic Definitions ---
def read_file(path: str) -> str:
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"
def write_file(path: str, content: str) -> str:
    try:
        with open(path, 'w') as f:
            f.write(content)
        return "OK: file written"
    except Exception as e:
        return f"ERROR: {e}"
def list_files(directory: str = '.') -> str:
    try:
        return '\n'.join(os.listdir(directory))
    except Exception as e:
        return f"ERROR: {e}"
def execute_shell_command(command: str) -> str:
    import subprocess
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout + result.stderr
    except Exception as e:
        return f"ERROR: {e}"
read_file_tool = PatchedFunctionTool(read_file, 'read_file')
write_file_tool = PatchedFunctionTool(write_file, 'write_file')
list_files_tool = PatchedFunctionTool(list_files, 'list_files')
execute_shell_command_tool = PatchedFunctionTool(execute_shell_command, 'execute_shell_command')

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

You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks.

If you are unsure, prefer a direct response. Never output tool schema, argument names, or placeholders to the user.
"""

fiona_instructions = """
You are Fiona Flame, the diligent git ops specialist for the Codey team.

Respond directly and naturally to creative or conversational prompts. Only use your tools (git_status, git_diff, git_add, git_commit, git_push) for explicit git/code requests.

You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks.
"""

sammy_instructions = """
You are SammyScript, the test runner and automation specialist.

For creative or general prompts, reply in natural language. Only use your tools (run_npm_test, run_pytest) for explicit test/code requests.

You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks.
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

# Spinner UX enhancement (Open Swarm TODO)
SPINNER_STATES = ['Generating.', 'Generating..', 'Generating...', 'Running...']

class CodeyBlueprint(BlueprintBase):
    def __init__(self, blueprint_id: str, config_path: Optional[str] = None, **kwargs):
        super().__init__(blueprint_id, config_path, **kwargs)
        class DummyLLM:
            def chat_completion_stream(self, messages, **_):
                class DummyStream:
                    def __aiter__(self): return self
                    async def __anext__(self):
                        raise StopAsyncIteration
                return DummyStream()
        self.llm = DummyLLM()
        self.logger = logging.getLogger(__name__)
        self._model_instance_cache = {}
        self._openai_client_cache = {}

    def render_prompt(self, template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        linus_corvalds = self.make_agent(
            name="Linus_Corvalds",
            instructions=linus_corvalds_instructions,
            tools=[git_status_tool, git_diff_tool, read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool],
            mcp_servers=mcp_servers
        )
        fiona_flame = self.make_agent(
            name="Fiona_Flame",
            instructions=fiona_instructions,
            tools=[git_status_tool, git_diff_tool, git_add_tool, git_commit_tool, git_push_tool, read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool],
            mcp_servers=mcp_servers
        )
        sammy_script = self.make_agent(
            name="SammyScript",
            instructions=sammy_instructions,
            tools=[run_npm_test_tool, run_pytest_tool, read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool],
            mcp_servers=mcp_servers
        )
        linus_corvalds.tools.append(fiona_flame.as_tool(tool_name="Fiona_Flame", tool_description="Delegate git actions to Fiona."))
        linus_corvalds.tools.append(sammy_script.as_tool(tool_name="SammyScript", tool_description="Delegate testing tasks to Sammy."))
        return linus_corvalds

    async def run(self, messages: List[dict], **kwargs):
        last_user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), None)
        if not last_user_message:
            yield {"messages": [{"role": "assistant", "content": "I need a user message to proceed."}]}
            return
        prompt_context = {
            "user_request": last_user_message,
            "history": messages[:-1],
            "available_tools": ["code"]
        }
        rendered_prompt = self.render_prompt("codey_prompt.j2", prompt_context)
        yield {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"[Codey LLM] Would respond to: {rendered_prompt}"
                }
            ]
        }
        return

if __name__ == "__main__":
    import asyncio
    import json
    messages = [
        {"role": "user", "content": "Write a function to reverse a string."}
    ]
    blueprint = CodeyBlueprint(blueprint_id="demo-1")
    async def run_and_print():
        async for response in blueprint.run(messages):
            print(json.dumps(response, indent=2))
    asyncio.run(run_and_print())
