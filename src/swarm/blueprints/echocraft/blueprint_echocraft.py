# --- Content for src/swarm/blueprints/echocraft/blueprint_echocraft.py ---
import logging
import os
import subprocess
import threading
import time  # Import time for timestamp
import uuid  # Import uuid to generate IDs
from collections.abc import AsyncGenerator
from typing import Any
import json # Import json for writing to file
import sys # Import sys for stderr
import tempfile # Import tempfile for temporary directory

from rich.console import Console
from rich.style import Style
from rich.text import Text

from swarm.core.blueprint_base import BlueprintBase
from swarm.ux.ansi_box import ansi_box


# Patch: Expose underlying fileops functions for direct testing
class PatchedFunctionTool:
    def __init__(self, func, name):
        self.func = func
        self.name = name

def read_file(path: str) -> str:
    try:
        with open(path) as f:
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
    Timeout is configurable via SWARM_COMMAND_TIMEOUT (default: 60s).
    """
    logger.info(f"Executing shell command: {command}")
    try:
        import os
        timeout = int(os.getenv("SWARM_COMMAND_TIMEOUT", "60"))
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
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

logger = logging.getLogger(__name__)

# Last swarm update: 2024-03-07T14:30:00Z (UTC)
# Enhanced spinner UX with more states and better visual feedback
SPINNER_STATES = [
    '🔄 Initializing EchoCraft...',
    '✨ Analyzing requirements...',
    '🔧 Setting up development environment...',
    '📝 Generating code structure...',
    '🧪 Running initial tests...',
    '🚀 Building and compiling...',
    '✅ Deployment ready!',
    '🎉 EchoCraft complete!'
]

# Enhanced spinner class with better UX
class EnhancedSpinner:
    def __init__(self):
        self.states = SPINNER_STATES
        self.current_state = 0
        self.running = False
    
    async def start(self):
        self.running = True
        while self.running:
            print(f"\r{self.states[self.current_state % len(self.states)]}", end='', flush=True)
            self.current_state += 1
            await asyncio.sleep(0.5)
    
    def stop(self):
        self.running = False
        print("\r" + " " * 50 + "\r", end='', flush=True)
        print("✅ EchoCraft process completed successfully!")

"""
EchoCraft Blueprint

