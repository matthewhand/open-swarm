"""
Codey Blueprint

Viral docstring update: Operational as of 2025-04-18T10:14:18Z (UTC).
Self-healing, fileops-enabled, swarm-scalable.
"""
# [Swarm Propagation] Next Blueprint: digitalbutlers
# digitalbutlers key vars: logger, project_root, src_path
# digitalbutlers guard: if src_path not in sys.path: sys.path.insert(0, src_path)
# digitalbutlers debug: logger.debug("Digital Butlers team created: Jeeves (Coordinator), Mycroft (Search), Gutenberg (Home).")
# digitalbutlers error handling: try/except ImportError with sys.exit(1)

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
from swarm.blueprints.common.spinner import SwarmSpinner
from swarm.blueprints.common.audit import AuditLogger
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from agents import MCPServer, Agent
from swarm.core.output_utils import print_operation_box, get_spinner_state

# --- CLI Entry Point for codey script ---
# Default instructions for Linus_Corvalds agent (fixes NameError)
linus_corvalds_instructions = (
    "You are Linus Corvalds, a senior software engineer and git expert. "
    "Assist with code reviews, git operations, and software engineering tasks. "
    "Delegate git actions to Fiona_Flame and testing tasks to SammyScript as needed."
)

# Default instructions for Fiona_Flame and SammyScript
fiona_instructions = (
    "You are Fiona Flame, a git specialist. Handle all git operations and delegate testing tasks to SammyScript as needed."
)
sammy_instructions = (
    "You are SammyScript, a testing and automation expert. Handle all test execution and automation tasks."
)

# Dummy tool objects for agent construction in test mode
class DummyTool:
    def __init__(self, name):
        self.name = name
    def __call__(self, *args, **kwargs):
        return f"[DummyTool: {self.name} called]"
    def __repr__(self):
        return f"<DummyTool {self.name}>"

git_status_tool = DummyTool("git_status")
git_diff_tool = DummyTool("git_diff")
git_add_tool = DummyTool("git_add")
git_commit_tool = DummyTool("git_commit")
git_push_tool = DummyTool("git_push")
read_file_tool = DummyTool("read_file")
write_file_tool = DummyTool("write_file")
list_files_tool = DummyTool("list_files")
execute_shell_command_tool = DummyTool("execute_shell_command")
run_npm_test_tool = DummyTool("run_npm_test")
run_pytest_tool = DummyTool("run_pytest")

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
    parser.add_argument("--audit", action="store_true", help="Enable session audit trail logging (jsonl)")
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
    audit_logger = AuditLogger(enabled=getattr(args, "audit", False))
    blueprint = CodeyBlueprint(blueprint_id="cli", audit_logger=audit_logger)
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

# --- Main entry point for CLI ---
def main():
    from swarm.blueprints.codey.codey_cli import main as cli_main
    cli_main()

# Resolve all merge conflicts by keeping the main branch's logic for agent creation, UX, and error handling, as it is the most up-to-date and tested version. Integrate any unique improvements from the feature branch only if they do not conflict with stability or UX.

