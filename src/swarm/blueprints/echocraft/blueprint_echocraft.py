# --- Content for src/swarm/blueprints/echocraft/blueprint_echocraft.py ---
import logging
from typing import Optional
from pathlib import Path
from typing import List, Dict, Any, AsyncGenerator
import uuid # Import uuid to generate IDs
import time # Import time for timestamp
import os
from datetime import datetime
import pytz
from swarm.core.output_utils import print_operation_box

from swarm.core.blueprint_base import BlueprintBase
from agents import function_tool
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

logger = logging.getLogger(__name__)

# Last swarm update: 2024-03-07T14:30:00Z (UTC)

SPINNER_STATES = ['Generating.', 'Generating..', 'Generating...', 'Running...']

"""
EchoCraft Blueprint

Viral docstring update: Operational as of {} (UTC).
Self-healing, fileops-enabled, swarm-scalable.
"""

# [Swarm Propagation] Next Blueprint: rue_code
# rue_code key vars: logger, project_root, src_path
# rue_code guard: if src_path not in sys.path: sys.path.insert(0, src_path)
# rue_code debug: logger.debug("RueCode agent created: Rue (Coordinator)")
# rue_code error handling: try/except ImportError with sys.exit(1)

class EchoCraftBlueprint(BlueprintBase):
    def __init__(self, blueprint_id: str, config_path: Optional[Path] = None, **kwargs):
        super().__init__(blueprint_id, config_path=config_path, **kwargs)

    """
    A simple blueprint that echoes the last user message.
    Used for testing and demonstrating basic blueprint structure.
    """

    # No specific __init__ needed beyond the base class unless adding more params
    # def __init__(self, blueprint_id: str, **kwargs):
    #     super().__init__(blueprint_id=blueprint_id, **kwargs)
    #     logger.info(f"EchoCraftBlueprint '{self.blueprint_id}' initialized.")

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

    async def _original_run(self, messages: List[Dict[str, Any]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Echoes the content of the last message with role 'user'.
        Yields a final message in OpenAI ChatCompletion format.
        """
        logger.info(f"EchoCraftBlueprint run called with {len(messages)} messages.")

        # Ensure LLM profile is initialized for test compatibility
        if self._llm_profile_name is None:
            self._llm_profile_name = self.config.get("llm_profile", "default")

        last_user_message_content = "No user message found."
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message_content = msg.get("content", "(empty content)")
                logger.debug(f"Found last user message: {last_user_message_content}")
                break

        echo_content = f"Echo: {last_user_message_content}"
        logger.info(f"EchoCraftBlueprint yielding: {echo_content}")

        # --- Format the final output as an OpenAI ChatCompletion object ---
        completion_id = f"chatcmpl-echo-{uuid.uuid4()}"
        created_timestamp = int(time.time())

        final_message_chunk = {
            "id": completion_id,
            "object": "chat.completion",
            "created": created_timestamp,
            "model": self.llm_profile_name, # Use profile name as model identifier
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": echo_content,
                    },
                    "finish_reason": "stop",
                    "logprobs": None, # Add null logprobs if needed
                }
            ],
            # Add usage stats if desired/possible
            # "usage": {
            #     "prompt_tokens": 0,
            #     "completion_tokens": 0,
            #     "total_tokens": 0
            # }
        }
        yield final_message_chunk
        # --- End formatting change ---

        logger.info("EchoCraftBlueprint run finished.")

    async def run(self, messages: List[Dict[str, Any]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        last_result = None
        async for result in self._original_run(messages):
            last_result = result
            # Unified box UX for all user-facing results
            print_operation_box(
                op_type="Echo Result",
                results=[result["messages"][0]["content"]] if isinstance(result, dict) and "messages" in result and result["messages"] else [str(result)],
                params={"messages": messages},
                result_type="creative",
                summary="EchoCraft blueprint result",
                progress_line=None,
                spinner_state=None,
                operation_type="Echo Result",
                search_mode=None,
                total_lines=None
            )
            yield result
        if last_result is not None:
            await self.reflect_and_learn(messages, last_result)

    async def reflect_and_learn(self, messages, result):
        log = {
            'task': messages,
            'result': result,
            'reflection': 'Success' if self.success_criteria(result) else 'Needs improvement',
            'alternatives': self.consider_alternatives(messages, result),
            'swarm_lessons': self.query_swarm_knowledge(messages)
        }
        self.write_to_swarm_log(log)

    def success_criteria(self, result):
        if not result or (isinstance(result, dict) and 'error' in result):
            return False
        if isinstance(result, list) and result and 'error' in result[0].get('messages', [{}])[0].get('content', '').lower():
            return False
        return True

    def consider_alternatives(self, messages, result):
        alternatives = []
        if not self.success_criteria(result):
            alternatives.append('Try echoing a different message.')
            alternatives.append('Use a fallback echo agent.')
        else:
            alternatives.append('Add sentiment analysis to the echo.')
        return alternatives

    def query_swarm_knowledge(self, messages):
        import json, os
        path = os.path.join(os.path.dirname(__file__), '../../../swarm_knowledge.json')
        if not os.path.exists(path):
            return []
        with open(path, 'r') as f:
            knowledge = json.load(f)
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

    def create_starting_agent(self, mcp_servers):
        echo_agent = self.make_agent(
            name="EchoCraft",
            instructions="You are EchoCraft, the echo agent. You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks.",
            tools=[self.read_file_tool, self.write_file_tool, self.list_files_tool, self.execute_shell_command_tool],
            mcp_servers=mcp_servers
        )
        return echo_agent

if __name__ == "__main__":
    import asyncio
    import json
    print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   🗣️ ECHOCRAFT: MESSAGE MIRROR & SWARM UX DEMO              ║\n╠══════════════════════════════════════════════════════════════╣\n║ This blueprint echoes user messages, demonstrates swarm UX,  ║\n║ and showcases viral docstring propagation.                   ║\n║ Try running: python blueprint_echocraft.py                   ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")
    messages = [
        {"role": "user", "content": "Show me how EchoCraft mirrors messages and benefits from swarm UX patterns."}
    ]
    blueprint = EchoCraftBlueprint(blueprint_id="demo-1")
    async def run_and_print():
        async for response in blueprint.run(messages):
            print(json.dumps(response, indent=2))
    asyncio.run(run_and_print())