Viral docstring update: Operational as of {} (UTC).
Expertise list: echo, demo
Self-healing, fileops-enabled, swarm-scalable.
"""

# [Swarm Propagation] Next Blueprint: rue_code
# rue_code key vars: logger, project_root, src_path
# rue_code guard: if src_path not in sys.path: sys.path.insert(0, src_path)
# rue_code debug: logger.debug("RueCode agent created: Rue (Coordinator)")
# rue_code error handling: try/except ImportError with sys.exit(1)

# --- Spinner and ANSI/emoji operation box for unified UX (for CLI/dev runs)---
class EchoCraftSpinner:
    FRAMES = [
        "Generating.", "Generating..", "Generating...", "Running...",
        "⠋ Generating...", "⠙ Generating...", "⠹ Generating...", "⠸ Generating...",
        "⠼ Generating...", "⠴ Generating...", "⠦ Generating...", "⠧ Generating...",
        "⠇ Generating...", "⠏ Generating...", "🤖 Generating...", "💡 Generating...", "✨ Generating..."
    ]
    SLOW_FRAME = "Generating... Taking longer than expected"
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10  # seconds

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._start_time = None
        self.console = Console()
        self._last_frame = None
        self._last_slow = False
        # Allow tuning via environment variable; fallback to default
        try:
            self._slow_threshold = int(os.getenv("ECHOCRAFT_SPINNER_SLOW_THRESHOLD", str(self.SLOW_THRESHOLD)))
        except Exception:
            self._slow_threshold = self.SLOW_THRESHOLD

    def start(self):
        self._stop_event.clear()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        idx = 0
        while not self._stop_event.is_set():
            elapsed = time.time() - self._start_time
            if elapsed > self._slow_threshold:
                txt = Text(self.SLOW_FRAME, style=Style(color="yellow", bold=True))
                self._last_frame = self.SLOW_FRAME
                self._last_slow = True
            else:
                frame = self.FRAMES[idx % len(self.FRAMES)]
                txt = Text(frame, style=Style(color="cyan", bold=True))
                self._last_frame = frame
                self._last_slow = False
            self.console.print(txt, end="\r", soft_wrap=True, highlight=False)
            time.sleep(self.INTERVAL)
            idx += 1
        self.console.print(" " * 40, end="\r")  # Clear line

    def stop(self, final_message="Done!"):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self.console.print(Text(final_message, style=Style(color="green", bold=True)))

    def current_spinner_state(self):
        if self._last_slow:
            return self.SLOW_FRAME
        return self._last_frame or self.FRAMES[0]


def print_operation_box(op_type, results, params=None, result_type="echo", taking_long=False):
    emoji = "🗣️" if result_type == "echo" else "🔍"
    style = 'success' if result_type == "echo" else 'default'
    box_title = op_type if op_type else ("EchoCraft Output" if result_type == "echo" else "Results")
    summary_lines = []
    count = len(results) if isinstance(results, list) else 0
    summary_lines.append(f"Results: {count}")
    if params:
        for k, v in params.items():
            summary_lines.append(f"{k.capitalize()}: {v}")
    box_content = "\n".join(summary_lines + ["\n".join(map(str, results))])
    ansi_box(box_title, box_content, count=count, params=params, style=style if not taking_long else 'warning', emoji=emoji)

class EchoCraftBlueprint(BlueprintBase):
    def __init__(self, blueprint_id: str = "echocraft", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self.blueprint_id = blueprint_id
        self.config_path = config_path
        self._config = config if config is not None else {}
        self._llm_profile_name = None
        self._llm_profile_data = None
        self._markdown_output = None
        # Add other attributes as needed for Echocraft
        # ...

    """
    A simple blueprint that echoes the last user message.
    Used for testing and demonstrating basic blueprint structure.
    """

    # No specific __init__ needed beyond the base class unless adding more params
    # def __init__(self, blueprint_id: str, **kwargs):
    #     super().__init__(blueprint_id=blueprint_id, **kwargs)
    #     logger.info(f"EchoCraftBlueprint '{self.blueprint_id}' initialized.")

    # --- FileOps Tool Logic Definitions (bound methods) ---
    def read_file(self, path: str) -> str:
        try:
            with open(path) as f:
                return f.read()
        except Exception as e:
            return f"ERROR: {e}"

    def write_file(self, path: str, content: str) -> str:
        try:
            with open(path, 'w') as f:
                f.write(content)
            return "OK: file written"
        except Exception as e:
            return f"ERROR: {e}"

    def list_files(self, directory: str = '.') -> str:
        try:
            return '\n'.join(os.listdir(directory))
        except Exception as e:
            return f"ERROR: {e}"

    def execute_shell_command(self, command: str) -> str:
        """
        Executes a shell command and returns its stdout and stderr.
        Timeout is configurable via SWARM_COMMAND_TIMEOUT (default: 60s).
        """
        logger.info(f"Executing shell command: {command}")
        try:
            import os
            timeout = int(os.getenv("SWARM_COMMAND_TIMEOUT", "60"))
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
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

    # Bind tools as PatchedFunctionTool wrappers referencing bound methods
    read_file_tool = PatchedFunctionTool(read_file, 'read_file')
    write_file_tool = PatchedFunctionTool(write_file, 'write_file')
    list_files_tool = PatchedFunctionTool(list_files, 'list_files')
    execute_shell_command_tool = PatchedFunctionTool(execute_shell_command, 'execute_shell_command')

    async def _original_run(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
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
            "model": self.llm_profile_name,  # Use profile name as model identifier
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": echo_content,
                    },
                    "finish_reason": "stop",
                    "logprobs": None,  # Add null logprobs if needed
                }
            ],
        }
        yield final_message_chunk

        logger.info("EchoCraftBlueprint run finished.")

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        """
        Wrapper around _original_run to keep public API stable and allow reflection.
        """
        last_result = None
        async for result in self._original_run(messages, **kwargs):
            last_result = result
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
        import json
        import os
        path = os.path.join(os.path.dirname(__file__), '../../../swarm_knowledge.json')
        if not os.path.exists(path):
            return []
        with open(path) as f:
            knowledge = json.load(f)
        task_str = json.dumps(messages)
        return [entry for entry in knowledge if entry.get('task_str') == task_str]

    def write_to_swarm_log(self, log):
        import json
        import os
        import time
        import tempfile # Import tempfile

        from filelock import FileLock, Timeout
        # Use a temporary directory for the log file
        log_dir = os.path.join(tempfile.gettempdir(), "swarm_logs")
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, 'swarm_log.json')
        lock_path = path + '.lock'
        log['task_str'] = json.dumps(log['task'])
        for attempt in range(10):
            try:
                with FileLock(lock_path, timeout=5):
                    if os.path.exists(path):
                        with open(path) as f:
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

# Exported helper for tests and __main__
async def run_echocraft_cli(blueprint: 'EchoCraftBlueprint', messages: list[dict[str, Any]]):
    """
    Run EchoCraft from a CLI-like context and render a result box.
    Yields nothing; prints output to stdout using print_operation_box.
    """
    spinner = EchoCraftSpinner()
    spinner.start()
    try:
        all_results = []
        async for response in blueprint.run(messages):
            # Print full response to stderr for debugging
            print(f"DEBUG: Full response object: {json.dumps(response, indent=2)}", file=sys.stderr)

            try:
                content = "Unexpected response format."
                if isinstance(response, dict):
                    if "choices" in response and isinstance(response["choices"], list) and len(response["choices"]) > 0:
                        choice = response["choices"][0]
                        if "message" in choice and isinstance(choice["message"], dict) and "content" in choice["message"]:
                            content = choice["message"]["content"]
                        elif "text" in choice:  # Fallback for older OpenAI API or simpler models
                            content = choice["text"]
                    elif "message" in response and isinstance(response["message"], dict) and "content" in response["message"]:
                        content = response["message"]["content"]  # Direct message content
                    else:
                        content = str(response)  # Fallback to string representation of dict
                else:
                    content = str(response)  # Fallback to string representation for non-dict responses
            except (KeyError, TypeError) as e:
                content = f"Error processing response: {e}. Full response: {response}"
                print(f"DEBUG: Error in run_echocraft_cli: {content}", file=sys.stderr)
            all_results.append(content)
    finally:
        spinner.stop()
    print_operation_box(
        op_type="EchoCraft Output",
        results=all_results,
        params={"prompt": messages[0].get("content") if messages and isinstance(messages, list) else ""},
        result_type="echo"
    )

if __name__ == "__main__":
    import asyncio
    print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   🗣️ ECHOCRAFT: MESSAGE MIRROR & SWARM UX DEMO              ║\n╠══════════════════════════════════════════════════════════════╣\n║ This blueprint echoes user messages, demonstrates swarm UX,  ║\n║ and showcases viral docstring propagation.                   ║\n║ Try running: python blueprint_echocraft.py                   ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")
    messages = [
        {"role": "user", "content": "Show me how EchoCraft mirrors messages and benefits from swarm UX patterns."}
    ]
    blueprint = EchoCraftBlueprint(blueprint_id="demo-1")
    asyncio.run(run_echocraft_cli(blueprint, messages))