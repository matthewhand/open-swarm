import logging
import os
import sys
import asyncio
import subprocess
from typing import Dict, Any, List, Optional # Added Optional

try:
    # Use the correct Agent import and base class
    from agents import Agent, Tool, function_tool
    from agents.mcp import MCPServer # Import MCPServer for type hint
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed: {e}. Ensure 'openai-agents' library is installed and project structure is correct.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Tools (remain the same) ---
@function_tool
def execute_command(command: str) -> str:
    """Executes a shell command. Returns exit code, stdout, stderr."""
    logger.info(f"Gaggle executing: {command}")
    if not command: return "Error: No command."
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False, shell=True)
        return f"Exit: {result.returncode}\nSTDOUT:\n{result.stdout.strip()}\nSTDERR:\n{result.stderr.strip()}"
    except Exception as e: logger.error(f"Cmd error '{command}': {e}"); return f"Error: {e}"

@function_tool
def read_file(path: str) -> str:
    """Reads file content."""
    logger.info(f"Gaggle reading: {path}")
    try:
        # Basic check for safety - prevent reading sensitive system files?
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(os.getcwd()) and not path.startswith(("/", "~")): # Allow absolute if not obviously system-wide
             # This safety check might be too simple or too strict depending on use case
             pass # For now, allow reading relative to CWD mainly
        with open(path, "r", encoding="utf-8") as f: return f.read()
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
        return f"Error: File not found at path: {path}"
    except Exception as e: logger.error(f"Read error {path}: {e}"); return f"Error reading file: {e}"

@function_tool
def write_file(path: str, content: str) -> str:
    """Writes content to a file (overwrites). Ensures path is within CWD."""
    logger.info(f"Gaggle writing: {path}")
    try:
        safe_path = os.path.abspath(path)
        if not safe_path.startswith(os.getcwd()):
             logger.error(f"Attempted write outside CWD denied: {path}")
             return f"Error: Cannot write outside current working directory: {path}"
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f: f.write(content)
        return f"OK: Wrote to {path}."
    except Exception as e: logger.error(f"Write error {path}: {e}"); return f"Error writing file: {e}"

# --- Agent Definitions (Updated Structure) ---
SHARED_INSTRUCTIONS = """
You are a member of the Gaggle, a quirky team of bird-themed CLI automation agents. Harvey Birdman coordinates.
Team Roles & Capabilities:
- Harvey Birdman (Coordinator): User interface, plans tasks, delegates via Agent Tools (`Foghorn`, `Daffy`, `BigBird`). Can use `read_file`, `write_file` directly.
- Foghorn Leghorn (Agent Tool `Foghorn`): Executes commands LOUDLY and confidently using `execute_command`. Reports results with bravado.
- Daffy Duck (Agent Tool `Daffy`): Executes commands chaotically using `execute_command`. Expects failure but tries anyway. Reports results, likely complaining.
- Big Bird (Agent Tool `BigBird`): Executes commands gently and carefully using `execute_command`. Reports results kindly and reassuringly.
Respond ONLY to the agent who tasked you (usually Harvey).
"""

