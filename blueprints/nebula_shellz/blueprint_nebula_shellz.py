import logging
import os
import sys
import asyncio
import subprocess
import re
import inspect
from typing import Dict, Any, List, Optional, ClassVar

try:
    from agents import Agent, Tool, function_tool
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
    from rich.panel import Panel # Import Panel for splash screen
except ImportError as e:
    print(f"ERROR: Import failed in nebula_shellz: {e}. Ensure 'openai-agents' install and structure.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Tool Definitions (Unchanged) ---
@function_tool
async def code_review(code_snippet: str) -> str:
    """Performs a review of the provided code snippet."""
    logger.info(f"Reviewing code snippet: {code_snippet[:50]}...")
    await asyncio.sleep(0.1); issues = []; ("TODO" in code_snippet and issues.append("Found TODO.")); (len(code_snippet.splitlines()) > 100 and issues.append("Code long.")); return "Review: " + " ".join(issues) if issues else "Code looks good!"
@function_tool
def generate_documentation(code_snippet: str) -> str:
    """Generates basic documentation string for the provided code snippet."""
    logger.info(f"Generating documentation for: {code_snippet[:50]}...")
    first_line = code_snippet.splitlines()[0] if code_snippet else "N/A"; doc = f"/**\n * This code snippet starts with: {first_line}...\n * TODO: Add more detailed documentation.\n */"; logger.debug(f"Generated documentation:\n{doc}"); return doc
@function_tool
def execute_shell_command(command: str) -> str:
    """Executes a shell command and returns its stdout and stderr."""
    logger.info(f"Executing shell command: {command}")
    if not command: logger.warning("execute_shell_command called with empty command."); return "Error: No command provided."
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False, shell=True); output = f"Exit Code: {result.returncode}\nSTDOUT:\n{result.stdout.strip()}\nSTDERR:\n{result.stderr.strip()}"; logger.debug(f"Command '{command}' result:\n{output}"); return output
    except FileNotFoundError: cmd_base = command.split()[0] if command else ""; logger.error(f"Command not found: {cmd_base}"); return f"Error: Command not found - {cmd_base}"
    except subprocess.TimeoutExpired: logger.error(f"Command '{command}' timed out after 60 seconds."); return f"Error: Command '{command}' timed out."
    except Exception as e: logger.error(f"Error executing command '{command}': {e}", exc_info=logger.level <= logging.DEBUG); return f"Error executing command: {e}"

# --- Agent Definitions (Instructions remain the same) ---
morpheus_instructions = """
You are Morpheus, the leader... (Instructions as before) ...
"""
trinity_instructions = """
You are Trinity, the investigator... (Instructions as before) ...
"""
neo_instructions = """
You are Neo, the programmer... (Instructions as before) ...
"""
oracle_instructions = "You are the Oracle..."
cypher_instructions = "You are Cypher..."
tank_instructions = "You are Tank..."

