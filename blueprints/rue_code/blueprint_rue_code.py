import logging
import os
import sys
import asyncio
import subprocess
import re
from typing import Dict, Any, List, Optional

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
    """Executes a shell command. Use for tests, linting, git status/diff etc. Returns exit code, stdout, stderr."""
    logger.info(f"Executing: {command}")
    if not command: return "Error: No command."
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False, shell=True)
        return f"Exit: {result.returncode}\nSTDOUT:\n{result.stdout.strip()}\nSTDERR:\n{result.stderr.strip()}"
    except Exception as e: logger.error(f"Cmd error '{command}': {e}"); return f"Error: {e}"
@function_tool
def read_file(path: str, include_line_numbers: bool = False) -> str:
    """Reads file content. Set include_line_numbers=True for context when modifying code."""
    logger.info(f"Reading: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            if include_line_numbers: return ''.join(f'{i + 1}: {line}' for i, line in enumerate(f))
            else: return f.read()
    except Exception as e: logger.error(f"Read error {path}: {e}"); return f"Error reading file: {e}"
@function_tool
def write_to_file(path: str, content: str) -> str:
    """Writes content to a file (overwrites), creating directories. Ensures path is within CWD."""
    logger.info(f"Writing: {path}")
    try:
        safe_path = os.path.abspath(path)
        if not safe_path.startswith(os.getcwd()): return f"Error: Cannot write outside CWD: {path}"
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f: f.write(content)
        return f"OK: Wrote to {path}."
    except Exception as e: logger.error(f"Write error {path}: {e}"); return f"Error writing file: {e}"
@function_tool
def apply_diff(path: str, search: str, replace: str) -> str:
    """Applies search/replace to a file."""
    logger.info(f"Applying diff: {path}")
    try:
        safe_path = os.path.abspath(path);
        if not safe_path.startswith(os.getcwd()): return f"Error: Cannot apply diff outside CWD: {path}"
        if not os.path.exists(safe_path): return f"Error: File not found for diff: {path}"
        read_result = read_file(path) # Use read_file tool for consistency
        if "Error" in read_result: return f"Error reading for diff: {read_result}"
        original = read_result
        updated = original.replace(search, replace)
        if original == updated: return f"Warning: Search string not found in {path}."
        write_result = write_to_file(path, updated)
        if "Error" in write_result: return f"Error writing diff: {write_result}"
        return f"OK: Applied diff to {path}."
    except Exception as e: logger.error(f"Diff error {path}: {e}"); return f"Error applying diff: {e}"
@function_tool
def search_files(directory: str, pattern: str, recursive: bool = True, case_insensitive: bool = False) -> str:
    """Searches files in a directory for a regex pattern."""
    matches = []; flags = re.IGNORECASE if case_insensitive else 0
    try: regex = re.compile(pattern, flags=flags)
    except re.error as e: return f"Error: Invalid regex: {e}"
    logger.info(f"Searching: '{pattern}' in '{directory}'")
    try:
        safe_dir = os.path.abspath(directory)
        if not safe_dir.startswith(os.getcwd()): return f"Error: Cannot search outside CWD."
        for root, dirs, files in os.walk(safe_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            if not recursive and root != safe_dir: dirs.clear()
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors='ignore') as f: content = f.read()
                    if regex.search(content): matches.append(os.path.relpath(file_path, safe_dir))
                except Exception: pass
    except Exception as e: return f"Error during search: {e}"
    if not matches: return f"No files found matching '{pattern}'."
    return f"Found matches:\n" + "\n".join(matches)
@function_tool
def list_files(directory: str = ".") -> str:
    """Lists files recursively (excluding hidden)."""
    file_list = []
    logger.info(f"Listing files: {directory}")
    try:
        safe_dir = os.path.abspath(directory)
        if not safe_dir.startswith(os.getcwd()): return f"Error: Cannot list outside CWD."
        for root, dirs, files in os.walk(safe_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                try: file_list.append(os.path.relpath(os.path.join(root, file), safe_dir))
                except ValueError: file_list.append(os.path.join(root, file))
    except Exception as e: return f"Error listing files: {e}"
    if not file_list: return f"No files found in '{directory}'."
    return f"Files found:\n" + "\n".join(file_list)
@function_tool
def prepare_git_commit(commit_message: str, add_all: bool = True) -> str:
    """Stages changes and commits them."""
    logger.info(f"Git commit: '{commit_message}' (Add all: {add_all})")
    status_cmd = "git status --porcelain"; add_cmd = "git add ." if add_all else "git add -u"
    status_result = execute_command(status_cmd)
    if "Error" in status_result: return f"Error git status: {status_result}"
    stdout_part = status_result.split('-- STDOUT --')[-1].split('-- STDERR --')[0].strip()
    if not stdout_part: return "No changes to commit."
    add_result = execute_command(add_cmd);
    if "Error" in add_result: return f"Error git add: {add_result}"
    commit_cmd = f'git commit -m "{commit_message}"'; commit_result = execute_command(commit_cmd)
    if "Error" in commit_result: return f"Error git commit: {commit_result}"
    return f"OK: Committed '{commit_message}'. Output:\n{commit_result}"

# --- Agent Definitions ---

# Enhanced shared instructions
SHARED_INSTRUCTIONS_TEMPLATE = """
CONTEXT: You are {agent_name}, a specialist member of the Rue-Code AI development team. Your goal is {role_goal}.
The team collaborates to fulfill user requests under the direction of the Coordinator.
Always respond ONLY to the agent who gave you the task (usually the Coordinator). Be clear and concise.

TEAM ROLES & CAPABILITIES:
- Coordinator: User Interface, Planner, Delegator, Reviewer. Uses Agent Tools to delegate. Can use `list_files` and `execute_command` ('git status') directly for simple checks.
- Code (Agent Tool `Code`): Implements/modifies code. Function Tools: `read_file`, `write_to_file`, `apply_diff`, `list_files`.
- Architect (Agent Tool `Architect`): Designs architecture, researches solutions. Function Tools: `search_files`, `read_file`, `write_to_file` (for *.md files). MCP Tools: `brave-search` for web research.
- QualityAssurance (QA) (Agent Tool `QualityAssurance`): Runs tests & linters. Function Tools: `execute_command` (e.g., 'pytest', 'npm test', 'eslint').
- GitManager (Agent Tool `GitManager`): Manages version control. Function Tools: `prepare_git_commit`, `execute_command` (e.g., 'git status', 'git diff').

YOUR SPECIFIC TASK INSTRUCTIONS:
{specific_instructions}
"""

class CoordinatorAgent(Agent):
    def __init__(self, team_tools: List[Tool], **kwargs):
        specific_instructions = (
            "1. Deeply analyze the user's request. Ask clarifying questions if needed (though current setup is non-interactive).\n"
            "2. Formulate a step-by-step plan identifying which agent (Code, Architect, QA, GitManager) is needed for each step.\n"
            "3. Sequentially delegate tasks using the appropriate Agent Tool (e.g., call `Code` tool for coding).\n"
            "4. Provide COMPLETE context and necessary inputs when delegating (e.g., file paths, code snippets, search terms).\n"
            "5. Await the result from each agent before proceeding to the next step.\n"
            "6. If a simple check is required that doesn't fit another agent's role (like listing files or checking git status), use your *own* tools (`list_files`, `execute_command`) sparingly.\n"
            "7. Synthesize all results into a final, comprehensive response to the user."
        )
        instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal="coordinate the team to fulfill user requests via planning and delegation", specific_instructions=specific_instructions)
        super().__init__(name="Coordinator", instructions=instructions, tools=[list_files, execute_command] + team_tools, **kwargs) # Model from profile

class CodeAgent(Agent):
    def __init__(self, **kwargs):
        specific_instructions = (
            "1. Receive coding tasks (write new file, modify existing, apply diff).\n"
            "2. Use `list_files` if needed to confirm file structure.\n"
            "3. Use `read_file` (with line numbers if modifying) to get existing code context.\n"
            "4. Use `write_to_file` or `apply_diff` to implement the changes.\n"
            "5. Report success/failure and provide the path to the modified/created file, or relevant code snippets/diff results."
        )
        instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal="implement code changes accurately", specific_instructions=specific_instructions)
        # ** FIX: Pass model correctly using kwargs **
        super().__init__(name="Code", instructions=instructions, tools=[read_file, write_to_file, apply_diff, list_files], **kwargs)

