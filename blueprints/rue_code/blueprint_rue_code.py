import logging
import os
import sys
import asyncio
import subprocess
import re
import inspect # Needed for filtering kwargs
from typing import Dict, Any, List, Optional, ClassVar

try:
    from agents import Agent, Tool, function_tool
    from agents.mcp import MCPServer
    from agents.models.interface import Model # Base class for type hints
    # Explicitly import the model classes we need
    from agents.models.openai_responses import OpenAIResponsesModel
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
    # Need the OpenAI client class
    from openai import AsyncOpenAI
except ImportError as e:
    print(f"ERROR: Import failed: {e}. Check 'openai-agents' install and project structure.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Tools (remain unchanged) ---
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
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
        return f"Error: File not found at path: {path}"
    except Exception as e: logger.error(f"Read error {path}: {e}"); return f"Error reading file: {e}"
@function_tool
def write_to_file(path: str, content: str) -> str:
    """Writes content to a file (overwrites), creating directories. Ensures path is within CWD."""
    logger.info(f"Writing: {path}")
    try:
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(os.getcwd()):
             logger.error(f"Attempted write outside CWD denied: {path}")
             return f"Error: Cannot write outside current working directory: {path}"
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f: f.write(content)
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
        read_result = read_file(path)
        if read_result.startswith("Error:"): return f"Error reading for diff: {read_result}"
        original = read_result
        updated = original.replace(search, replace)
        if original == updated: return f"Warning: Search string not found in {path}."
        write_result = write_to_file(path, updated)
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
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            if not recursive and root != safe_dir: dirs.clear()
            for file in files:
                 if file.startswith('.'): continue
                 file_path = os.path.join(root, file)
                 try:
                     with open(file_path, "r", encoding="utf-8", errors='ignore') as f: content = f.read()
                     if regex.search(content): matches.append(os.path.relpath(file_path, safe_dir))
                 except Exception: pass
    except Exception as e: return f"Error during search: {e}"
    if not matches: return f"No files found matching '{pattern}'."
    return f"Found matches:\n" + "\n".join(matches)
@function_tool
def list_files(directory: str) -> str:
    """Lists files recursively (excluding hidden)."""
    effective_directory = directory if directory else "."
    file_list = []
    logger.info(f"Listing files: {effective_directory}")
    try:
        safe_dir = os.path.abspath(effective_directory)
        if not safe_dir.startswith(os.getcwd()): return f"Error: Cannot list outside CWD."
        for root, dirs, files in os.walk(safe_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            files = [f for f in files if not f.startswith('.')]
            for file in files:
                try: file_list.append(os.path.relpath(os.path.join(root, file), safe_dir))
                except ValueError: file_list.append(os.path.join(root, file))
    except Exception as e: return f"Error listing files: {e}"
    if not file_list: return f"No files found in '{effective_directory}'."
    return f"Files found:\n" + "\n".join(sorted(file_list))
@function_tool
def prepare_git_commit(commit_message: str, add_all: bool = True) -> str:
    """Stages changes and commits them."""
    logger.info(f"Git commit: '{commit_message}' (Add all: {add_all})")
    status_cmd = "git status --porcelain"; add_cmd = "git add ." if add_all else "git add -u"
    status_result = execute_command(status_cmd)
    if status_result.startswith("Error:"): return f"Error checking git status: {status_result}"
    stdout_match = re.search(r"STDOUT:\n(.*?)\nSTDERR:", status_result, re.DOTALL)
    stdout_part = stdout_match.group(1).strip() if stdout_match else ""
    if not stdout_part: return "No changes detected to commit."
    add_result = execute_command(add_cmd);
    if add_result.startswith("Error:"): return f"Error staging files: {add_result}"
    safe_commit_message = commit_message.replace('"', '\\"')
    commit_cmd = f'git commit -m "{safe_commit_message}"';
    commit_result = execute_command(commit_cmd)
    if commit_result.startswith("Error:"): return f"Error during git commit: {commit_result}"
    return f"OK: Committed '{commit_message}'. Output:\n{commit_result}"

# --- Agent Definitions ---
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
# Agent __init__ methods use **kwargs filtering
class CoordinatorAgent(Agent):
    def __init__(self, team_tools: List[Tool], mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
        specific_instructions = "..." # Keep brief
        instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal="coordinate the team", specific_instructions=specific_instructions)
        effective_mcp_servers = mcp_servers if mcp_servers is not None else []
        agent_kwargs = {k: v for k, v in kwargs.items() if k in inspect.signature(Agent.__init__).parameters}
        super().__init__(name="Coordinator", instructions=instructions, tools=[list_files, execute_command] + team_tools, mcp_servers=effective_mcp_servers, **agent_kwargs)
class CodeAgent(Agent):
    def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
        specific_instructions = "..." # Keep brief
        instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal="implement code changes", specific_instructions=specific_instructions)
        effective_mcp_servers = mcp_servers if mcp_servers is not None else []
        agent_kwargs = {k: v for k, v in kwargs.items() if k in inspect.signature(Agent.__init__).parameters}
        super().__init__(name="Code", instructions=instructions, tools=[read_file, write_to_file, apply_diff, list_files], mcp_servers=effective_mcp_servers, **agent_kwargs)
class ArchitectAgent(Agent):
     def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
         specific_instructions = "..." # Keep brief
         instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal="design systems", specific_instructions=specific_instructions)
         effective_mcp_servers = mcp_servers if mcp_servers is not None else []
         agent_kwargs = {k: v for k, v in kwargs.items() if k in inspect.signature(Agent.__init__).parameters}
         super().__init__(name="Architect", instructions=instructions, tools=[read_file, write_to_file, search_files, list_files], mcp_servers=effective_mcp_servers, **agent_kwargs)
