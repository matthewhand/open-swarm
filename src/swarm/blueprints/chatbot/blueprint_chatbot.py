import os
from dotenv import load_dotenv; load_dotenv(override=True)

import logging
import os
import sys
from typing import Dict, Any, List, ClassVar, Optional
import argparse

# Set logging to WARNING by default unless SWARM_DEBUG=1
if not os.environ.get("SWARM_DEBUG"):
    logging.basicConfig(level=logging.WARNING)
else:
    logging.basicConfig(level=logging.DEBUG)

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

from agents import Agent, function_tool
from agents.mcp import MCPServer
from agents.models.interface import Model
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from swarm.core.blueprint_base import BlueprintBase
from swarm.core.blueprint_ux import BlueprintUXImproved
from agents import Runner

logger = logging.getLogger(__name__)

# --- Define the Blueprint ---
class ChatbotBlueprint(BlueprintBase):
    def __init__(self, blueprint_id: str = "chatbot", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self.ux = BlueprintUXImproved(style="serious")
        class DummyLLM:
            def chat_completion_stream(self, messages, **_):
                class DummyStream:
                    def __aiter__(self): return self
                    async def __anext__(self):
                        raise StopAsyncIteration
                return DummyStream()
        self.llm = DummyLLM()

        # Remove redundant client instantiation; rely on framework-level default client
        # (No need to re-instantiate AsyncOpenAI or set_default_openai_client)
        # All blueprints now use the default client set at framework init

    """A simple conversational chatbot agent."""
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "ChatbotBlueprint",
        "title": "Simple Chatbot",
        "description": "A basic conversational agent that responds to user input.",
        "version": "1.1.0", # Refactored version
        "author": "Open Swarm Team (Refactored)",
        "tags": ["chatbot", "conversation", "simple"],
        "required_mcp_servers": [],
        "env_vars": [],
    }

    # Caches
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    @function_tool
    def read_file(path: str) -> str:
        try:
            with open(path, 'r') as f:
                return f.read()
        except Exception as e:
            return f"ERROR: {e}"

    @function_tool
    def write_file(path: str, content: str) -> str:
        try:
            with open(path, 'w') as f:
                f.write(content)
            return "OK: file written"
        except Exception as e:
            return f"ERROR: {e}"

    @function_tool
    def list_files(directory: str = '.') -> str:
        try:
            return '\n'.join(os.listdir(directory))
        except Exception as e:
            return f"ERROR: {e}"

    @function_tool
    def execute_shell_command(command: str) -> str:
        import subprocess
        import os
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Executing shell command: {command}")
        try:
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

    # --- Model Instantiation Helper --- (Standard helper)
    def _get_model_instance(self, profile_name: str) -> Model:
        """Retrieves or creates an LLM Model instance, respecting LITELLM_MODEL/DEFAULT_LLM if set."""
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]
        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = self.get_llm_profile(profile_name)
        # Patch: Respect LITELLM_MODEL/DEFAULT_LLM env vars
        import os
        model_name = os.getenv("LITELLM_MODEL") or os.getenv("DEFAULT_LLM") or profile_data.get("model")
        profile_data["model"] = model_name
        if profile_data.get("provider", "openai").lower() != "openai": raise ValueError(f"Unsupported provider: {profile_data.get('provider')}")
        if not model_name: raise ValueError(f"Missing 'model' in profile '{profile_name}'.")

        # REMOVE PATCH: env expansion is now handled globally in config loader
        client_cache_key = f"{profile_data.get('provider', 'openai')}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_kwargs = {k:v for k,v in filtered_kwargs.items() if k != 'api_key'}
             logger.debug(f"Creating new AsyncOpenAI client for '{profile_name}': {log_kwargs}")
             try: self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_kwargs)
             except Exception as e: raise ValueError(f"Failed to init client: {e}") from e
        client = self._openai_client_cache[client_cache_key]
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e: raise ValueError(f"Failed to init LLM: {e}") from e

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the single Chatbot agent."""
        logger.debug("Creating Chatbot agent...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for Chatbot.")
        model_instance = self._get_model_instance(default_profile_name)

        chatbot_instructions = """
