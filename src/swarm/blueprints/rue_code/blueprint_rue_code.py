import logging
import os
import sys
import json
import subprocess
from typing import Dict, List, Any, AsyncGenerator, Optional
from pathlib import Path
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Attempt to import BlueprintBase, handle potential ImportError during early setup/testing
try:
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
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
    logger.info(f"Reading file: {file_path}")
    try:
        # Basic path traversal check (can be enhanced)
        if ".." in file_path:
             logger.warning(f"Attempted path traversal detected in read_file: {file_path}")
             return "Error: Invalid file path (potential traversal)."
        # Consider restricting base path if needed
        # base_path = Path("/workspace").resolve()
        # target_path = (base_path / file_path).resolve()
        # if not target_path.is_relative_to(base_path):
        #     return "Error: Access denied."

        path = Path(file_path)
        if not path.is_file():
            return f"Error: File not found at {file_path}"
        content = path.read_text(encoding='utf-8')
        logger.info(f"Successfully read {len(content)} characters from {file_path}")
        # Truncate long files?
        max_len = 10000
        if len(content) > max_len:
             logger.warning(f"File {file_path} truncated to {max_len} characters.")
             return content[:max_len] + "\n... [File Truncated]"
        return content
    except Exception as e:
        logger.error(f"Error reading file '{file_path}': {e}", exc_info=True)
        return f"Error reading file: {e}"

def write_file(file_path: str, content: str) -> str:
    """Writes content to a specified file, creating directories if needed."""
    logger.info(f"Writing to file: {file_path}")
    try:
        # Basic path traversal check
        if ".." in file_path:
             logger.warning(f"Attempted path traversal detected in write_file: {file_path}")
             return "Error: Invalid file path (potential traversal)."
        # Consider restricting base path

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        logger.info(f"Successfully wrote {len(content)} characters to {file_path}")
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        logger.error(f"Error writing file '{file_path}': {e}", exc_info=True)
        return f"Error writing file: {e}"

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