class CodeyBlueprint(BlueprintBase):
    def __init__(self, blueprint_id: str, config_path: Optional[str] = None, audit_logger: AuditLogger = None, approval_policy: dict = None, **kwargs):
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
        self.audit_logger = audit_logger or AuditLogger(enabled=False)
        self.approval_policy = approval_policy or {}

    def render_prompt(self, template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

    def create_starting_agent(self, mcp_servers: "List[MCPServer]", no_tools: bool = False) -> "Agent":
        # If SWARM_TEST_MODE or no_tools is set, don't attach tools (for compatibility with ChatCompletions API)
        import os
        test_mode = os.environ.get("SWARM_TEST_MODE", "0") == "1" or no_tools
        tools_lin = [] if test_mode else [git_status_tool, git_diff_tool, read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool]
        tools_fiona = [] if test_mode else [git_status_tool, git_diff_tool, git_add_tool, git_commit_tool, git_push_tool, read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool]
        tools_sammy = [] if test_mode else [run_npm_test_tool, run_pytest_tool, read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool]
        linus_corvalds = self.make_agent(
            name="Linus_Corvalds",
            instructions=linus_corvalds_instructions,
            tools=tools_lin,
            mcp_servers=mcp_servers
        )
        fiona_flame = self.make_agent(
            name="Fiona_Flame",
            instructions=fiona_instructions,
            tools=tools_fiona,
            mcp_servers=mcp_servers
        )
        sammy_script = self.make_agent(
            name="SammyScript",
            instructions=sammy_instructions,
            tools=tools_sammy,
            mcp_servers=mcp_servers
        )
        # Only append agent tools if not in test mode
        if not test_mode:
            linus_corvalds.tools.append(fiona_flame.as_tool(tool_name="Fiona_Flame", tool_description="Delegate git actions to Fiona."))
            linus_corvalds.tools.append(sammy_script.as_tool(tool_name="SammyScript", tool_description="Delegate testing tasks to Sammy."))
        return linus_corvalds

    async def _original_run(self, messages: List[dict], **kwargs):
        self.audit_logger.log_event("completion", {"event": "start", "messages": messages})
        last_user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), None)
        if not last_user_message:
            yield {"messages": [{"role": "assistant", "content": "I need a user message to proceed."}]}
            self.audit_logger.log_event("completion", {"event": "no_user_message", "messages": messages})
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
        self.audit_logger.log_event("completion", {"event": "end", "messages": messages})
        return

    async def run(self, messages: List[dict], **kwargs):
        import time
        op_start = time.monotonic()
        from swarm.core.output_utils import print_operation_box, get_spinner_state
        instruction = messages[-1].get("content", "") if messages else ""
        self.audit_logger.log_event("agent_action", {"status": "start"})
        self.audit_logger.log_event("completion", {"event": "start", "messages": messages})
        if not instruction:
            spinner_state = get_spinner_state(op_start)
            print_operation_box(
                op_type="Codey Error",
                results=["I need a user message to proceed."],
                params=None,
                result_type="codey",
                summary="No user message provided",
                progress_line=None,
                spinner_state=spinner_state,
                operation_type="Codey Run",
                search_mode=None,
                total_lines=None
            )
            self.audit_logger.log_event("completion", {"event": "no_user_message", "messages": messages})
            yield {"messages": [{"role": "assistant", "content": "I need a user message to proceed."}]}
            self.audit_logger.log_event("agent_action", {"status": "end"})
            self.audit_logger.log_event("completion", {"status": "done"})
            return
        spinner_state = get_spinner_state(op_start)
        print_operation_box(
            op_type="Codey Input",
            results=[instruction],
            params=None,
            result_type="codey",
            summary="User instruction received",
            progress_line=None,
            spinner_state=spinner_state,
            operation_type="Codey Run",
            search_mode=None,
            total_lines=None
        )
        import os
        test_mode = os.environ.get("SWARM_TEST_MODE", "0") == "1"
        if test_mode:
            canned = {"messages": [{"role": "assistant", "content": f"[Codey LLM] Would respond to: {instruction}"}]}
            self.audit_logger.log_event("agent_action", {"event": "test_action", "messages": messages, "action": "respond"})
            self.audit_logger.log_event("reflection", {"event": "test_reflection", "messages": messages, "reflection": "success"})
            self.audit_logger.log_event("completion", {"event": "end", "messages": messages})
            yield canned
            self.audit_logger.log_event("agent_action", {"status": "end"})
            self.audit_logger.log_event("completion", {"status": "done"})
            return
        async for chunk in self._run_non_interactive(instruction, **kwargs):
            content = chunk["messages"][0]["content"] if (isinstance(chunk, dict) and "messages" in chunk and chunk["messages"]) else str(chunk)
            spinner_state = get_spinner_state(op_start)
            print_operation_box(
                op_type="Codey Result",
                results=[content],
                params=None,
                result_type="codey",
                summary="Codey agent response",
                progress_line=None,
                spinner_state=spinner_state,
                operation_type="Codey Run",
                search_mode=None,
                total_lines=None
            )
            # Audit log agent action
            self.audit_logger.log_event("agent_action", {
                "event": "agent_action",
                "content": content,
                "messages": messages
            })
            yield chunk
            # Log reflection event after yielding result
            await self.reflect_and_learn(messages, content)
        self.audit_logger.log_event("agent_action", {"status": "end"})
        self.audit_logger.log_event("completion", {"status": "done"})

    async def _run_non_interactive(self, instruction: str, **kwargs) -> Any:
        logger = logging.getLogger(__name__)
        from agents import Runner
        import time
        op_start = time.monotonic()
        try:
            result = await Runner.run(self.create_starting_agent([]), instruction)
            if hasattr(result, "__aiter__"):
                async for chunk in result:
                    result_content = getattr(chunk, 'final_output', str(chunk))
                    spinner_state = get_spinner_state(op_start)
                    print_operation_box(
                        op_type="Codey Result",
                        results=[result_content],
                        params=None,
                        result_type="codey",
                        summary="Codey agent response",
                        progress_line=None,
                        spinner_state=spinner_state,
                        operation_type="Codey Run",
                        search_mode=None,
                        total_lines=None
                    )
                    self.audit_logger.log_event("agent_action", {
                        "event": "agent_action",
                        "content": result_content,
                        "instruction": instruction
                    })
                    yield chunk
            elif isinstance(result, (list, dict)):
                if isinstance(result, list):
                    for chunk in result:
                        result_content = getattr(chunk, 'final_output', str(chunk))
                        spinner_state = get_spinner_state(op_start)
                        print_operation_box(
                            op_type="Codey Result",
                            results=[result_content],
                            params=None,
                            result_type="codey",
                            summary="Codey agent response",
                            progress_line=None,
                            spinner_state=spinner_state,
                            operation_type="Codey Run",
                            search_mode=None,
                            total_lines=None
                        )
                        self.audit_logger.log_event("agent_action", {
                            "event": "agent_action",
                            "content": result_content,
                            "instruction": instruction
                        })
                        yield chunk
                else:
                    result_content = getattr(result, 'final_output', str(result))
                    spinner_state = get_spinner_state(op_start)
                    print_operation_box(
                        op_type="Codey Result",
                        results=[result_content],
                        params=None,
                        result_type="codey",
                        summary="Codey agent response",
                        progress_line=None,
                        spinner_state=spinner_state,
                        operation_type="Codey Run",
                        search_mode=None,
                        total_lines=None
                    )
                    self.audit_logger.log_event("agent_action", {
                        "event": "agent_action",
                        "content": result_content,
                        "instruction": instruction
                    })
                    yield result
            elif result is not None:
                spinner_state = get_spinner_state(op_start)
                print_operation_box(
                    op_type="Codey Result",
                    results=[str(result)],
                    params=None,
                    result_type="codey",
                    summary="Codey agent response",
                    progress_line=None,
                    spinner_state=spinner_state,
                    operation_type="Codey Run",
                    search_mode=None,
                    total_lines=None
                )
                self.audit_logger.log_event("agent_action", {
                    "event": "agent_action",
                    "content": str(result),
                    "instruction": instruction
                })
                yield {"messages": [{"role": "assistant", "content": str(result)}]}
        except Exception as e:
            logger.error(f"Error during non-interactive run: {e}", exc_info=True)
            print_operation_box(
                op_type="Codey Error",
                results=[f"An error occurred: {e}"],
                params=None,
                result_type="codey",
                summary="Codey agent error",
                progress_line=None,
                spinner_state="Error!",
                operation_type="Codey Run",
                search_mode=None,
                total_lines=None
            )
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}

    async def reflect_and_learn(self, messages, result):
        # Analyze the result, compare with swarm knowledge, adapt if needed
        log = {
            'task': messages,
            'result': result,
            'reflection': 'Success' if self.success_criteria(result) else 'Needs improvement',
            'alternatives': self.consider_alternatives(messages, result),
            'swarm_lessons': self.query_swarm_knowledge(messages)
        }
        self.write_to_swarm_log(log)
        self.audit_logger.log_event("reflection", log)
        # Optionally, adjust internal strategies or propose a patch

    def success_criteria(self, result):
        # Success if result contains non-empty messages and no error
        if not result or (isinstance(result, dict) and 'error' in result):
            return False
        if isinstance(result, list) and result and 'error' in result[0].get('messages', [{}])[0].get('content', '').lower():
            return False
        return True

    def consider_alternatives(self, messages, result):
        alternatives = []
        if not self.success_criteria(result):
            alternatives.append('Retry with alternate agent or tool.')
            alternatives.append('Fallback to simpler operation.')
        else:
            alternatives.append('Optimize for speed or resource use.')
        return alternatives

    def query_swarm_knowledge(self, messages):
        import json, os
        path = os.path.join(os.path.dirname(__file__), '../../../swarm_knowledge.json')
        if not os.path.exists(path):
            return []
        with open(path, 'r') as f:
            knowledge = json.load(f)
        # Find similar tasks
        task_str = json.dumps(messages)
        return [entry for entry in knowledge if entry.get('task_str') == task_str]

    def write_to_swarm_log(self, log):
        import json, os, time
        from filelock import FileLock, Timeout
        path = os.path.join(os.path.dirname(__file__), '../../../swarm_log.json')
        lock_path = path + '.lock'
        log['task_str'] = json.dumps(log['task'])
        for attempt in range(10):
            try:
                with FileLock(lock_path, timeout=5):
                    if os.path.exists(path):
                        with open(path, 'r') as f:
                            try:
                                logs = json.load(f)
                            except json.JSONDecodeError:
                                logs = []
                    else:
                        logs = []
                    logs.append(log)
                    with open(path, 'w') as f:
                        json.dump(logs, f, indent=2)
                break
            except Timeout:
                time.sleep(0.2 * (attempt + 1))

    def check_approval(self, tool_name, **kwargs):
        policy = self.approval_policy.get(tool_name, "allow")
        if policy == "deny":
            print(f"[DENIED] Tool '{tool_name}' is denied by approval policy.")
            self.audit_logger.log_event("approval_denied", {"tool": tool_name, "kwargs": kwargs})
            raise PermissionError(f"Tool '{tool_name}' denied by approval policy.")
        elif policy == "ask":
            print(f"[APPROVAL NEEDED] Tool '{tool_name}' wants to run with args: {kwargs}")
            self.audit_logger.log_event("approval_requested", {"tool": tool_name, "kwargs": kwargs})
            resp = input("Approve? [y/N]: ").strip().lower()
            if resp != "y":
                print(f"[DENIED] Tool '{tool_name}' not approved by user.")
                self.audit_logger.log_event("approval_user_denied", {"tool": tool_name, "kwargs": kwargs})
                raise PermissionError(f"Tool '{tool_name}' denied by user.")
            self.audit_logger.log_event("approval_user_approved", {"tool": tool_name, "kwargs": kwargs})
        # else allow

    # Example: wrap file write and shell exec tools for approval
    def write_file_with_approval(self, path, content):
        self.check_approval("tool.fs.write", path=path)
        # Simulate file write (for demo)
        with open(path, "w") as f:
            f.write(content)
        print(f"[WRITE] File written: {path}")

    def shell_exec_with_approval(self, command):
        self.check_approval("tool.shell.exec", command=command)
        # Simulate shell exec (for demo)
        import subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        print(f"[SHELL] Command output: {result.stdout.strip()}")
        return result.stdout.strip()

    def get_cli_splash(self):
        return "Codey CLI - Approval Workflow Demo\nType --help for usage."

