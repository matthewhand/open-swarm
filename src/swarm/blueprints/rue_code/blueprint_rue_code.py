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
from typing import Dict, List, Any, AsyncGenerator, Optional
from pathlib import Path
import re
from datetime import datetime
import pytz
from swarm.core.blueprint_ux import BlueprintUX

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

# Attempt to import BlueprintBase, handle potential ImportError during early setup/testing
try:
    from swarm.core.blueprint_base import BlueprintBase
except ImportError as e:
    logger.error(f"Import failed: {e}. Check 'openai-agents' install and project structure.")
    # *** REMOVED sys.exit(1) ***
    # Define a dummy class if import fails, allowing module to load for inspection/debugging
    class BlueprintBase:
        metadata = {}
        def __init__(self, *args, **kwargs): pass
        async def run(self, *args, **kwargs): yield {}

# --- Tool Definitions ---

def execute_shell_command(command: str) -> str:
    """
    Executes a shell command and returns its stdout and stderr.
    Security Note: Ensure commands are properly sanitized or restricted.
    """
    logger.info(f"Executing shell command: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=False, # Don't raise exception on non-zero exit code
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60 # Add a timeout
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
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        logger.error(f"Error executing command '{command}': {e}", exc_info=True)
        return f"Error executing command: {e}"

def read_file(file_path: str) -> str:
    """Reads the content of a specified file."""
    logger.info(f"📄 Reading file: {file_path}")
    try:
        if ".." in file_path:
            logger.warning(f"Attempted path traversal detected in read_file: {file_path}")
            return "\033[91m❌ Error: Invalid file path (potential traversal).\033[0m"
        path = Path(file_path)
        if not path.is_file():
            logger.warning(f"File not found: {file_path}")
            return f"\033[91m❌ Error: File not found at {file_path}\033[0m"
        content = path.read_text(encoding='utf-8')
        logger.info(f"Successfully read {len(content)} characters from {file_path}")
        max_len = 10000
        if len(content) > max_len:
            logger.warning(f"File {file_path} truncated to {max_len} characters.")
            return f"\033[93m⚠️ {content[:max_len]}\n... [File Truncated]\033[0m"
        return f"\033[92m✅ File read successfully!\033[0m\n\033[94m{content}\033[0m"
    except Exception as e:
        logger.error(f"Error reading file '{file_path}': {e}", exc_info=True)
        return f"\033[91m❌ Error reading file: {e}\033[0m"

def write_file(file_path: str, content: str) -> str:
    """Writes content to a specified file, creating directories if needed."""
    logger.info(f"✏️ Writing to file: {file_path}")
    try:
        if ".." in file_path:
            logger.warning(f"Attempted path traversal detected in write_file: {file_path}")
            return "\033[91m❌ Error: Invalid file path (potential traversal).\033[0m"
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        logger.info(f"Successfully wrote {len(content)} characters to {file_path}")
        return f"\033[92m✅ Successfully wrote to {file_path}\033[0m"
    except Exception as e:
        logger.error(f"Error writing file '{file_path}': {e}", exc_info=True)
        return f"\033[91m❌ Error writing file: {e}\033[0m"

def list_files(directory_path: str = ".") -> str:
    """Lists files and directories in a specified path."""
    logger.info(f"Listing files in directory: {directory_path}")
    try:
        # Basic path traversal check
        if ".." in directory_path:
             logger.warning(f"Attempted path traversal detected in list_files: {directory_path}")
             return "Error: Invalid directory path (potential traversal)."
        # Consider restricting base path

        path = Path(directory_path)
        if not path.is_dir():
            return f"Error: Directory not found at {directory_path}"

        entries = []
        for entry in path.iterdir():
            entry_type = "d" if entry.is_dir() else "f"
            entries.append(f"{entry_type} {entry.name}")

        logger.info(f"Found {len(entries)} entries in {directory_path}")
        return "\n".join(entries) if entries else "Directory is empty."
    except Exception as e:
        logger.error(f"Error listing files in '{directory_path}': {e}", exc_info=True)
        return f"Error listing files: {e}"

# --- FileOps Tool Logic Definitions ---
def read_file_fileops(path: str) -> str:
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"
def write_file_fileops(path: str, content: str) -> str:
    try:
        with open(path, 'w') as f:
            f.write(content)
        return "OK: file written"
    except Exception as e:
        return f"ERROR: {e}"
def list_files_fileops(directory: str = '.') -> str:
    try:
        return '\n'.join(os.listdir(directory))
    except Exception as e:
        return f"ERROR: {e}"
def execute_shell_command_fileops(command: str) -> str:
    import subprocess
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout + result.stderr
    except Exception as e:
        return f"ERROR: {e}"

# --- RueCodeBlueprint Definition ---

# === OpenAI GPT-4.1 Prompt Engineering Guide ===
# See: https://github.com/openai/openai-cookbook/blob/main/examples/gpt4-1_prompting_guide.ipynb
#
# Agentic System Prompt Example (recommended for code generation/repair agents):
SYS_PROMPT_AGENTIC = """
You are an agent - please keep going until the user’s query is completely resolved, before ending your turn and yielding back to the user. Only terminate your turn when you are sure that the problem is solved.
If you are not sure about file content or codebase structure pertaining to the user’s request, use your tools to read files and gather the relevant information: do NOT guess or make up an answer.
You MUST plan extensively before each function call, and reflect extensively on the outcomes of the previous function calls. DO NOT do this entire process by making function calls only, as this can impair your ability to solve the problem and think insightfully.
"""

class RueCodeBlueprint(BlueprintBase):
    """
    A blueprint designed for code generation, execution, and file system interaction.
    Uses Jinja2 for templating prompts and provides tools for shell commands and file operations.
    """
    metadata = {
        "name": "RueCode",
        "description": "Generates, executes code, and interacts with the file system.",
        "author": "Matthew Hand",
        "version": "0.1.0",
        "tags": ["code", "execution", "filesystem", "developer"],
        "llm_profile": "default_dev" # Example: Suggests a profile suitable for coding
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Minimal LLM stub for demo
        class DummyLLM:
            def chat_completion_stream(self, messages, **_):
                class DummyStream:
                    def __aiter__(self): return self
                    async def __anext__(self):
                        raise StopAsyncIteration
                return DummyStream()
        self.llm = DummyLLM()
        # Use silly style for RueCode
        self.ux = BlueprintUX(style="silly")

    def render_prompt(self, template_name: str, context: dict) -> str:
        # Minimal fallback: just format the user request directly for now
        # (No Jinja2 dependency, just a stub for demo)
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

    async def run(self, messages: List[Dict[str, str]]):
        logger.info("RueCodeBlueprint run method called.")
        last_user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), None)
        if not last_user_message:
            yield {"messages": [{"role": "assistant", "content": self.ux.box("Error", "I need a user message to proceed.")}]}
            return
        prompt_context = {
            "user_request": last_user_message,
            "history": messages[:-1],
            "available_tools": ["rue_code"]
        }
        rendered_prompt = self.render_prompt("rue_code_prompt.j2", prompt_context)
        # Spinner demo: cycle through a few states, then fallback
        import asyncio
        for i in range(4):
            yield {"messages": [{"role": "assistant", "content": self.ux.box("RueCode", self.ux.spinner(i), summary="Preparing to process", params=prompt_context["user_request"])}]}
            await asyncio.sleep(0.2)
        yield {"messages": [{"role": "assistant", "content": self.ux.box("RueCode", self.ux.spinner(0, taking_long=True), summary="Still working", params=prompt_context["user_request"])}]}
        # Simulate code vs semantic search distinction
        code_results = ["def foo(): ...", "def bar(): ..."]
        semantic_results = ["This function sorts a list.", "This function calculates a sum."]
        yield {"messages": [{"role": "assistant", "content": self.ux.box(
            "RueCode Results",
            self.ux.code_vs_semantic("code", code_results) + "\n" + self.ux.code_vs_semantic("semantic", semantic_results),
            summary=self.ux.summary("Analyzed codebase", 4, prompt_context["user_request"]),
            result_count=4,
            params=prompt_context["user_request"]
        )}]}
        logger.info("RueCodeBlueprint run finished.")
        return

    def create_starting_agent(self, mcp_servers):
        read_file_tool = PatchedFunctionTool(read_file_fileops, 'read_file')
        write_file_tool = PatchedFunctionTool(write_file_fileops, 'write_file')
        list_files_tool = PatchedFunctionTool(list_files_fileops, 'list_files')
        execute_shell_command_tool = PatchedFunctionTool(execute_shell_command_fileops, 'execute_shell_command')
        rue_agent = self.make_agent(
            name="RueCodeAgent",
            instructions="You are RueCodeAgent. You can use fileops tools (read_file, write_file, list_files, execute_shell_command) for any file or shell tasks.",
            tools=[read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool],
            mcp_servers=mcp_servers
        )
        return rue_agent

if __name__ == "__main__":
    import asyncio
    import json
    print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   📝 RUE CODE: SWARM TEMPLATING & EXECUTION DEMO             ║\n╠══════════════════════════════════════════════════════════════╣\n║ This blueprint demonstrates viral doc propagation,           ║\n║ code templating, and swarm-powered execution.                ║\n║ Try running: python blueprint_rue_code.py                    ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")
    messages = [
        {"role": "user", "content": "Show me how Rue Code does templating and swarm execution."}
    ]
    blueprint = RueCodeBlueprint(blueprint_id="demo-1")
    async def run_and_print():
        async for response in blueprint.run(messages):
            print(json.dumps(response, indent=2))
    asyncio.run(run_and_print())
