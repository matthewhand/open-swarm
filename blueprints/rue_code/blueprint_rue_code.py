import logging
import os
import sys
import asyncio
import subprocess
import re
from typing import Dict, Any, List, Optional

try:
    # Use the correct Agent import and base class
    from agents import Agent, Tool, function_tool
    from agents.mcp import MCPServer # Import MCPServer for type hint
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
    # Provide more helpful error message
    print(f"ERROR: Import failed: {e}. Ensure 'openai-agents' library is installed and project structure is correct.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Tools (remain the same) ---
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
        # Use absolute path for safety, but check it's within CWD project root?
        # For now, keep it simple, assume relative paths are intended within project
        with open(path, "r", encoding="utf-8") as f:
            if include_line_numbers: return ''.join(f'{i + 1}: {line}' for i, line in enumerate(f))
            else: return f.read()
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
        return f"Error: File not found at path: {path}"
    except Exception as e: logger.error(f"Read error {path}: {e}"); return f"Error reading file: {e}"
@function_tool
def write_to_file(path: str, content: str) -> str:
    """Writes content to a file (overwrites), creating directories. Ensures path is within CWD."""
    logger.info(f"Writing: {path}")
    try:
        # Ensure path is relative to project root and prevent writing outside
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(os.getcwd()):
             logger.error(f"Attempted write outside CWD denied: {path}")
             return f"Error: Cannot write outside current working directory: {path}"
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f: f.write(content)
        return f"OK: Wrote to {path}."
    except Exception as e: logger.error(f"Write error {path}: {e}"); return f"Error writing file: {e}"

# Apply Diff, Search Files, List Files, Prepare Git Commit tools remain the same...
@function_tool
def apply_diff(path: str, search: str, replace: str) -> str:
    """Applies search/replace to a file."""
    logger.info(f"Applying diff: {path}")
    try:
        safe_path = os.path.abspath(path);
        if not safe_path.startswith(os.getcwd()): return f"Error: Cannot apply diff outside CWD: {path}"
        if not os.path.exists(safe_path): return f"Error: File not found for diff: {path}"
        read_result = read_file(path) # Use read_file tool for consistency
        if read_result.startswith("Error:"): return f"Error reading for diff: {read_result}"
        original = read_result
        updated = original.replace(search, replace)
        if original == updated: return f"Warning: Search string not found in {path}."
        write_result = write_to_file(path, updated) # Use write_to_file tool
        if write_result.startswith("Error:"): return f"Error writing diff: {write_result}"
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
            # Simple exclusion of hidden dirs, might need more robust ignore logic
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            if not recursive and root != safe_dir: dirs.clear()
            for file in files:
                 # Simple exclusion of hidden files
                 if file.startswith('.'): continue
                 file_path = os.path.join(root, file)
                 try:
                     with open(file_path, "r", encoding="utf-8", errors='ignore') as f: content = f.read()
                     if regex.search(content): matches.append(os.path.relpath(file_path, safe_dir))
                 except Exception: pass # Ignore files we can't read
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
            files = [f for f in files if not f.startswith('.')] # Exclude hidden files
            for file in files:
                try: file_list.append(os.path.relpath(os.path.join(root, file), safe_dir))
                except ValueError: file_list.append(os.path.join(root, file)) # Handle case if not under safe_dir? Should not happen with check
    except Exception as e: return f"Error listing files: {e}"
    if not file_list: return f"No files found in '{directory}'."
    return f"Files found:\n" + "\n".join(sorted(file_list)) # Sort for consistency
@function_tool
def prepare_git_commit(commit_message: str, add_all: bool = True) -> str:
    """Stages changes and commits them."""
    logger.info(f"Git commit: '{commit_message}' (Add all: {add_all})")
    status_cmd = "git status --porcelain"; add_cmd = "git add ." if add_all else "git add -u"
    status_result = execute_command(status_cmd)
    if status_result.startswith("Error:"): return f"Error checking git status: {status_result}"
    # Extract STDOUT cleanly
    stdout_match = re.search(r"STDOUT:\n(.*?)\nSTDERR:", status_result, re.DOTALL)
    stdout_part = stdout_match.group(1).strip() if stdout_match else ""
    if not stdout_part: return "No changes detected to commit."
    add_result = execute_command(add_cmd);
    if add_result.startswith("Error:"): return f"Error staging files: {add_result}"
    # Escape double quotes in commit message for shell safety
    safe_commit_message = commit_message.replace('"', '\\"')
    commit_cmd = f'git commit -m "{safe_commit_message}"';
    commit_result = execute_command(commit_cmd)
    if commit_result.startswith("Error:"): return f"Error during git commit: {commit_result}"
    return f"OK: Committed '{commit_message}'. Output:\n{commit_result}"


# --- Agent Definitions (Updated Structure) ---

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

# Agent classes remain largely the same, but may accept mcp_servers if needed
class CoordinatorAgent(Agent):
    def __init__(self, team_tools: List[Tool], mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
        specific_instructions = (
            # (Instructions remain the same)
            "1. Deeply analyze the user's request. Ask clarifying questions if needed (though current setup is non-interactive).\n"
            "2. Formulate a step-by-step plan identifying which agent (Code, Architect, QA, GitManager) is needed for each step.\n"
            "3. Sequentially delegate tasks using the appropriate Agent Tool (e.g., call `Code` tool for coding).\n"
            "4. Provide COMPLETE context and necessary inputs when delegating (e.g., file paths, code snippets, search terms).\n"
            "5. Await the result from each agent before proceeding to the next step.\n"
            "6. If a simple check is required that doesn't fit another agent's role (like listing files or checking git status), use your *own* tools (`list_files`, `execute_command`) sparingly.\n"
            "7. Synthesize all results into a final, comprehensive response to the user."
        )
        instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal="coordinate the team to fulfill user requests via planning and delegation", specific_instructions=specific_instructions)
        # Coordinator itself doesn't directly use MCPs in this design, but receives the list for potential future use or inspection
        super().__init__(name="Coordinator", instructions=instructions, tools=[list_files, execute_command] + team_tools, mcp_servers=mcp_servers, **kwargs)

class CodeAgent(Agent):
    def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs): # Accept mcp_servers even if unused
        specific_instructions = (
            # (Instructions remain the same)
            "1. Receive coding tasks (write new file, modify existing, apply diff).\n"
            "2. Use `list_files` if needed to confirm file structure.\n"
            "3. Use `read_file` (with line numbers if modifying) to get existing code context.\n"
            "4. Use `write_to_file` or `apply_diff` to implement the changes.\n"
            "5. Report success/failure and provide the path to the modified/created file, or relevant code snippets/diff results."
        )
        instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal="implement code changes accurately", specific_instructions=specific_instructions)
        super().__init__(name="Code", instructions=instructions, tools=[read_file, write_to_file, apply_diff, list_files], mcp_servers=mcp_servers, **kwargs)