class QualityAssuranceAgent(Agent):
     def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
         specific_instructions = "..." # Keep brief
         instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal="ensure quality", specific_instructions=specific_instructions)
         effective_mcp_servers = mcp_servers if mcp_servers is not None else []
         agent_kwargs = {k: v for k, v in kwargs.items() if k in inspect.signature(Agent.__init__).parameters}
         super().__init__(name="QualityAssurance", instructions=instructions, tools=[execute_command], mcp_servers=effective_mcp_servers, **agent_kwargs)
class GitManagerAgent(Agent):
     def __init__(self, mcp_servers: Optional[List[MCPServer]] = None, **kwargs):
         specific_instructions = "..." # Keep brief
         instructions = SHARED_INSTRUCTIONS_TEMPLATE.format(agent_name=self.__class__.__name__, role_goal='manage version control', specific_instructions=specific_instructions)
         effective_mcp_servers = mcp_servers if mcp_servers is not None else []
         agent_kwargs = {k: v for k, v in kwargs.items() if k in inspect.signature(Agent.__init__).parameters}
         super().__init__(name="GitManager", instructions=instructions, tools=[prepare_git_commit, execute_command], mcp_servers=effective_mcp_servers, **agent_kwargs)

# --- Define the Blueprint ---
class RueCodeBlueprint(BlueprintBase):
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "RueCodeBlueprint", "title": "Rue-Code AI Dev Team",
        "description": "An automated coding team using openai-agents.", "version": "1.3.0",
        "author": "Open Swarm Team", "tags": ["code", "dev", "mcp", "multi-agent"],
        "required_mcp_servers": ["brave-search"],
    }
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

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

        # Use provider name (plus base_url if present) as cache key for the client
        client_cache_key = f"{provider}_{profile_data.get('base_url')}"

        if provider == "openai":
            if client_cache_key not in self._openai_client_cache:
                 client_kwargs = {
                     "api_key": profile_data.get("api_key"),
                     "base_url": profile_data.get("base_url")
                 }
                 filtered_client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
                 log_client_kwargs = {k:v for k,v in filtered_client_kwargs.items() if k != 'api_key'}
                 logger.info(f"Creating new AsyncOpenAI client for profile '{profile_name}' with config: {log_client_kwargs}")
                 try:
                     self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_client_kwargs)
                 except Exception as e:
                     logger.error(f"Failed to create AsyncOpenAI client for profile '{profile_name}': {e}", exc_info=True)
                     raise ValueError(f"Failed to initialize OpenAI client for profile '{profile_name}': {e}") from e
            openai_client_instance = self._openai_client_cache[client_cache_key]

            # Instantiate the *correct* Model class based on desired API (Chat Completions)
            logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') with specific client instance.")
            try:
                # Use OpenAIChatCompletionsModel
                model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=openai_client_instance)
            except Exception as e:
                 logger.error(f"Failed to instantiate OpenAIChatCompletionsModel for profile '{profile_name}': {e}", exc_info=True)
                 raise ValueError(f"Failed to initialize LLM provider for profile '{profile_name}': {e}") from e
        # TODO: Add elif blocks here for other providers
        else:
            logger.error(f"Unsupported LLM provider '{provider}' specified in profile '{profile_name}'. Cannot create specific Model instance.")
            raise ValueError(f"Unsupported LLM provider: {provider}")

        self._model_instance_cache[profile_name] = model_instance
        return model_instance


    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the multi-agent team and returns the Coordinator agent."""
        logger.info(f"Creating RueCode agent team with {len(mcp_servers)} MCP server(s)...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        code_agent_profile_name = self.config.get("llm_profile", "default") # Revert: Use default for CodeAgent for now
        code_agent_model_instance = self._get_model_instance(code_agent_profile_name)
        logger.info(f"CodeAgent using LLM profile '{code_agent_profile_name}'.")

        # Use 'code-large' profile for Coordinator & others as originally intended
        default_profile_name = self.config.get("llm_profile", "code-large") # Use code-large as the 'default' for this BP's agents
        default_model_instance = self._get_model_instance(default_profile_name)
        logger.info(f"Other agents using LLM profile '{default_profile_name}'.")

        # Pass the Model instance to the 'model' parameter
        code_agent = CodeAgent(model=code_agent_model_instance, mcp_servers=[])
        architect_agent = ArchitectAgent(model=default_model_instance, mcp_servers=mcp_servers)
        qa_agent = QualityAssuranceAgent(model=default_model_instance, mcp_servers=[])
        git_agent = GitManagerAgent(model=default_model_instance, mcp_servers=[])

        coordinator = CoordinatorAgent(
             model=default_model_instance, # Coordinator uses the 'code-large' (LiteLLM) model instance
             team_tools=[
                 code_agent.as_tool(tool_name="Code", tool_description="Delegate coding tasks to the Code agent."),
                 architect_agent.as_tool(tool_name="Architect", tool_description="Delegate design/research tasks."),
                 qa_agent.as_tool(tool_name="QualityAssurance", tool_description="Delegate testing/linting tasks."),
                 git_agent.as_tool(tool_name="GitManager", tool_description="Delegate version control tasks.")
             ],
             mcp_servers=[]
        )

        logger.info("RueCode agent team created. Coordinator is the starting agent.")
        return coordinator

if __name__ == "__main__":
    RueCodeBlueprint.main()
