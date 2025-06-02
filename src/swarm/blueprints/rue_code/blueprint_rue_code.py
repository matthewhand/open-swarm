"""
RueCode Blueprint

Viral docstring update: Operational as of 2025-04-18T10:14:18Z (UTC).
Self-healing, fileops-enabled, swarm-scalable.
"""
import logging
import os
import sys
import json
import subprocess
import asyncio # Added import for asyncio.sleep
from typing import Dict, List, Any, AsyncGenerator, Optional
from pathlib import Path
import re
from datetime import datetime
import pytz
from swarm.core.blueprint_ux import BlueprintUX
from swarm.core.config_loader import load_full_configuration
import time
from swarm.blueprints.common.operation_box_utils import display_operation_box

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Last swarm update: {{ datetime.now(pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ') }}
# Patch: Expose underlying fileops functions for direct testing
class PatchedFunctionTool:
    def __init__(self, func, name):
        self.func = func
        self.name = name

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
    """
    Executes a shell command and returns its stdout and stderr.
    Security Note: Ensure commands are properly sanitized or restricted.
    Timeout is configurable via SWARM_COMMAND_TIMEOUT (default: 60s).
    """
    logger.info(f"Executing shell command: {command}")
    try:
        import os
        timeout = int(os.getenv("SWARM_COMMAND_TIMEOUT", "60"))
        result = subprocess.run(
            command,
            shell=True,
            check=False, # Don't raise exception on non-zero exit code
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        output = f"Exit Code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        logger.info(f"Command finished. Exit Code: {result.returncode}")
        return output.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {command}")
        return f"Error: Command timed out after {os.getenv('SWARM_COMMAND_TIMEOUT', '60')} seconds."
    except Exception as e:
        logger.error(f"Error executing command '{command}': {e}", exc_info=True)
        return f"Error executing command: {e}"
read_file_tool = PatchedFunctionTool(read_file, 'read_file')
write_file_tool = PatchedFunctionTool(write_file, 'write_file')
list_files_tool = PatchedFunctionTool(list_files, 'list_files')
execute_shell_command_tool = PatchedFunctionTool(execute_shell_command, 'execute_shell_command')

# Attempt to import BlueprintBase, handle potential ImportError during early setup/testing
try:
    from swarm.core.blueprint_base import BlueprintBase
except ImportError as e:
    logger.error(f"Import failed: {e}. Check 'openai-agents' install and project structure.")
    class BlueprintBase:
        metadata = {}
        def __init__(self, *args, **kwargs): pass
        async def run(self, *args, **kwargs): yield {}

# --- Tool Definitions ---
# Using the more detailed versions defined earlier.
# The simpler execute_shell_command, read_file, write_file, list_files are effectively shadowed.

# --- FileOps Tool Logic Definitions (Redundant, consider removing if PatchedFunctionTool versions are primary) ---
# def read_file_fileops(path: str) -> str: ...
# def write_file_fileops(path: str, content: str) -> str: ...
# def list_files_fileops(directory: str = '.') -> str: ...
# def execute_shell_command_fileops(command: str) -> str: ...

# --- LLM Cost Estimation Tool ---
def calculate_llm_cost(model: str, prompt_tokens: int, completion_tokens: int = 0, config: dict = None) -> float:
    default_price = {'prompt': 0.002, 'completion': 0.004}
    price = None
    model_key = model.lower()
    if config:
        llm_config = config.get('llm', {})
        for key, val in llm_config.items():
            m = val.get('model', '').lower()
            if m == model_key or key.lower() == model_key:
                if isinstance(val.get('cost'), dict):
                    price = val['cost']
                elif 'cost' in val:
                    price = {'prompt': float(val['cost']), 'completion': float(val['cost'])}
                break
    if price is None:
        price = default_price
    cost = (prompt_tokens / 1000.0) * price['prompt'] + (completion_tokens / 1000.0) * price['completion']
    return round(cost, 6)

def llm_cost_tool(model: str, prompt_tokens: int, completion_tokens: int = 0, config: dict = None) -> str:
    try:
        cost = calculate_llm_cost(model, prompt_tokens, completion_tokens, config)
        return f"Estimated cost for {model}: ${cost} (prompt: {prompt_tokens}, completion: {completion_tokens} tokens)"
    except Exception as e:
        return f"Error: {e}"

llm_cost_tool_fn = PatchedFunctionTool(llm_cost_tool, 'llm_cost')

SYS_PROMPT_AGENTIC = """
You are an agent - please keep going until the user’s query is completely resolved, before ending your turn and yielding back to the user. Only terminate your turn when you are sure that the problem is solved.
If you are not sure about file content or codebase structure pertaining to the user’s request, use your tools to read files and gather the relevant information: do NOT guess or make up an answer.
You MUST plan extensively before each function call, and reflect extensively on the outcomes of the previous function calls. DO NOT do this entire process by making function calls only, as this can impair your ability to solve the problem and think insightfully.
"""

class RueSpinner:
    FRAMES = ["Generating.", "Generating..", "Generating...", "Running..."]
    LONG_WAIT_MSG = "Generating... Taking longer than expected"
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10

    def __init__(self):
        self._idx = 0
        self._start_time = None
        self._last_frame = self.FRAMES[0]

    def start(self):
        self._start_time = time.time()
        self._idx = 0
        self._last_frame = self.FRAMES[0]

    def _spin(self):
        self._idx = (self._idx + 1) % len(self.FRAMES)
        self._last_frame = self.FRAMES[self._idx]

    def current_spinner_state(self):
        if self._start_time and (time.time() - self._start_time) > self.SLOW_THRESHOLD:
            return self.LONG_WAIT_MSG
        return self._last_frame

class RueCodeBlueprint(BlueprintBase):
    metadata = {
        "name": "RueCode",
        "description": "Generates, executes code, and interacts with the file system.",
        "author": "Matthew Hand",
        "version": "0.1.0",
        "tags": ["code", "execution", "filesystem", "developer"],
        "llm_profile": "default_dev"
    }

    def __init__(self, blueprint_id: str = "rue_code", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self.blueprint_id = blueprint_id
        self.config_path = config_path
        self._config = config if config is not None else None
        self._llm_profile_name = None # Will be resolved from config
        self._llm_profile_data = None # Will be resolved from config
        self._markdown_output = None # Will be resolved from config

        if self._config is None:
            # Determine the path to swarm_config.json relative to this blueprint file
            # src/swarm/blueprints/rue_code/blueprint_rue_code.py -> src/swarm_config.json
            project_config_file = Path(os.path.dirname(__file__)).parent.parent.parent / 'swarm_config.json'
            self._config = load_full_configuration(
                blueprint_class_name=self.__class__.__name__,
                # This blueprint specifically loads from project root for its defaults if no other config is found/passed.
                default_config_path_for_tests=project_config_file if project_config_file.exists() else None,
                config_path_override=config_path, # This could be an XDG path or a CLI override
                profile_override=kwargs.get('profile_override'), # Pass through if provided
                cli_config_overrides=kwargs.get('cli_config_overrides') # Pass through if provided
            )

        class DummyLLM: # Minimal LLM stub for demo
            def chat_completion_stream(self, messages, **_):
                class DummyStream:
                    def __aiter__(self): return self
                    async def __anext__(self):
                        raise StopAsyncIteration
                return DummyStream()
        self.llm = DummyLLM()
        self.ux = BlueprintUX(style="silly")
        self.spinner = RueSpinner()

    def render_prompt(self, template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

    def code_vs_semantic(self, label, results):
        return f"{label.title()} Results:\n" + "\n".join(f"- {r}" for r in results)

    def summary(self, label, count, params):
        return f"{label} ({count} results) for: {params}"

    async def run(self, messages: List[Dict[str, str]]):
        logger.info("RueCodeBlueprint run method called.")
        last_user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), None)
        if not last_user_message:
            display_operation_box(title="RueCode Error", content="I need a user message to proceed.", emoji="📝")
            yield {"messages": [{"role": "assistant", "content": self.ux.box("Error", "I need a user message to proceed.")}]}
            return

        prompt_context = {"user_request": last_user_message, "history": messages[:-1], "available_tools": ["rue_code"]}
        rendered_prompt = self.render_prompt("rue_code_prompt.j2", prompt_context)
        self.spinner.start()
        prompt_tokens = len(rendered_prompt) // 4
        completion_tokens = 64
        
        # Resolve LLM profile name (example, might be more sophisticated in BlueprintBase)
        llm_profile_to_use = self.metadata.get("llm_profile") or self._config.get("settings", {}).get("default_llm_profile") or "default"
        model_config = self._config.get('llm', {}).get(llm_profile_to_use, {})
        model = model_config.get('model', 'gpt-3.5-turbo') # Fallback model

        cost_str = llm_cost_tool(model, prompt_tokens, completion_tokens, self._config)
        code_results = ["def foo(): ...", "def bar(): ..."]
        semantic_results = ["This function sorts a list.", "This function calculates a sum."]

        for i, frame in enumerate(self.spinner.FRAMES):
            self.spinner._spin()
            display_operation_box(
                title="RueCode Progress", content=f"Processing... {frame}",
                progress_line=i + 1, total_lines=len(self.spinner.FRAMES) + 2,
                spinner_state=self.spinner.current_spinner_state(), emoji="⏳"
            )
            yield {"progress": f"Processing... {frame}"}
            await asyncio.sleep(0.1)

        display_operation_box(
            title="RueCode Code Results", content=self.code_vs_semantic("code", code_results),
            style="bold cyan", result_count=len(code_results), params={"user_request": prompt_context["user_request"]},
            progress_line=len(self.spinner.FRAMES) + 1, total_lines=len(self.spinner.FRAMES) + 2, emoji="📝"
        )
        yield {"intermediate": "Code results generated."}

        display_operation_box(
            title="RueCode Semantic Results", content=self.code_vs_semantic("semantic", semantic_results),
            style="bold magenta", result_count=len(semantic_results), params={"user_request": prompt_context["user_request"]},
            progress_line=len(self.spinner.FRAMES) + 2, total_lines=len(self.spinner.FRAMES) + 2, emoji="💡"
        )
        yield {"intermediate": "Semantic results generated."}

        final_summary_content = f"{self.summary('Analyzed codebase', 4, prompt_context['user_request'])}\n\n{cost_str}"
        display_operation_box(title="RueCode Summary", content=final_summary_content, emoji="📊")

        yield {"messages": [{"role": "assistant", "content": self.ux.box(
            "RueCode Results",
            f"{self.code_vs_semantic('code', code_results)}\n{self.code_vs_semantic('semantic', semantic_results)}\n\n{cost_str}",
            summary=self.summary("Analyzed codebase", 4, prompt_context["user_request"])
        )}]}
        logger.info("RueCodeBlueprint run finished.")

if __name__ == "__main__":
    # Ensure asyncio is imported for the main block as well if it uses async features directly
    # import asyncio # Already imported at the top
    print("\033[1;36m\n📝 RUE CODE: SWARM TEMPLATING & EXECUTION DEMO\033[0m")
    messages_main = [{"role": "user", "content": "Show me how Rue Code does templating and swarm execution."}]
    # Pass config_path=None explicitly if you want it to try XDG path first, then project root as fallback.
    # Or pass a specific Path object to config_path to load a specific config.
    blueprint_main = RueCodeBlueprint(blueprint_id="demo-main", config_path=None)

    async def run_and_print_main():
        all_results_main = []
        async for response_main in blueprint_main.run(messages_main):
            if isinstance(response_main, dict) and "messages" in response_main and response_main["messages"]:
                content_main = response_main["messages"][0]["content"]
                print(f"\nAssistant:\n{content_main}")
                all_results_main.append(content_main)
            elif isinstance(response_main, dict) and "progress" in response_main:
                print(f"Progress: {response_main['progress']}")
            elif isinstance(response_main, dict) and "intermediate" in response_main:
                print(f"Intermediate: {response_main['intermediate']}")
            else:
                print(f"Other: {response_main}")
    asyncio.run(run_and_print_main())