if __name__ == "__main__":
    import asyncio
    import json
    import random
    import string
    from concurrent.futures import ThreadPoolExecutor

    print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   🤖 CODEY: SWARM ULTIMATE LIMIT TEST                        ║\n╠══════════════════════════════════════════════════════════════╣\n║ ULTIMATE: Multi-agent, multi-step, parallel, self-modifying  ║\n║ workflow with error injection, rollback, and viral patching. ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")

    def random_string():
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    async def consume_asyncgen(agen):
        results = []
        async for item in agen:
            results.append(item)
        return results

    async def run_limit_test():
        blueprint = CodeyBlueprint(blueprint_id="ultimate-limit-test")
        tasks = []
        # Step 1: Parallel file edits with injected errors and rollbacks
        for i in range(3):
            fname = f"swarm_test_{i}_{random_string()}.txt"
            content = f"Swarm Power {i} - {random_string()}"
            messages = [
                {"role": "user", "content": f"Create file '{fname}' with content '{content}', commit, then inject an error, rollback, and verify file state."}
            ]
            tasks.append(consume_asyncgen(blueprint.run(messages)))
        # Step 2: Orchestrated multi-agent workflow with viral patching
        messages = [
            {"role": "user", "content": "Agent A edits README.md, Agent B reviews and intentionally injects a bug, Agent C detects and patches it, Agent D commits and shows the diff. Log every step, agent, and patch."}
        ]
        tasks.append(consume_asyncgen(blueprint.run(messages)))
        # Step 3: Self-modifying code and viral propagation
        messages = [
            {"role": "user", "content": "Modify your own blueprint to add a new function 'swarm_propagate', propagate it to another blueprint, and verify the function exists in both. Log all steps."}
        ]
        tasks.append(consume_asyncgen(blueprint.run(messages)))
        # Run all tasks in parallel, logging every intermediate step
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for idx, result in enumerate(results):
            print(f"\n[PARALLEL TASK {idx+1}] Result:")
            if isinstance(result, Exception):
                print(f"Exception: {result}")
            else:
                for response in result:
                    print(json.dumps(response, indent=2))

class SwarmSpinner:
    def __init__(self, console: Console, message: str = "Working..."):
        self.console = console
        self.message = message
        self._stop_event = threading.Event()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin)
        self._thread.start()

    # Codex-style spinner frames (standardized for Swarm blueprints)
    FRAMES = [
        "Generating.",
        "Generating..",
        "Generating...",
        "Running..."
    ]
    SLOW_FRAME = "Generating... Taking longer than expected"
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10  # seconds

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

    def stop(self):
        self._stop_event.set()
        self._thread.join()