class ArchitectAgent(Agent):
     # CRITICAL: Needs mcp_servers passed in
     def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
         specific_instructions = (
             # (Instructions remain the same)
             "1. Receive design or research tasks.\n"
             "2. Use `brave-search` (via attached MCP server) for external web research on technologies, libraries, or best practices.\n"
             "3. Use `search_files` or `read_file` to understand existing project context.\n"
             "4. Synthesize findings into a design document.\n"
             "5. Use `write_to_file` to save the documentation, ensuring the filename ends with `.md`.\n"
             "6. Report completion and the path to the documentation file."
         )
         instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal="design systems and research technical solutions", specific_instructions=specific_instructions)
         # Pass mcp_servers to the parent Agent class
         super().__init__(name="Architect", instructions=instructions, tools=[read_file, write_to_file, search_files, list_files], mcp_servers=mcp_servers, **kwargs)

class QualityAssuranceAgent(Agent):
     def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs): # Accept mcp_servers
         specific_instructions = (
             # (Instructions remain the same)
             "1. Receive testing or linting tasks with the EXACT command to execute.\n"
             "2. Use the `execute_command` tool to run the command.\n"
             "3. Report the full, verbatim results (Exit Code, STDOUT, STDERR) back."
         )
         instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal="ensure code quality via tests and linting", specific_instructions=specific_instructions)
         super().__init__(name="QualityAssurance", instructions=instructions, tools=[execute_command], mcp_servers=mcp_servers, **kwargs)

