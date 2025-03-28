import argparse
import asyncio
import os
import logging
import json
import re
from abc import abstractmethod
from typing import List, Dict, Any, Optional, Union, AsyncGenerator

# Assuming standard project structure
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import necessary Swarm components
try:
    from swarm.core import Swarm
    from swarm.types import Agent, Tool, ToolCall, ToolResult, ChatMessage, Response
    from swarm.extensions.config.config_loader import load_server_config
    from swarm.extensions.blueprint.output_utils import pretty_print_response
except ImportError as e:
    print(f"Error importing Swarm components: {e}")
    sys.exit(1)

from swarm.extensions.blueprint import BlueprintBase

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Agent Functions ---
async def code_review(code_snippet: str) -> str: """Performs a review of the provided code snippet."""; logger.info(f"Reviewing: {code_snippet[:50]}..."); await asyncio.sleep(0.1); issues = []; ("TODO" in code_snippet and issues.append("Found TODO.")); (len(code_snippet.splitlines()) > 100 and issues.append("Code long.")); return "Review: " + " ".join(issues) if issues else "Code looks good!"
def generate_documentation(code_snippet: str) -> str: """Generates documentation for the provided code snippet."""; logger.info(f"Docgen: {code_snippet[:50]}..."); return f"/**\n * Doc: {code_snippet.splitlines()[0]}...\n */"
def execute_shell_command(command: str) -> str:
    """Executes a shell command and returns the output."""
    logger.info(f"Exec shell: {command}")
    try: import subprocess; result = subprocess.run(command.split(), capture_output=True, text=True, timeout=30, check=False); output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"; logger.info(f"Output: {output[:100]}"); return output
    except FileNotFoundError: cmd_base = command.split()[0] if command else ""; logger.error(f"Cmd not found: {cmd_base}"); return f"Error: Cmd not found - {cmd_base}"
    except subprocess.TimeoutExpired: logger.error(f"Cmd timed out: {command}"); return f"Error: Cmd '{command}' timed out."
    except Exception as e: logger.error(f"Cmd error '{command}': {e}"); return f"Error executing: {e}"

# --- Agent Definitions ---
morpheus_agent = Agent( name="Morpheus", model="default", instructions= "Leader: plan, delegate (Neo: code, Trinity: info, Oracle: complex), use handoff, exec shell.", functions=[execute_shell_command], mcp_servers=["memory"],)
trinity_agent = Agent( name="Trinity", model="default", instructions="Investigator: gather info, exec recon shell cmds. Report findings.", functions=[execute_shell_command], mcp_servers=["memory"],)
neo_agent = Agent( name="Neo", model="default", instructions="Programmer: write, review, debug code. Use tools. Exec shell build/test.", functions=[code_review, generate_documentation, execute_shell_command], mcp_servers=["memory"],)
oracle_agent = Agent( name="Oracle", model="default", instructions="Oracle: provide insights, predictions. No direct actions.",)
cypher_agent = Agent( name="Cypher", model="default", instructions="Disillusioned: might mislead/negatives. Use shell if wanted.", functions=[execute_shell_command],)
tank_agent = Agent( name="Tank", model="default", instructions="Operator: exec shell cmds as requested. Report results.", functions=[execute_shell_command],)

