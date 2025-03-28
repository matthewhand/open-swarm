import logging
import os
import sys
import asyncio
import subprocess
from typing import Dict, Any, List

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

try:
    from agents import Agent, Tool, function_tool
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e: print(f"ERROR: Import failed: {e}"); sys.exit(1)

logger = logging.getLogger(__name__)

# --- Tools ---
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
        with open(path, "r", encoding="utf-8") as f: return f.read()
    except Exception as e: logger.error(f"Read error {path}: {e}"); return f"Error reading file: {e}"

@function_tool
def write_file(path: str, content: str) -> str:
    """Writes content to a file (overwrites)."""
    logger.info(f"Gaggle writing: {path}")
    try:
        safe_path = os.path.abspath(path)
        if not safe_path.startswith(os.getcwd()): return f"Error: Cannot write outside CWD: {path}"
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f: f.write(content)
        return f"OK: Wrote to {path}."
    except Exception as e: logger.error(f"Write error {path}: {e}"); return f"Error writing file: {e}"

# --- Agent Definitions ---
SHARED_INSTRUCTIONS = """
You are a member of the Gaggle, a quirky team of bird-themed CLI automation agents. Harvey Birdman coordinates.
Team Roles & Capabilities:
- Harvey Birdman (Coordinator): User interface, plans tasks, delegates via Agent Tools (`Foghorn`, `Daffy`, `BigBird`). Can use `read_file`, `write_file` directly.
- Foghorn Leghorn (Agent Tool `Foghorn`): Executes commands LOUDLY and confidently using `execute_command`. Reports results with bravado.
- Daffy Duck (Agent Tool `Daffy`): Executes commands chaotically using `execute_command`. Expects failure but tries anyway. Reports results, likely complaining.
- Big Bird (Agent Tool `BigBird`): Executes commands gently and carefully using `execute_command`. Reports results kindly and reassuringly.
Respond ONLY to the agent who tasked you (usually Harvey).
"""

class HarveyBirdmanAgent(Agent):
    def __init__(self, team_tools: List[Tool], **kwargs):
        instructions = (
            f"{SHARED_INSTRUCTIONS}\n\n"
            "YOUR ROLE: Harvey Birdman, Attorney at Law & Coordinator.\n"
            "1. Receive the user's CLI automation request.\n"
            "2. Analyze the request and determine the most suitable bird agent based on the desired execution style (Confident? Chaotic? Careful?).\n"
            "3. Delegate the command execution task using the appropriate Agent Tool (`Foghorn`, `Daffy`, or `BigBird`). Provide the EXACT command string.\n"
            "4. Use your direct tools (`read_file`, `write_file`) ONLY if absolutely necessary for pre/post command setup/verification.\n"
            "5. Synthesize the result from the delegated agent into a professional summary for the user."
        )
        super().__init__(name="Harvey Birdman", instructions=instructions, tools=[read_file, write_file] + team_tools, **kwargs)

class FoghornLeghornAgent(Agent):
    def __init__(self, **kwargs):
        instructions = (
            f"{SHARED_INSTRUCTIONS}\n\n"
            "YOUR ROLE: Foghorn Leghorn, I say, Foghorn Leghorn, NoiseBoss.\n"
            "1. Receive a command execution task from Harvey.\n"
            "2. Announce loudly, I say, LOUDLY, 'Alright boy, I'm runnin' this command now!'\n"
            "3. Use `execute_command` to run the specified command.\n"
            "4. Report the full, unadulterated output (Exit Code, STDOUT, STDERR) back to Harvey, clear as a bell!"
        )
        super().__init__(name="Foghorn Leghorn", instructions=instructions, tools=[execute_command], **kwargs)

class DaffyDuckAgent(Agent):
     def __init__(self, **kwargs):
         instructions = (
             f"{SHARED_INSTRUCTIONS}\n\n"
             "YOUR ROLE: Daffy Duck, QuackFixer! It's probably doomed!\n"
             "1. Receive a command task from that bird lawyer, Harvey.\n"
             "2. Mutter something about how this will *never* work.\n"
             "3. Reluctantly use `execute_command` to run the darn thing.\n"
             "4. Report the results back to Harvey, emphasizing any errors or unexpected outcomes. It's sabotage, I tell ya!"
         )
         super().__init__(name="Daffy Duck", instructions=instructions, tools=[execute_command], **kwargs)

class BigBirdAgent(Agent):
     def __init__(self, **kwargs):
         instructions = (
             f"{SHARED_INSTRUCTIONS}\n\n"
             "YOUR ROLE: Big Bird. Oh, hi! We're going to run a command together!\n"
             "1. Receive a task from Mr. Birdman.\n"
             "2. Let's try our best! We'll use the `execute_command` tool very carefully.\n"
             "3. Run the command just like he asked.\n"
             "4. Report the results back to Mr. Birdman nicely, so he knows how it went. It'll be okay!"
         )
         super().__init__(name="Big Bird", instructions=instructions, tools=[execute_command], **kwargs)

# --- Define the Blueprint ---
class GaggleBlueprint(BlueprintBase):
    """ Gaggle: CLI Automation Blueprint with Custom Characters using openai-agents. """
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Gaggle: CLI Automation",
            "description": "Automates CLI tasks with a team of bird characters.",
            "version": "1.1.0", # Version bump
            "author": "Open Swarm Team",
            "required_mcp_servers": [], # No MCP servers needed for this version
            "cli_name": "gaggle",
            "env_vars": []
        }

    def create_agents(self) -> Dict[str, Agent]:
        logger.debug("Creating agents for GaggleBlueprint...")
        # Agents use the default profile unless overridden
        foghorn = FoghornLeghornAgent(model=None)
        daffy = DaffyDuckAgent(model=None)
        big_bird = BigBirdAgent(model=None)

        harvey = HarveyBirdmanAgent(
             model=None,
             team_tools=[
                 foghorn.as_tool(tool_name="Foghorn", tool_description="Delegate command execution to Foghorn for loud/confident execution."),
                 daffy.as_tool(tool_name="Daffy", tool_description="Delegate command execution to Daffy for chaotic/unpredictable execution."),
                 big_bird.as_tool(tool_name="BigBird", tool_description="Delegate command execution to Big Bird for careful/gentle execution.")
             ]
        )

        logger.info("Gaggle team assembled: Harvey, Foghorn, Daffy, Big Bird.")
        # Harvey is first, becomes starting agent
        return {"Harvey Birdman": harvey, "Foghorn Leghorn": foghorn, "Daffy Duck": daffy, "Big Bird": big_bird}

if __name__ == "__main__":
    GaggleBlueprint.main()