# --- Blueprint Definition ---
class NebuchaShellzzarBlueprint(BlueprintBase):
    """A multi-agent blueprint inspired by The Matrix for sysadmin and coding tasks."""
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "NebulaShellzzarBlueprint", "title": "NebulaShellzzar",
        "description": "A multi-agent blueprint inspired by The Matrix for system administration and coding tasks.",
        "version": "1.0.0", "author": "Open Swarm Team",
        "tags": ["matrix", "multi-agent", "shell", "coding", "mcp"],
        "required_mcp_servers": ["memory"],
    }
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    # --- ADDED: Splash Screen ---
    def display_splash_screen(self):
        """Displays a Matrix-themed splash screen."""
        splash_text = """
[bold green]Wake up, Neo...[/]
[green]The Matrix has you...[/]
[bold green]Follow the white rabbit.[/]

Initializing NebulaShellzzar Crew...
        """
        panel = Panel(splash_text.strip(), title="[bold green]NebulaShellzzar[/]", border_style="green", expand=False)
        self.console.print(panel)
        self.console.print() # Add a blank line

    def _get_model_instance(self, profile_name: str) -> Model:
        """Gets or creates a Model instance for the given profile name."""
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]
        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = self.get_llm_profile(profile_name)
        if not profile_data:
             logger.critical(f"Cannot create Model instance: Profile '{profile_name}' (or default) not resolved.")
             raise ValueError(f"Missing LLM profile configuration for '{profile_name}' or 'default'.")
        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name:
             logger.critical(f"LLM profile '{profile_name}' is missing the 'model' key.")
             raise ValueError(f"Missing 'model' key in LLM profile '{profile_name}'.")
        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
        if provider == "openai":
            if client_cache_key not in self._openai_client_cache:
                 client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
                 filtered_client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
                 log_client_kwargs = {k:v for k,v in filtered_client_kwargs.items() if k != 'api_key'}
                 logger.debug(f"Creating new AsyncOpenAI client for profile '{profile_name}' with config: {log_client_kwargs}") # Changed to DEBUG
                 try: self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_client_kwargs)
                 except Exception as e:
                     logger.error(f"Failed to create AsyncOpenAI client for profile '{profile_name}': {e}", exc_info=True)
                     raise ValueError(f"Failed to initialize OpenAI client for profile '{profile_name}': {e}") from e
            openai_client_instance = self._openai_client_cache[client_cache_key]
            logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') with specific client instance.")
            try: model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=openai_client_instance)
            except Exception as e:
                 logger.error(f"Failed to instantiate OpenAIChatCompletionsModel for profile '{profile_name}': {e}", exc_info=True)
                 raise ValueError(f"Failed to initialize LLM provider for profile '{profile_name}': {e}") from e
        else:
            logger.error(f"Unsupported LLM provider '{provider}' in profile '{profile_name}'.")
            raise ValueError(f"Unsupported LLM provider: {provider}")
        self._model_instance_cache[profile_name] = model_instance
        return model_instance

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the Matrix-themed agent team with Morpheus as the coordinator."""
        logger.debug(f"Creating NebulaShellzzar agent team with {len(mcp_servers)} MCP server(s)...") # Changed to DEBUG
        self._model_instance_cache = {}
        self._openai_client_cache = {}
        default_profile_name = self.config.get("llm_profile", "default")
        default_model_instance = self._get_model_instance(default_profile_name)
        logger.debug(f"Using LLM profile '{default_profile_name}' for all agents.") # Changed to DEBUG

        neo = Agent(name="Neo", model=default_model_instance, instructions=neo_instructions, tools=[code_review, generate_documentation, execute_shell_command], mcp_servers=mcp_servers)
        trinity = Agent(name="Trinity", model=default_model_instance, instructions=trinity_instructions, tools=[execute_shell_command], mcp_servers=mcp_servers)
        oracle = Agent(name="Oracle", model=default_model_instance, instructions=oracle_instructions, tools=[])
        cypher = Agent(name="Cypher", model=default_model_instance, instructions=cypher_instructions, tools=[execute_shell_command])
        tank = Agent(name="Tank", model=default_model_instance, instructions=tank_instructions, tools=[execute_shell_command])

        morpheus = Agent(
             name="Morpheus", model=default_model_instance, instructions=morpheus_instructions,
             tools=[
                 execute_shell_command,
                 neo.as_tool(tool_name="Neo", tool_description="Delegate coding, review, or documentation tasks to Neo."),
                 trinity.as_tool(tool_name="Trinity", tool_description="Delegate information gathering or reconnaissance shell commands to Trinity."),
                 cypher.as_tool(tool_name="Cypher", tool_description="Delegate tasks to Cypher for alternative perspectives or direct shell execution if needed."),
                 tank.as_tool(tool_name="Tank", tool_description="Delegate specific shell command execution to Tank."),
             ],
             mcp_servers=mcp_servers
        )
        logger.debug("NebulaShellzzar agent team created. Morpheus is the starting agent.") # Changed to DEBUG
        return morpheus

if __name__ == "__main__":
    NebuchaShellzzarBlueprint.main()