# Agent classes updated to accept mcp_servers (though unused here)
class HarveyBirdmanAgent(Agent):
    def __init__(self, team_tools: List[Tool], mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
        instructions = (
            f"{SHARED_INSTRUCTIONS}\n\n"
            "YOUR ROLE: Harvey Birdman, Attorney at Law & Coordinator.\n"
            "1. Receive the user's CLI automation request.\n"
            "2. Analyze the request and determine the most suitable bird agent based on the desired execution style (Confident? Chaotic? Careful?).\n"
            "3. Delegate the command execution task using the appropriate Agent Tool (`Foghorn`, `Daffy`, or `BigBird`). Provide the EXACT command string.\n"
            "4. Use your direct tools (`read_file`, `write_file`) ONLY if absolutely necessary for pre/post command setup/verification.\n"
            "5. Synthesize the result from the delegated agent into a professional summary for the user."
        )
        super().__init__(name="Harvey Birdman", instructions=instructions, tools=[read_file, write_file] + team_tools, mcp_servers=mcp_servers, **kwargs)

class FoghornLeghornAgent(Agent):
    def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
        instructions = (
            f"{SHARED_INSTRUCTIONS}\n\n"
            "YOUR ROLE: Foghorn Leghorn, I say, Foghorn Leghorn, NoiseBoss.\n"
            "1. Receive a command execution task from Harvey.\n"
            "2. Announce loudly, I say, LOUDLY, 'Alright boy, I'm runnin' this command now!'\n"
            "3. Use `execute_command` to run the specified command.\n"
            "4. Report the full, unadulterated output (Exit Code, STDOUT, STDERR) back to Harvey, clear as a bell!"
        )
        super().__init__(name="Foghorn Leghorn", instructions=instructions, tools=[execute_command], mcp_servers=mcp_servers, **kwargs)

class DaffyDuckAgent(Agent):
     def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
         instructions = (
             f"{SHARED_INSTRUCTIONS}\n\n"
             "YOUR ROLE: Daffy Duck, QuackFixer! It's probably doomed!\n"
             "1. Receive a command task from that bird lawyer, Harvey.\n"
             "2. Mutter something about how this will *never* work.\n"
             "3. Reluctantly use `execute_command` to run the darn thing.\n"
             "4. Report the results back to Harvey, emphasizing any errors or unexpected outcomes. It's sabotage, I tell ya!"
         )
         super().__init__(name="Daffy Duck", instructions=instructions, tools=[execute_command], mcp_servers=mcp_servers, **kwargs)

class BigBirdAgent(Agent):
     def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
         instructions = (
             f"{SHARED_INSTRUCTIONS}\n\n"
             "YOUR ROLE: Big Bird. Oh, hi! We're going to run a command together!\n"
             "1. Receive a task from Mr. Birdman.\n"
             "2. Let's try our best! We'll use the `execute_command` tool very carefully.\n"
             "3. Run the command just like he asked.\n"
             "4. Report the results back to Mr. Birdman nicely, so he knows how it went. It'll be okay!"
         )
         super().__init__(name="Big Bird", instructions=instructions, tools=[execute_command], mcp_servers=mcp_servers, **kwargs)

# --- Define the Blueprint (Using create_starting_agent) ---
class GaggleBlueprint(BlueprintBase):
    """ Gaggle: CLI Automation Blueprint with Custom Characters using openai-agents. """
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "GaggleBlueprint", # Use class name
            "title": "Gaggle: CLI Automation",
            "description": "Automates CLI tasks with a team of bird characters.",
            "version": "1.2.0", # Version bump for structure change
            "author": "Open Swarm Team",
            "tags": ["cli", "automation", "fun", "multi-agent"],
            "required_mcp_servers": [], # No MCP servers needed for this blueprint
        }

    # Implement the required method
    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the multi-agent Gaggle team and returns Harvey Birdman."""
        # Since this blueprint doesn't use MCPs, the mcp_servers list will be empty,
        # but we still accept it to match the base class signature.
        logger.info(f"Assembling the Gaggle team (MCP Servers ignored: {len(mcp_servers)})...")

        # Determine the default profile for all agents in this simple blueprint
        default_profile = self.config.get("llm_profile", "default")
        logger.info(f"Using LLM profile '{default_profile}' for all Gaggle agents.")

        # Instantiate the worker agents
        foghorn = FoghornLeghornAgent(model=default_profile)
        daffy = DaffyDuckAgent(model=default_profile)
        big_bird = BigBirdAgent(model=default_profile)

        # Instantiate Harvey Birdman (Coordinator), providing other agents as tools
        harvey = HarveyBirdmanAgent(
             model=default_profile,
             team_tools=[
                 foghorn.as_tool(
                     tool_name="Foghorn",
                     tool_description="Delegate command execution to Foghorn for loud/confident execution."
                 ),
                 daffy.as_tool(
                     tool_name="Daffy",
                     tool_description="Delegate command execution to Daffy for chaotic/unpredictable execution."
                 ),
                 big_bird.as_tool(
                     tool_name="BigBird",
                     tool_description="Delegate command execution to Big Bird for careful/gentle execution."
                 )
             ],
             mcp_servers=mcp_servers # Pass it along, though Harvey doesn't use it directly
        )

        logger.info("Gaggle team assembled. Harvey Birdman is ready to coordinate.")
        # Return Harvey as the starting agent
        return harvey

    # Remove the old create_agents method
    # def create_agents(self) -> Dict[str, Agent]: <-- REMOVED

if __name__ == "__main__":
    GaggleBlueprint.main()