# --- RueCodeBlueprint Definition ---

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

    # Override __init__ if you need specific setup beyond the base class
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     # Add any RueCode specific initialization here
    #     logger.info("RueCodeBlueprint initialized.")

    async def run(self, messages: List[Dict[str, str]]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Processes user requests for code generation, execution, or file operations.
        """
        logger.info(f"RueCodeBlueprint run called with {len(messages)} messages.")
        last_user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), None)

        if not last_user_message:
            yield {"messages": [{"role": "assistant", "content": "I need a user message to proceed."}]}
            return

        # 1. Prepare the prompt using Jinja (example)
        # Assuming you have a 'rue_code_prompt.j2' in a 'templates' subdir
        try:
            prompt_context = {
                "user_request": last_user_message,
                "history": messages[:-1], # Provide previous messages for context
                "available_tools": ["execute_shell_command", "read_file", "write_file", "list_files"]
            }
            rendered_prompt = self.render_prompt("rue_code_prompt.j2", prompt_context)
            logger.debug(f"Rendered prompt:\n{rendered_prompt}")
        except Exception as e:
            logger.error(f"Failed to render prompt template: {e}")
            yield {"messages": [{"role": "assistant", "content": f"Internal error: Could not prepare request ({e})."}]}
            return

        # 2. Define available tools for the LLM
        tools = [
            {"type": "function", "function": {"name": "execute_shell_command", "description": "Executes a shell command.", "parameters": {"type": "object", "properties": {"command": {"type": "string", "description": "The shell command to execute."}}, "required": ["command"]}}},
            {"type": "function", "function": {"name": "read_file", "description": "Reads content from a file.", "parameters": {"type": "object", "properties": {"file_path": {"type": "string", "description": "Path to the file to read."}}, "required": ["file_path"]}}},
            {"type": "function", "function": {"name": "write_file", "description": "Writes content to a file.", "parameters": {"type": "object", "properties": {"file_path": {"type": "string", "description": "Path to the file to write."}, "content": {"type": "string", "description": "Content to write."}}, "required": ["file_path", "content"]}}},
            {"type": "function", "function": {"name": "list_files", "description": "Lists files in a directory.", "parameters": {"type": "object", "properties": {"directory_path": {"type": "string", "description": "Path to the directory (default is current)."}}, "required": []}}}, # directory_path is optional
        ]
        tool_map = {
            "execute_shell_command": execute_shell_command,
            "read_file": read_file,
            "write_file": write_file,
            "list_files": list_files,
        }

        # 3. Call the LLM (using the base class's llm instance)
        llm_messages = [{"role": "system", "content": rendered_prompt}] # Or construct differently based on template
        # Add user message if not fully incorporated into the system prompt
        # llm_messages.append({"role": "user", "content": last_user_message})

        logger.info(f"Calling LLM profile '{self.llm_profile_name}' with tools.")
        try:
            # Use the configured LLM instance from the base class
            response_stream = self.llm.chat_completion_stream(
                messages=llm_messages,
                tools=tools,
                tool_choice="auto" # Let the model decide
            )

            # 4. Process the streaming response and handle tool calls
            full_response_content = ""
            tool_calls = []
            async for chunk in response_stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_response_content += delta.content
                    yield {"messages": [{"role": "assistant", "delta": {"content": delta.content}}]} # Yield content delta

                if delta.tool_calls:
                    # Accumulate tool call information from deltas
                    for tc_delta in delta.tool_calls:
                        if tc_delta.index >= len(tool_calls):
                            # Start of a new tool call
                            tool_calls.append({
                                "id": tc_delta.id,
                                "type": "function",
                                "function": {"name": tc_delta.function.name, "arguments": tc_delta.function.arguments}
                            })
                        else:
                            # Append arguments to existing tool call
                            tool_calls[tc_delta.index]["function"]["arguments"] += tc_delta.function.arguments

            logger.info("LLM response received.")
            # If no tool calls, the final response is just the accumulated content
            if not tool_calls and not full_response_content:
                 logger.warning("LLM finished without content or tool calls.")
                 yield {"messages": [{"role": "assistant", "content": "[No response content or tool call generated]"}]}


            # 5. Execute tool calls if any were made
            if tool_calls:
                logger.info(f"Executing {len(tool_calls)} tool call(s)...")
                tool_messages = [{"role": "assistant", "tool_calls": tool_calls}] # Message for next LLM call

                for tool_call in tool_calls:
                    function_name = tool_call["function"]["name"]
                    tool_call_id = tool_call["id"]
                    logger.debug(f"Processing tool call: {function_name} (ID: {tool_call_id})")

                    if function_name in tool_map:
                        try:
                            arguments = json.loads(tool_call["function"]["arguments"])
                            logger.debug(f"Arguments: {arguments}")
                            tool_function = tool_map[function_name]
                            # Execute the tool function (sync for now, consider async if tools are I/O bound)
                            tool_output = tool_function(**arguments)
                            logger.debug(f"Tool output: {tool_output[:200]}...") # Log truncated output
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode arguments for {function_name}: {tool_call['function']['arguments']}")
                            tool_output = f"Error: Invalid arguments format for {function_name}."
                        except Exception as e:
                            logger.error(f"Error executing tool {function_name}: {e}", exc_info=True)
                            tool_output = f"Error executing tool {function_name}: {e}"

                        tool_messages.append({
                            "tool_call_id": tool_call_id,
                            "role": "tool",
                            "name": function_name,
                            "content": tool_output,
                        })
                    else:
                        logger.warning(f"LLM requested unknown tool: {function_name}")
                        tool_messages.append({
                            "tool_call_id": tool_call_id,
                            "role": "tool",
                            "name": function_name,
                            "content": f"Error: Tool '{function_name}' not found.",
                        })

                # 6. Send tool results back to LLM for final response
                logger.info("Sending tool results back to LLM...")
                final_response_stream = self.llm.chat_completion_stream(
                    messages=llm_messages + tool_messages # Original messages + tool req + tool resp
                )
                async for final_chunk in final_response_stream:
                     if final_chunk.choices[0].delta.content:
                         yield {"messages": [{"role": "assistant", "delta": {"content": final_chunk.choices[0].delta.content}}]}

        except Exception as e:
            logger.error(f"Error during RueCodeBlueprint run: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}

        logger.info("RueCodeBlueprint run finished.")