class GitManagerAgent(Agent):
     def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs): # Accept mcp_servers
         specific_instructions = (
             # (Instructions remain the same, just formatting applied here)
             "Receive version control tasks. Use `prepare_git_commit` for staging and committing (provide a clear commit message!).\n"
             "Use `execute_command` for non-committing actions like 'git status', 'git diff', 'git log'. Report the outcome."
         )
         instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(
            agent_name=self.__class__.__name__,
            role_goal='manage version control',
            specific_instructions=specific_instructions
         )
         super().__init__(name="GitManager", instructions=instructions, tools=[prepare_git_commit, execute_command], mcp_servers=mcp_servers, **kwargs)


# --- Define the Blueprint (Using create_starting_agent) ---
class RueCodeBlueprint(BlueprintBase):
    # metadata remains the same
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "RueCodeBlueprint", # Use class name for consistency
            "title": "Rue-Code AI Dev Team",
            "description": "An automated coding team using openai-agents.",
            "version": "1.3.0", # Incremented version
            "author": "Open Swarm Team",
            "tags": ["code", "dev", "mcp", "multi-agent"],
            "required_mcp_servers": ["brave-search"], # Architect needs Brave Search
        }

    # Implement the required method
    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the multi-agent team and returns the Coordinator agent."""
        logger.info(f"Creating RueCode agent team with {len(mcp_servers)} MCP server(s)...")

        # Determine LLM profile for the CodeAgent (specialized model if configured)
        # Use self.config which already has merged blueprint/profile/cli overrides
        code_agent_profile = self.config.get("llm_profile_code", self.config.get("llm_profile", "default"))
        # Fallback further if specific profile doesn't exist? Base class _get_llm_profile handles default.
        # For simplicity, we assume the profile name in config is valid or 'default'.
        logger.info(f"Using LLM profile '{code_agent_profile}' for CodeAgent.")

        # Determine default profile for other agents
        default_profile = self.config.get("llm_profile", "default")
        logger.info(f"Using LLM profile '{default_profile}' for Coordinator, Architect, QA, GitManager.")


        # Instantiate agents, passing mcp_servers ONLY to those that need it (Architect)
        # Pass the profile NAME to the 'model' parameter, agents library should handle lookup via configured providers
        code_agent = CodeAgent(model=code_agent_profile)
        architect_agent = ArchitectAgent(model=default_profile, mcp_servers=mcp_servers) # Pass MCPs here
        qa_agent = QualityAssuranceAgent(model=default_profile)
        git_agent = GitManagerAgent(model=default_profile)

        # Instantiate Coordinator, giving it the other agents as tools
        coordinator = CoordinatorAgent(
             model=default_profile,
             # Pass the *list* of other agents converted to tools
             team_tools=[
                 code_agent.as_tool(
                     tool_name="Code",
                     tool_description="Delegate coding tasks (write, modify, read, diff files) to the Code agent. Provide full context and file paths."
                 ),
                 architect_agent.as_tool(
                     tool_name="Architect",
                     tool_description="Delegate system design, research (web via brave-search, files), or documentation (markdown) tasks to the Architect agent."
                 ),
                 qa_agent.as_tool(
                     tool_name="QualityAssurance",
                     tool_description="Delegate running test or lint commands via shell to the QA agent. Provide the exact command."
                 ),
                 git_agent.as_tool(
                     tool_name="GitManager",
                     tool_description="Delegate version control tasks like committing changes or checking status/diff to the GitManager agent."
                 )
             ],
             # Coordinator doesn't need direct MCP access in this design
             mcp_servers=None # Explicitly None
        )

        logger.info("RueCode agent team created. Coordinator is the starting agent.")
        # Return the Coordinator as the entry point for the Runner
        return coordinator

    # Remove the old create_agents method if it exists (it does in the user provided code)
    # def create_agents(self) -> Dict[str, Agent]: <-- REMOVED

if __name__ == "__main__":
    RueCodeBlueprint.main()
