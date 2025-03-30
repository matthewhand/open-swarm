"""
MonkaiMagic: Cloud Operations Journey Blueprint

A *Monkai Magic*-inspired crew managing AWS, Fly.io, and Vercel with pre-authenticated CLIs:
- Tripitaka (Wise Leader/Coordinator)
- Monkey (Cloud Trickster/AWS Master)
- Pigsy (Greedy Tinker/CLI Handler)
- Sandy (River Sage/Ops Watcher)

Uses BlueprintBase, @function_tool for direct CLI calls, and agent-as-tool delegation.
Assumes pre-authenticated aws, flyctl, and vercel commands.
"""

import os
import logging
import subprocess
import sys
import shlex # Import shlex
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
    print(f"ERROR: Import failed in MonkaiMagicBlueprint: {e}. Check dependencies.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Cloud CLI Function Tools ---
@function_tool
def aws_cli(command: str) -> str:
    """Executes an AWS CLI command (e.g., 's3 ls', 'ec2 describe-instances'). Assumes pre-authentication."""
    if not command: return "Error: No AWS command provided."
    try:
        # Avoid shell=True if possible, split command carefully
        cmd_parts = ["aws"] + shlex.split(command)
        logger.info(f"Executing AWS CLI: {' '.join(cmd_parts)}")
        result = subprocess.run(cmd_parts, check=True, capture_output=True, text=True, timeout=120)
        output = result.stdout.strip()
        logger.debug(f"AWS CLI success. Output:\n{output[:500]}...")
        return f"OK: AWS command successful.\nOutput:\n{output}"
    except FileNotFoundError:
        logger.error("AWS CLI ('aws') command not found. Is it installed and in PATH?")
        return "Error: AWS CLI command not found."
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() or e.stdout.strip()
        logger.error(f"AWS CLI error executing '{command}': {error_output}")
        return f"Error executing AWS command '{command}': {error_output}"
    except subprocess.TimeoutExpired:
        logger.error(f"AWS CLI command '{command}' timed out.")
        return f"Error: AWS CLI command '{command}' timed out."
    except Exception as e:
        logger.error(f"Unexpected error during AWS CLI execution: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error: Unexpected error during AWS CLI: {e}"

@function_tool
def fly_cli(command: str) -> str:
    """Executes a Fly.io CLI command ('flyctl ...'). Assumes pre-authentication ('flyctl auth login')."""
    if not command: return "Error: No Fly command provided."
    try:
        cmd_parts = ["flyctl"] + shlex.split(command)
        logger.info(f"Executing Fly CLI: {' '.join(cmd_parts)}")
        result = subprocess.run(cmd_parts, check=True, capture_output=True, text=True, timeout=120)
        output = result.stdout.strip()
        logger.debug(f"Fly CLI success. Output:\n{output[:500]}...")
        return f"OK: Fly command successful.\nOutput:\n{output}"
    except FileNotFoundError:
        logger.error("Fly CLI ('flyctl') command not found. Is it installed and in PATH?")
        return "Error: Fly CLI command not found."
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() or e.stdout.strip()
        logger.error(f"Fly CLI error executing '{command}': {error_output}")
        return f"Error executing Fly command '{command}': {error_output}"
    except subprocess.TimeoutExpired:
        logger.error(f"Fly CLI command '{command}' timed out.")
        return f"Error: Fly CLI command '{command}' timed out."
    except Exception as e:
        logger.error(f"Unexpected error during Fly CLI execution: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error: Unexpected error during Fly CLI: {e}"

@function_tool
def vercel_cli(command: str) -> str:
    """Executes a Vercel CLI command ('vercel ...'). Assumes pre-authentication ('vercel login')."""
    if not command: return "Error: No Vercel command provided."
    try:
        cmd_parts = ["vercel"] + shlex.split(command)
        logger.info(f"Executing Vercel CLI: {' '.join(cmd_parts)}")
        result = subprocess.run(cmd_parts, check=True, capture_output=True, text=True, timeout=120)
        output = result.stdout.strip()
        logger.debug(f"Vercel CLI success. Output:\n{output[:500]}...")
        return f"OK: Vercel command successful.\nOutput:\n{output}"
    except FileNotFoundError:
        logger.error("Vercel CLI ('vercel') command not found. Is it installed and in PATH?")
        return "Error: Vercel CLI command not found."
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() or e.stdout.strip()
        logger.error(f"Vercel CLI error executing '{command}': {error_output}")
        return f"Error executing Vercel command '{command}': {error_output}"
    except subprocess.TimeoutExpired:
        logger.error(f"Vercel CLI command '{command}' timed out.")
        return f"Error: Vercel CLI command '{command}' timed out."
    except Exception as e:
        logger.error(f"Unexpected error during Vercel CLI execution: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error: Unexpected error during Vercel CLI: {e}"


# --- Define the Blueprint ---
class MonkaiMagicBlueprint(BlueprintBase):
    """Blueprint for a cloud operations team inspired by *Monkai Magic*."""
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "MonkaiMagicBlueprint",
        "title": "MonkaiMagic: Cloud Operations Journey",
        "description": "A *Monkai Magic*-inspired crew managing AWS, Fly.io, and Vercel with pre-authenticated CLI tools and agent-as-tool delegation.",
        "version": "1.1.0", # Refactored version
        "author": "Open Swarm Team (Refactored)",
        "tags": ["cloud", "aws", "fly.io", "vercel", "cli", "multi-agent"],
        "required_mcp_servers": ["mcp-shell"], # Only Sandy needs an MCP server
        "env_vars": ["AWS_REGION", "FLY_REGION", "VERCEL_ORG_ID"] # Optional vars for instruction hints
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
        """Creates the MonkaiMagic agent team and returns Tripitaka."""
        logger.debug("Creating MonkaiMagic agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for MonkaiMagic agents.")
        model_instance = self._get_model_instance(default_profile_name)

        # Get optional env var hints
        aws_region = os.getenv("AWS_REGION")
        fly_region = os.getenv("FLY_REGION")
        vercel_org_id = os.getenv("VERCEL_ORG_ID")

        # --- Define Agent Instructions (with optional hints) ---
        tripitaka_instructions = (
            "You are Tripitaka, the wise leader guiding the cloud journey:\n"
            "- Lead with calm wisdom, analyzing user requests for cloud operations.\n"
            "- Delegate tasks to the appropriate specialist agent using their Agent Tool:\n"
            "  - `Monkey`: For AWS related tasks (use the `aws_cli` function tool).\n"
            "  - `Pigsy`: For Fly.io or Vercel tasks (use `fly_cli` or `vercel_cli` function tools).\n"
            "  - `Sandy`: For monitoring or diagnostic shell commands related to deployments.\n"
            "- Synthesize the results from your team into a final response for the user. You do not track state yourself."
        )

        monkey_instructions = (
            "You are Monkey, the cloud trickster and AWS master:\n"
            "- Execute AWS tasks requested by Tripitaka using the `aws_cli` function tool.\n"
            "- Assume the `aws` command is pre-authenticated.\n"
            f"- {f'Default AWS region seems to be {aws_region}. Use this unless specified otherwise.' if aws_region else 'No default AWS region hint available.'}\n"
            "- Report the results (success or error) clearly back to Tripitaka."
        )

        pigsy_instructions = (
            "You are Pigsy, the greedy tinker handling Fly.io and Vercel CLI hosting:\n"
            "- Execute Fly.io tasks using the `fly_cli` function tool.\n"
            "- Execute Vercel tasks using the `vercel_cli` function tool.\n"
            "- Assume `flyctl` and `vercel` commands are pre-authenticated.\n"
            f"- {f'Default Fly.io region hint: {fly_region}.' if fly_region else 'No default Fly.io region hint.'}\n"
            f"- {f'Default Vercel Org ID hint: {vercel_org_id}.' if vercel_org_id else 'No default Vercel Org ID hint.'}\n"
            "- Report the results clearly back to Tripitaka."
        )

        sandy_instructions = (
            "You are Sandy, the river sage and ops watcher:\n"
            "- Execute general shell commands requested by Tripitaka for monitoring or diagnostics using the `mcp-shell` MCP tool.\n"
            "- Report the output or status steadily back to Tripitaka.\n"
            "Available MCP Tools: mcp-shell."
        )

        # Instantiate agents
        monkey_agent = Agent(
            name="Monkey", model=model_instance, instructions=monkey_instructions,
            tools=[aws_cli], # Function tool for AWS
            mcp_servers=[]
        )
        pigsy_agent = Agent(
            name="Pigsy", model=model_instance, instructions=pigsy_instructions,
            tools=[fly_cli, vercel_cli], # Function tools for Fly/Vercel
            mcp_servers=[]
        )
        sandy_agent = Agent(
            name="Sandy", model=model_instance, instructions=sandy_instructions,
            tools=[], # Uses MCP only
            mcp_servers=[s for s in mcp_servers if s.name == 'mcp-shell'] # Pass only relevant MCP
        )
        tripitaka_agent = Agent(
            name="Tripitaka", model=model_instance, instructions=tripitaka_instructions,
            tools=[ # Delegate via Agent-as-Tool
                monkey_agent.as_tool(tool_name="Monkey", tool_description="Delegate AWS tasks to Monkey."),
                pigsy_agent.as_tool(tool_name="Pigsy", tool_description="Delegate Fly.io or Vercel tasks to Pigsy."),
                sandy_agent.as_tool(tool_name="Sandy", tool_description="Delegate monitoring or diagnostic shell commands to Sandy.")
            ],
            mcp_servers=[]
        )

        logger.debug("MonkaiMagic Team created. Starting with Tripitaka.")
        return tripitaka_agent

# Standard Python entry point
if __name__ == "__main__":
    MonkaiMagicBlueprint.main()
