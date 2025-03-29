"""
Gotchaman: CLI Automation Blueprint

This blueprint provides CLI automation capabilities using a team of agents:
- Ken (Coordinator)
- Joe (Runner - executes commands/file ops)
- Jun (Logger - hypothetical monitoring via MCP)
- Jinpei (Advisor - hypothetical suggestion via MCP)
- Ryu (Reviewer - hypothetical insights via MCP)

Uses BlueprintBase, @function_tool for local commands, and agent-as-tool delegation.
"""

import os
import sys
import logging
import subprocess
import shlex # For safe command splitting
from pathlib import Path # Use pathlib
from typing import Dict, Any, List, ClassVar, Optional

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

try:
    from agents import Agent, Tool, function_tool, Runner
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed in GotchamanBlueprint: {e}. Check dependencies.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Function Tools ---
@function_tool
def execute_command(command: str) -> str:
    """Executes a shell command and returns its stdout and stderr."""
    if not command: return "Error: No command provided."
    logger.info(f"Tool: Executing command: {command}")
    try:
        # Use shell=True cautiously, consider splitting if possible for safer execution
        result = subprocess.run(
            command,
            shell=True, # Be cautious with shell=True
            check=False, # Capture output even on error
            capture_output=True,
            text=True,
            timeout=120
        )
        output = f"Exit Code: {result.returncode}\nSTDOUT:\n{result.stdout.strip()}\nSTDERR:\n{result.stderr.strip()}"
        if result.returncode == 0:
            logger.debug(f"Command successful:\n{output}")
            return f"OK: Command executed.\n{output}"
        else:
            logger.error(f"Command failed:\n{output}")
            return f"Error: Command failed.\n{output}"
    except FileNotFoundError:
         # This error is less likely with shell=True unless the shell itself is missing
         logger.error(f"Error executing command '{command}': Shell or command not found.")
         return f"Error: Shell or command '{command.split()[0]}' not found."
    except subprocess.TimeoutExpired:
        logger.error(f"Command '{command}' timed out.")
        return f"Error: Command '{command}' timed out."
    except Exception as e:
        logger.error(f"Unexpected error executing command '{command}': {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error: Unexpected error during command execution: {e}"

@function_tool
def read_file(path: str) -> str:
    """Reads the content of a file at the specified path."""
    if not path: return "Error: No file path provided."
    logger.info(f"Tool: Reading file at: {path}")
    try:
        file_path = Path(path).resolve()
        # Optional: Add security check to ensure path is within allowed bounds if needed
        # cwd = Path.cwd()
        # if not str(file_path).startswith(str(cwd)):
        #     logger.warning(f"Attempt to read file outside current working directory: {path}")
        #     return f"Error: Access denied to path: {path}"
        if not file_path.is_file():
             logger.error(f"File not found at: {file_path}")
             return f"Error: File not found at path: {path}"
        content = file_path.read_text(encoding="utf-8")
        logger.debug(f"Read {len(content)} characters from {file_path}.")
        return f"OK: Content of {path}:\n{content}"
    except Exception as e:
        logger.error(f"Error reading file at {path}: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error reading file '{path}': {e}"

@function_tool
def write_file(path: str, content: str) -> str:
    """Writes content to a file at the specified path, overwriting if it exists."""
    if not path: return "Error: No file path provided."
    logger.info(f"Tool: Writing {len(content)} characters to file at: {path}")
    try:
        file_path = Path(path).resolve()
        # Optional: Add security check
        # cwd = Path.cwd()
        # if not str(file_path).startswith(str(cwd)):
        #     logger.warning(f"Attempt to write file outside current working directory: {path}")
        #     return f"Error: Access denied to path: {path}"

        file_path.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists
        file_path.write_text(content, encoding="utf-8")
        logger.debug(f"Successfully wrote to {file_path}.")
        return f"OK: Successfully wrote to {path}."
    except Exception as e:
        logger.error(f"Error writing file at {path}: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error writing file '{path}': {e}"

# --- Define the Blueprint ---
class GotchamanBlueprint(BlueprintBase):
    """Gotchaman: CLI Automation Blueprint using BlueprintBase."""

    metadata: ClassVar[Dict[str, Any]] = {
        "name": "GotchamanBlueprint",
        "title": "Gotchaman: CLI Automation",
        "description": (
            "A blueprint for automating CLI tasks using a team of agents (Ken, Joe, Jun, Jinpei, Ryu) "
            "with specific roles and MCP/tool access."
        ),
        "version": "1.1.0", # Refactored version
        "author": "Open Swarm Team (Refactored)",
        "tags": ["cli", "automation", "multi-agent", "mcp", "slack", "monday"],
        # List only servers directly used by refactored agents
        "required_mcp_servers": ["slack", "mondayDotCom", "basic-memory", "mcp-npx-fetch"],
        "env_vars": ["SLACK_API_KEY", "MONDAY_API_KEY"]
    }

     # Caches
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    # --- Model Instantiation Helper --- (Standard helper)
    def _get_model_instance(self, profile_name: str) -> Model:
        """Retrieves or creates an LLM Model instance."""
        # ... (Implementation is the same as previous refactors) ...
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]
        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = self.get_llm_profile(profile_name)
        if not profile_data: raise ValueError(f"Missing LLM profile '{profile_name}'.")
        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name: raise ValueError(f"Missing 'model' in profile '{profile_name}'.")
        if provider != "openai": raise ValueError(f"Unsupported provider: {provider}")
        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
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
        """Creates the Gotchaman agent team and returns Ken (Coordinator)."""
        logger.debug("Creating Gotchaman agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for Gotchaman agents.")
        model_instance = self._get_model_instance(default_profile_name)

        # Helper to filter MCP servers
        def get_agent_mcps(names: List[str]) -> List[MCPServer]:
            return [s for s in mcp_servers if s.name in names]

        # --- Agent Instructions ---
        ken_instructions = "You are Ken, the Coordinator for Gotchaman team. Your team: Joe (Runner), Jun (Logger), Jinpei (Advisor), and Ryu (Reviewer). Analyze the user request and delegate tasks to the appropriate agent using their Agent Tool. Synthesize their responses for the final output."
        joe_instructions = "You are Joe, the Runner. Execute shell commands, read files, or write files using your function tools (`execute_command`, `read_file`, `write_file`) as requested by Ken. Report the outcome."
        jun_instructions = "You are Jun, the Logger. Receive information or instructions from Ken. Use the `slack` MCP tool to log messages or feedback to a designated channel (details provided by Ken or pre-configured). Report success/failure of logging back to Ken."
        jinpei_instructions = "You are Jinpei, the Advisor. Receive context from Ken. Use the `mcp-npx-fetch` MCP tool to fetch relevant documentation or examples based on the context. Provide concise suggestions or relevant snippets back to Ken."
        ryu_instructions = "You are Ryu, the Reviewer. Receive outputs or code snippets from Ken. Use the `basic-memory` MCP tool to recall previous related outputs or guidelines if necessary. Provide insightful review comments or quality checks back to Ken."

        # Instantiate agents
        joe_agent = Agent(
            name="Joe", model=model_instance, instructions=joe_instructions,
            tools=[execute_command, read_file, write_file], # Joe has the function tools
            mcp_servers=[] # Joe doesn't directly use MCPs listed
        )
        jun_agent = Agent(
            name="Jun", model=model_instance, instructions=jun_instructions,
            tools=[], # Jun uses MCP
            mcp_servers=get_agent_mcps(["slack"])
        )
        jinpei_agent = Agent(
            name="Jinpei", model=model_instance, instructions=jinpei_instructions,
            tools=[], # Jinpei uses MCP
            mcp_servers=get_agent_mcps(["mcp-npx-fetch"])
        )
        ryu_agent = Agent(
            name="Ryu", model=model_instance, instructions=ryu_instructions,
            tools=[], # Ryu uses MCP
            mcp_servers=get_agent_mcps(["basic-memory"])
        )
        # Coordinator - Ken
        ken_agent = Agent(
            name="Ken", model=model_instance, instructions=ken_instructions,
            tools=[ # Ken delegates to others via agent tools
                joe_agent.as_tool(tool_name="Joe", tool_description="Delegate command execution or file operations to Joe."),
                jun_agent.as_tool(tool_name="Jun", tool_description="Delegate logging tasks via Slack to Jun."),
                jinpei_agent.as_tool(tool_name="Jinpei", tool_description="Delegate fetching docs/examples to Jinpei."),
                ryu_agent.as_tool(tool_name="Ryu", tool_description="Delegate review tasks or recall past info via Ryu."),
            ],
             # Ken might use memory directly, or coordinate access via Ryu? Assigning for potential direct use.
            mcp_servers=get_agent_mcps(["basic-memory"])
        )

        logger.debug("Gotchaman agents created. Starting with Ken.")
        return ken_agent

# Standard Python entry point
if __name__ == "__main__":
    GotchamanBlueprint.main()