You are a helpful and friendly chatbot. Respond directly to the user's input in a conversational manner.\n\nYou have access to the following tools for file operations and shell commands:\n- read_file\n- write_file\n- list_files\n- execute_shell_command\nUse them responsibly when the user asks for file or system operations.
"""

        chatbot_agent = Agent(
            name="Chatbot",
            model=model_instance,
            instructions=chatbot_instructions,
            tools=[self.read_file, self.write_file, self.list_files, self.execute_shell_command],
            mcp_servers=mcp_servers # Pass along, though likely unused
        )

        logger.debug("Chatbot agent created.")
        return chatbot_agent

    async def run(self, messages: List[Dict[str, Any]], **kwargs):
        """Main execution entry point for the Chatbot blueprint."""
        logger.info("ChatbotBlueprint run method called.")
        instruction = messages[-1].get("content", "") if messages else ""
        from agents import Runner
        spinner_idx = 0
        start_time = time.time()
        spinner_yield_interval = 1.0  # seconds
        last_spinner_time = start_time
        yielded_spinner = False
        result_chunks = []
        try:
            runner_gen = Runner.run(self.create_starting_agent([]), instruction)
            while True:
                now = time.time()
                try:
                    chunk = next(runner_gen)
                    result_chunks.append(chunk)
                    # If chunk is a final result, wrap and yield
                    if chunk and isinstance(chunk, dict) and "messages" in chunk:
                        content = chunk["messages"][0]["content"] if chunk["messages"] else ""
                        summary = self.ux.summary("Operation", len(result_chunks), {"instruction": instruction[:40]})
                        box = self.ux.ansi_emoji_box(
                            title="Chatbot Result",
                            content=content,
                            summary=summary,
                            params={"instruction": instruction[:40]},
                            result_count=len(result_chunks),
                            op_type="run",
                            status="success"
                        )
                        yield {"messages": [{"role": "assistant", "content": box}]}
                    else:
                        yield chunk
                    yielded_spinner = False
                except StopIteration:
                    break
                except Exception:
                    if now - last_spinner_time >= spinner_yield_interval:
                        taking_long = (now - start_time > 10)
                        spinner_msg = self.ux.spinner(spinner_idx, taking_long=taking_long)
                        yield {"messages": [{"role": "assistant", "content": spinner_msg}]}
                        spinner_idx += 1
                        last_spinner_time = now
                        yielded_spinner = True
            if not result_chunks and not yielded_spinner:
                yield {"messages": [{"role": "assistant", "content": self.ux.spinner(0)}]}
        except Exception as e:
            logger.error(f"Error during Chatbot run: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}

# --- Spinner and ANSI/emoji operation box for unified UX ---
from swarm.ux.ansi_box import ansi_box
from rich.console import Console
from rich.style import Style
from rich.text import Text
import threading
import time

class ChatbotSpinner:
    FRAMES = [
        "Generating.", "Generating..", "Generating...", "Running...",
        "⠋ Generating...", "⠙ Generating...", "⠹ Generating...", "⠸ Generating...",
        "⠼ Generating...", "⠴ Generating...", "⠦ Generating...", "⠧ Generating...",
        "⠇ Generating...", "⠏ Generating...", "🤖 Generating...", "💡 Generating...", "✨ Generating..."
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
        self._thread = threading.Thread(target=self._spin, daemon=True)
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

def print_operation_box(op_type, results, params=None, result_type="chat", taking_long=False):
    emoji = "💬" if result_type == "chat" else "🔍"
    style = 'success' if result_type == "chat" else 'default'
    box_title = op_type if op_type else ("Chatbot Output" if result_type == "chat" else "Results")
    summary_lines = []
    count = len(results) if isinstance(results, list) else 0
    summary_lines.append(f"Results: {count}")
    if params:
        for k, v in params.items():
            summary_lines.append(f"{k.capitalize()}: {v}")
    box_content = "\n".join(summary_lines + ["\n".join(map(str, results))])
    ansi_box(box_title, box_content, count=count, params=params, style=style if not taking_long else 'warning', emoji=emoji)

# Standard Python entry point
if __name__ == "__main__":
    import sys
    import asyncio
    # --- AUTO-PYTHONPATH PATCH FOR AGENTS ---
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    if '--instruction' in sys.argv:
        instruction = sys.argv[sys.argv.index('--instruction') + 1]
    else:
        print("Interactive mode not supported in this script.")
        sys.exit(1)

    blueprint = ChatbotBlueprint(blueprint_id="chatbot")
    async def runner():
        spinner = ChatbotSpinner()
        spinner.start()
        try:
            all_results = []
            async for chunk in blueprint._run_non_interactive(instruction):
                msg = chunk["messages"][0]["content"]
                if not msg.startswith("An error occurred:"):
                    all_results.append(msg)
        finally:
            spinner.stop()
        print_operation_box(
            op_type="Chatbot Output",
            results=all_results,
            params={"instruction": instruction},
            result_type="chat"
        )
    asyncio.run(runner())