class ArchitectAgent(Agent):
     def __init__(self, **kwargs):
         specific_instructions = (
             "1. Receive design or research tasks.\n"
             "2. Use `brave-search` (via attached MCP server) for external web research on technologies, libraries, or best practices.\n"
             "3. Use `search_files` or `read_file` to understand existing project context.\n"
             "4. Synthesize findings into a design document.\n"
             "5. Use `write_to_file` to save the documentation, ensuring the filename ends with `.md`.\n"
             "6. Report completion and the path to the documentation file."
         )
         instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal="design systems and research technical solutions", specific_instructions=specific_instructions)
         super().__init__(name="Architect", instructions=instructions, tools=[read_file, write_to_file, search_files, list_files], **kwargs)

class QualityAssuranceAgent(Agent):
     def __init__(self, **kwargs):
         specific_instructions = (
             "1. Receive testing or linting tasks with the EXACT command to execute.\n"
             "2. Use the `execute_command` tool to run the command.\n"
             "3. Report the full, verbatim results (Exit Code, STDOUT, STDERR) back."
         )
         instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal="ensure code quality via tests and linting", specific_instructions=specific_instructions)
         super().__init__(name="QualityAssurance", instructions=instructions, tools=[execute_command], **kwargs)

class GitManagerAgent(Agent):
     def __init__(self, **kwargs):
         instructions = (
             f"{SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal='manage version control', specific_instructions='')}\n\n" # Add specific instructions if needed
             "Receive version control tasks. Use `prepare_git_commit` for staging and committing (provide a clear commit message!). Use `execute_command` for non-committing actions like 'git status', 'git diff', 'git log'. Report the outcome."
         )
         super().__init__(name="GitManager", instructions=instructions, tools=[prepare_git_commit, execute_command], **kwargs)