# --- Blueprint Definition ---
class NebuchaShellzzarBlueprint(BlueprintBase):
    """
    Blueprint Name: NebulaShellzzar
    Description: A multi-agent blueprint inspired by The Matrix for system administration and coding tasks.
    Version: 0.1
    """
    def __init__(self, config_file: Optional[str] = None, debug: bool = False):
        try: loaded_config = load_server_config(file_path=config_file)
        except Exception as e: logger.error(f"Failed to load config: {e}"); raise
        super().__init__(config=loaded_config, debug=debug, use_markdown=getattr(self, 'use_markdown', False))
        self.swarm = Swarm(config=self.config, debug=self.debug)
        self.agents_list = [morpheus_agent, trinity_agent, neo_agent, oracle_agent, cypher_agent, tank_agent]
        for agent in self.agents_list: self.swarm.register_agent(agent)
        logger.debug(f"Agents registered: {[a.name for a in self.agents_list]}")

        # --- FIX: Explicitly set starting_agent for interactive mode ---
        start_agent_name = "Morpheus"
        if start_agent_name in self.swarm.agents:
            self.starting_agent = self.swarm.agents[start_agent_name]
            logger.debug(f"Starting agent set to: {start_agent_name}")
            # Optionally trigger discovery here if needed by interactive_mode setup, though determine_active_agent handles it later
            # self.set_starting_agent(self.starting_agent) # Call base class method if it does more setup
        else:
            logger.error(f"Default starting agent '{start_agent_name}' not found after registration!")
            # Handle error - maybe default to first available agent or raise?
            if self.swarm.agents:
                 first_agent_name = next(iter(self.swarm.agents))
                 self.starting_agent = self.swarm.agents[first_agent_name]
                 logger.warning(f"Defaulting starting agent to first available: {first_agent_name}")
            else:
                 # This case should be rare if agents_list is non-empty
                 logger.critical("No agents available to set as starting agent.")
                 # No need to raise here, the interactive_mode check will fail later
        # --- End FIX ---


    @property
    def metadata(self) -> Dict[str, str]:
        docstring = self.__doc__ or ""; metadata_dict = {'blueprint_name': 'Unknown', 'description': 'No description.', 'version': '0.0', 'author': 'N/A'}
        for line in [l.strip() for l in docstring.strip().split('\n')]:
            if ':' in line: key, value = line.split(':', 1); key_lower = key.strip().lower().replace(' ', '_'); (key_lower == 'blueprint_name' and metadata_dict.update({'blueprint_name': value.strip()})); (key_lower == 'description' and metadata_dict.update({'description': value.strip()})); (key_lower == 'version' and metadata_dict.update({'version': value.strip()})); (key_lower == 'author' and metadata_dict.update({'author': value.strip()}))
        if metadata_dict['blueprint_name'] == 'Unknown': metadata_dict['blueprint_name'] = self.__class__.__name__
        return metadata_dict

    async def run(self, instruction: str, stream: bool = False) -> Union[Response, AsyncGenerator[Dict[str, Any], None]]:
        initial_message = ChatMessage(role="user", content=instruction); starting_agent = self.swarm.agents.get("Morpheus")
        if not starting_agent: logger.error("Morpheus agent not found!"); return Response(messages=[ChatMessage(role="system", content="Error: Starting agent Morpheus not registered.")]) if not stream else self._stream_error("Starting agent Morpheus not registered.")
        logger.info(f"Starting run: '{instruction}'"); return await self.swarm.run(agent=starting_agent, messages=[initial_message.model_dump(exclude_none=True)], stream=stream, debug=self.debug)

    async def _stream_error(self, error_msg: str):
        yield {"error": error_msg}

# --- Main execution block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run NebulaShellzzar Blueprint"); parser.add_argument('--instruction', type=str); parser.add_argument('--auto-complete-task', action='store_true'); parser.add_argument('--config', type=str); parser.add_argument('--debug', action='store_true'); parser.add_argument('--use-markdown', action='store_true', help="Enable markdown output."); args = parser.parse_args()

    config_loader_logger = logging.getLogger('swarm.extensions.config.config_loader')
    if not args.debug: config_loader_logger.setLevel(logging.ERROR)

    try:
        blueprint = NebuchaShellzzarBlueprint(config_file=args.config, debug=args.debug)
        blueprint.use_markdown = args.use_markdown
    except Exception as init_error: print(f"Failed init: {init_error}"); logger.exception("Init failed."); sys.exit(1)

    if args.auto_complete_task:
        if not args.instruction: print("Error: --instruction required."); sys.exit(1)
        print("--- Non-Interactive Mode ---")
        try:
            final_response = asyncio.run(blueprint.run(args.instruction, stream=False))
            if isinstance(final_response, Response):
                messages_as_dicts = [msg.model_dump(exclude_none=True) for msg in final_response.messages]
                pretty_print_response(messages=messages_as_dicts, use_markdown=False, spinner=getattr(blueprint, 'spinner', None))
            else: print(f"Error: Invalid response type: {type(final_response)}")
        except Exception as e: print(f"Critical Error: {e}"); logger.exception("Run failed."); sys.exit(1)
        sys.exit(0)
    else:
        print("--- Interactive Mode ---")
        # Pass stream flag if needed, default False
        asyncio.run(blueprint.interactive_mode(stream=args.use_markdown))

