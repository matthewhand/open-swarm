import logging
import os
import sys
import asyncio
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path

# Ensure src is in path for imports like swarm.extensions...
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# --- Use new Agent and Tool types ---
try:
    from agents import Agent, Tool, function_tool
    # --- Use new BlueprintBase ---
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
     print(f"ERROR: Failed to import 'agents' or 'BlueprintBase'. Is 'openai-agents' installed and src in PYTHONPATH? Details: {e}")
     sys.exit(1)

# Setup logger for this specific blueprint module
logger = logging.getLogger(__name__)

# --- Define Tools using @function_tool ---
@function_tool
async def code_review(code_snippet: str) -> str:
    """
    Performs a basic static analysis of the provided code snippet.
    Checks for the presence of 'TODO' comments and excessive line count (>100 lines).
    Use this tool when asked to review code quality or identify potential issues.
    """
    logger.info(f"Reviewing code snippet (first 50 chars): {code_snippet[:50]}...")
    await asyncio.sleep(0.1) # Simulate analysis time
    issues = []
    if "TODO" in code_snippet: issues.append("Contains 'TODO' comment(s).")
    if len(code_snippet.splitlines()) > 100: issues.append("Code length exceeds 100 lines.")
    review = "Code Review Results: " + " ".join(issues) if issues else "Code Review Results: No basic issues found (checked TODOs, length)."
    logger.debug(f"Code review result: {review}")
    return review

@function_tool
def generate_documentation(code_snippet: str) -> str:
    """
    Generates a basic placeholder documentation block for the provided code snippet.
    Includes the first line of the code in the documentation.
    Use this tool ONLY when explicitly asked to generate documentation for code.
    """
    logger.info(f"Generating documentation for code (first 50 chars): {code_snippet[:50]}...")
    first_line = code_snippet.splitlines()[0].strip() if code_snippet else "N/A"
    doc = f"/**\n * Placeholder documentation generated for:\n * `{first_line}`\n * TODO: Elaborate on functionality, parameters, and return values.\n */"
    logger.debug(f"Generated documentation: {doc}")
    return doc

@function_tool
def execute_shell_command(command: str) -> str:
    """
    Executes a given shell command in a subprocess and returns its exit code, STDOUT, and STDERR.
    Use this tool for tasks requiring interaction with the underlying operating system's shell,
    such as running scripts, checking system status, managing files (ls, pwd, cat), or build processes.
    Be specific and careful with the commands you execute.
    """
    logger.info(f"Attempting shell command execution: {command}")
    if not command: return "Error: No command provided."
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False, shell=True)
        output = f"Exit Code: {result.returncode}\n-- STDOUT --\n{result.stdout.strip()}\n-- STDERR --\n{result.stderr.strip()}"
        logger.info(f"Shell command '{command}' finished with exit code {result.returncode}.")
        logger.debug(f"Shell Output:\n{output}")
        return output
    except FileNotFoundError:
        logger.error(f"Shell command not found (or shell itself missing): {command.split()[0]}")
        return f"Error: Command or shell not found: {command.split()[0]}"
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {command}")
        return f"Error: Command '{command}' timed out after 30 seconds."
    except Exception as e:
        logger.error(f"Command execution error '{command}': {e}", exc_info=logger.isEnabledFor(logging.DEBUG))
        return f"Error executing command '{command}': {e}"

# --- Agent Definitions ---

class MorpheusAgent(Agent):
    def __init__(self, team_tools: List[Tool] = [], **kwargs):
        instructions = (
            "You are Morpheus, leader of the Nebuchadnezzar. Your mission: fulfill user requests via planning and delegation.\n"
            "PLAN -> DELEGATE (using agent tools) -> SYNTHESIZE -> RESPOND.\n"
            "Crew & Tools:\n"
            "- `Neo` (Agent Tool): Coding, review (`code_review`), docs (`generate_documentation`), code tests/builds (`execute_shell_command`).\n"
            "- `Trinity` (Agent Tool): Info gathering, recon (`execute_shell_command`).\n"
            "- `Tank` (Agent Tool): Straightforward shell execution (`execute_shell_command`).\n"
            "- `Oracle` (Agent Tool): Complex analysis, strategic advice (no function tools).\n"
            "- `Cypher` (Agent Tool): Alternative/cynical view, reluctant shell execution (`execute_shell_command`).\n"
            "Direct Function Tools:\n"
            "- `execute_shell_command`: For simple coordination tasks YOU perform.\n"
            "Be clear in your plan and delegation. Combine results accurately."
        )
        all_tools = [execute_shell_command] + team_tools
        super().__init__(name="Morpheus", model="gpt-4o", instructions=instructions, tools=all_tools, **kwargs)