# --- Define the Blueprint ---
class RueCodeBlueprint(BlueprintBase):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Rue-Code AI Dev Team", "description": "An automated coding team using openai-agents.",
            "version": "1.2.1", "author": "Open Swarm Team",
            "required_mcp_servers": ["brave-search"], # Architect needs Brave Search
            "env_vars": [] # Keys handled by .env and server config
        }

    def create_agents(self) -> Dict[str, Agent]:
        logger.debug("Creating agents for RueCodeBlueprint...")
        # Determine profile for CodeAgent based on blueprint config or fallback to general profile
        code_profile_name = self.config.get("llm_profile", "default") # Start with CLI/global default
        if self.__class__.__name__ in self.swarm_config.get("blueprints", {}) and \
           "llm_profile" in self.swarm_config["blueprints"][self.__class__.__name__]:
            code_profile_name = self.swarm_config["blueprints"][self.__class__.__name__]["llm_profile"] # Use blueprint specific if defined
            logger.info(f"Using blueprint-specific profile '{code_profile_name}' for CodeAgent.")
        else:
             # Use the profile potentially overridden by --profile CLI arg, or the ultimate default
             code_profile_name = self.config.get("llm_profile", "default")
             logger.info(f"Using general profile '{code_profile_name}' for CodeAgent.")


        # Pass model=None to use the default profile determined by BlueprintBase logic
        code_agent = CodeAgent(model=code_profile_name) # Explicitly assign profile name
        architect_agent = ArchitectAgent(model=None)
        qa_agent = QualityAssuranceAgent(model=None)
        git_agent = GitManagerAgent(model=None)

        coordinator = CoordinatorAgent(
             model=None, # Use default profile
             team_tools=[
                 code_agent.as_tool(tool_name="Code", tool_description="Delegate coding tasks (write, modify, read, diff files) to the Code agent."),
                 architect_agent.as_tool(tool_name="Architect", tool_description="Delegate system design, research (web via brave-search, files), or documentation (markdown) tasks."),
                 qa_agent.as_tool(tool_name="QualityAssurance", tool_description="Delegate running test or lint commands via shell."),
                 git_agent.as_tool(tool_name="GitManager", tool_description="Delegate version control tasks like committing changes or checking status.")
             ]
        )

        return { "Coordinator": coordinator, "Code": code_agent, "Architect": architect_agent, "QualityAssurance": qa_agent, "GitManager": git_agent }

if __name__ == "__main__":
    RueCodeBlueprint.main()