# ... (Other agent definitions remain the same: TrinityAgent, NeoAgent, OracleAgent, CypherAgent, TankAgent) ...
class TrinityAgent(Agent):
     def __init__(self, **kwargs): super().__init__( name="Trinity", model="gpt-4o", instructions="You are Trinity, recon expert. Use `execute_shell_command` for info gathering (e.g., `uname -a`, `df -h`, `ip addr`) as tasked by Morpheus. Report findings clearly.", tools=[execute_shell_command], **kwargs)
class NeoAgent(Agent):
     def __init__(self, **kwargs): super().__init__( name="Neo", model="gpt-4o", instructions="You are Neo, the programmer. Use tools `code_review`, `generate_documentation`, or `execute_shell_command` (for build/test) as directed by Morpheus. Provide code/results clearly.", tools=[code_review, generate_documentation, execute_shell_command], **kwargs)
class OracleAgent(Agent):
     def __init__(self, **kwargs): super().__init__( name="Oracle", model="gpt-4o", instructions="You are the Oracle. Offer insights, analysis, predictions when consulted. You do not use tools.", tools=[], **kwargs)
class CypherAgent(Agent):
     def __init__(self, **kwargs): super().__init__( name="Cypher", model="gpt-4o", instructions="You are Cypher, pragmatic and cynical. Offer alternative views. Use `execute_shell_command` if ordered, maybe with commentary.", tools=[execute_shell_command], **kwargs)
class TankAgent(Agent):
     def __init__(self, **kwargs): super().__init__( name="Tank", model="gpt-4o", instructions="You are Tank, the operator. Execute specific shell commands using `execute_shell_command` when told. Report exact output (stdout/stderr/exit code).", tools=[execute_shell_command], **kwargs)

# --- Define the Blueprint ---
class NebulaShellzzarBlueprint(BlueprintBase):
    @property
    def metadata(self) -> Dict[str, Any]:
        return { "title": "NebulaShellzzar", "description": "Matrix-themed crew for sysadmin/coding.", "version": "1.1.1", "author": "Open Swarm Team", "required_mcp_servers": [], "env_vars": ["OPENAI_API_KEY"], }

    def create_agents(self) -> Dict[str, Agent]:
        logger.debug("Creating agents for NebulaShellzzarBlueprint...")
        trinity = TrinityAgent()
        neo = NeoAgent()
        oracle = OracleAgent()
        cypher = CypherAgent()
        tank = TankAgent()

        # Create Morpheus last, passing other agents as potential tools for delegation
        # *** FIX: Provide required args to as_tool() ***
        morpheus = MorpheusAgent(team_tools=[
            trinity.as_tool(tool_name="Trinity", tool_description="Delegate info gathering/recon tasks to Trinity."),
            neo.as_tool(tool_name="Neo", tool_description="Delegate coding, review, documentation, or code build/test tasks to Neo."),
            oracle.as_tool(tool_name="Oracle", tool_description="Consult the Oracle for complex analysis, predictions, or strategic advice."),
            cypher.as_tool(tool_name="Cypher", tool_description="Delegate tasks to Cypher for an alternative/cynical perspective or reluctant shell execution."),
            tank.as_tool(tool_name="Tank", tool_description="Delegate specific, straightforward shell command execution to Tank.")
        ])

        return { "Morpheus": morpheus, "Trinity": trinity, "Neo": neo, "Oracle": oracle, "Cypher": cypher, "Tank": tank }

# --- Main execution block ---
if __name__ == "__main__":
    NebulaShellzzarBlueprint.main()
