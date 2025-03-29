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
    logger.info(f"Executing shell command: {command}")
    if not command: return "Error: No command provided."
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False, shell=True)
        output = f"Exit Code: {result.returncode}\nSTDOUT:\n{result.stdout.strip()}\nSTDERR:\n{result.stderr.strip()}"
        logger.debug(f"Command '{command}' result:\n{output}")
        return output
    except FileNotFoundError:
        cmd_base = command.split()[0] if command else ""
        logger.error(f"Command not found: {cmd_base}")
        return f"Error: Command not found - {cmd_base}"
    except subprocess.TimeoutExpired:
        logger.error(f"Command '{command}' timed out after 60 seconds.")
        return f"Error: Command '{command}' timed out."
    except Exception as e:
        logger.error(f"Error executing command '{command}': {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error executing command: {e}"

@function_tool
def read_file(path: str, include_line_numbers: bool = False) -> str:
    """Reads file content. Set include_line_numbers=True for context when modifying code."""
    logger.info(f"Reading file: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            if include_line_numbers:
                lines = [f'{i + 1}: {line}' for i, line in enumerate(f)]
                content = "".join(lines)
            else:
                content = f.read()
            logger.debug(f"Read {len(content)} characters from {path}.")
            return content
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
        return f"Error: File not found at path: {path}"
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error reading file: {e}"

@function_tool
def write_to_file(path: str, content: str) -> str:
    """Writes content to a file (overwrites), creating directories. Ensures path is within CWD."""
    logger.info(f"Writing {len(content)} characters to file: {path}")
    try:
        abs_path_obj = Path(path).resolve()
        cwd_obj = Path.cwd().resolve()
        if not str(abs_path_obj).startswith(str(cwd_obj)):
             logger.error(f"Attempted write outside CWD denied: {path} (resolved to {abs_path_obj})")
             return f"Error: Cannot write outside current working directory: {path}"
        abs_path_obj.parent.mkdir(parents=True, exist_ok=True)
        with open(abs_path_obj, "w", encoding="utf-8") as f:
            f.write(content)
        logger.debug(f"Successfully wrote to {abs_path_obj}.")
        return f"OK: Wrote {len(content)} characters to {path}."
    except Exception as e:
        logger.error(f"Error writing file {path}: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error writing file: {e}"

@function_tool
def apply_diff(path: str, search: str, replace: str) -> str:
    """Applies search/replace to a file using its current content."""
    logger.info(f"Applying diff to file: {path} (search: '{search[:30]}...', replace: '{replace[:30]}...')")
    try:
        safe_path_obj = Path(path).resolve()
        cwd_obj = Path.cwd().resolve()
        if not str(safe_path_obj).startswith(str(cwd_obj)):
            return f"Error: Cannot apply diff outside CWD: {path}"
        if not safe_path_obj.is_file():
            return f"Error: File not found for diff: {path}"
        read_result = read_file(path)
        if read_result.startswith("Error:"):
            return f"Error reading file for diff: {read_result}"
        original_content = read_result
        updated_content = original_content.replace(search, replace)
        if original_content == updated_content:
            logger.warning(f"Search string not found in {path}, no changes applied.")
            return f"Warning: Search string not found in {path}."
        write_result = write_to_file(path, updated_content)
        if write_result.startswith("Error:"):
            return f"Error writing updated content after diff: {write_result}"
        logger.debug(f"Successfully applied diff to {path}.")
        return f"OK: Applied diff to {path}."
    except Exception as e:
        logger.error(f"Error applying diff to {path}: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error applying diff: {e}"

@function_tool
def search_files(directory: str, pattern: str, recursive: bool = True, case_insensitive: bool = False) -> str:
    """Searches files within a directory for a regex pattern."""
    logger.info(f"Searching for pattern '{pattern}' in directory '{directory}' (recursive={recursive}, case_insensitive={case_insensitive})")
    matches = []; flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern, flags=flags)
    except re.error as e:
        logger.error(f"Invalid regex pattern '{pattern}': {e}")
        return f"Error: Invalid regex pattern provided: {e}"
    try:
        safe_dir_obj = Path(directory).resolve()
        cwd_obj = Path.cwd().resolve()
        if not str(safe_dir_obj).startswith(str(cwd_obj)) and safe_dir_obj != cwd_obj:
             logger.warning(f"Search directory '{directory}' resolves outside CWD to '{safe_dir_obj}'. Restricting search to CWD.")
             safe_dir_obj = cwd_obj
        if not safe_dir_obj.is_dir():
            logger.error(f"Search directory not found: {safe_dir_obj}")
            return f"Error: Search directory not found: {directory}"
        search_method = safe_dir_obj.rglob if recursive else safe_dir_obj.glob
        for item_path in search_method("*"):
            if item_path.is_file() and not item_path.name.startswith('.'):
                 try:
                     content = item_path.read_text(encoding="utf-8", errors='ignore')
                     if regex.search(content):
                         matches.append(str(item_path.relative_to(cwd_obj)))
                 except Exception as read_err:
                     logger.debug(f"Could not read or search file {item_path}: {read_err}")
                     pass
    except Exception as e:
        logger.error(f"Error during file search in '{directory}': {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during file search: {e}"
    if not matches:
        logger.info(f"No files found matching pattern '{pattern}' in '{directory}'.")
        return f"No files found matching '{pattern}'."
    result_str = f"Found {len(matches)} file(s) matching '{pattern}':\n" + "\n".join(sorted(matches))
    logger.debug(f"Search results for '{pattern}':\n{result_str}")
    return result_str

@function_tool
def list_files(directory: str) -> str:
    """Lists files recursively within a directory (excluding hidden files/dirs)."""
    logger.info(f"Listing files in directory: {directory}")
    file_list = []
    try:
        safe_dir_obj = Path(directory).resolve()
        cwd_obj = Path.cwd().resolve()
        if not str(safe_dir_obj).startswith(str(cwd_obj)) and safe_dir_obj != cwd_obj:
            logger.warning(f"List directory '{directory}' resolves outside CWD to '{safe_dir_obj}'. Restricting list to CWD.")
            safe_dir_obj = cwd_obj
        if not safe_dir_obj.is_dir():
            logger.error(f"List directory not found: {safe_dir_obj}")
            return f"Error: Directory not found: {directory}"
        for item_path in safe_dir_obj.rglob('*'):
            if any(part.startswith('.') for part in item_path.relative_to(safe_dir_obj).parts): continue
            if item_path.is_file():
                try: file_list.append(str(item_path.relative_to(safe_dir_obj)))
                except ValueError: file_list.append(str(item_path))
    except Exception as e:
        logger.error(f"Error listing files in '{directory}': {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error listing files: {e}"
    if not file_list:
        logger.info(f"No non-hidden files found in '{directory}'.")
        return f"No non-hidden files found in '{directory}'."
    result_str = f"Files found in '{directory}':\n" + "\n".join(sorted(file_list))
    logger.debug(f"List files result:\n{result_str}")
    return result_str

@function_tool
def prepare_git_commit(commit_message: str, add_all: bool = True) -> str:
    """Stages changes ('git add .' or 'git add -u') and commits them."""
    logger.info(f"Preparing Git commit: '{commit_message}' (Add all: {add_all})")
    status_cmd = "git status --porcelain"; add_cmd = "git add ." if add_all else "git add -u"
    status_result = execute_command(status_cmd)
    if status_result.startswith("Error:"): return f"Error checking git status: {status_result}"
    stdout_match = re.search(r"STDOUT:\n(.*?)(?:\nSTDERR:|\Z)", status_result, re.DOTALL)
    stdout_part = stdout_match.group(1).strip() if stdout_match else ""
    if not stdout_part:
        logger.info("No changes detected by 'git status --porcelain'.")
        return "No changes detected to commit."
    logger.info(f"Staging changes using: {add_cmd}")
    add_result = execute_command(add_cmd);
    if add_result.startswith("Error:") or "Exit Code: 0" not in add_result:
        logger.error(f"Error staging files: {add_result}")
        return f"Error staging files: {add_result}"
    safe_commit_message = commit_message.replace('"', '\\"')
    commit_cmd = f'git commit -m "{safe_commit_message}"';
    logger.info(f"Executing commit command: {commit_cmd}")
    commit_result = execute_command(commit_cmd)
    if commit_result.startswith("Error:") or "Exit Code: 0" not in commit_result:
         logger.error(f"Error during git commit: {commit_result}")
         return f"Error during git commit: {commit_result}"
    logger.info(f"Successfully committed '{commit_message}'.")
    return f"OK: Committed '{commit_message}'.\nCommit Output:\n{commit_result}"

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

        client_cache_key = f"{provider}_{profile_data.get('base_url')}"

        if provider == "openai":
            if client_cache_key not in self._openai_client_cache:
                 client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
                 filtered_client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
                 log_client_kwargs = {k:v for k,v in filtered_client_kwargs.items() if k != 'api_key'}
                 logger.debug(f"Creating new AsyncOpenAI client for profile '{profile_name}' with config: {log_client_kwargs}")
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
        """Creates the multi-agent team and returns the Coordinator agent."""
        logger.debug(f"Creating RueCode agent team with {len(mcp_servers)} MCP server(s)...") # Changed to DEBUG
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        code_agent_profile_name = self.config.get("llm_profile", "default")
        code_agent_model_instance = self._get_model_instance(code_agent_profile_name)
        logger.debug(f"CodeAgent using LLM profile '{code_agent_profile_name}'.") # Changed to DEBUG

        default_profile_name = self.config.get("llm_profile", "code-large")
        default_model_instance = self._get_model_instance(default_profile_name)
        logger.debug(f"Other agents using LLM profile '{default_profile_name}'.") # Changed to DEBUG

        code_agent = CodeAgent(model=code_agent_model_instance, mcp_servers=[])
        architect_agent = ArchitectAgent(model=default_model_instance, mcp_servers=mcp_servers)
        qa_agent = QualityAssuranceAgent(model=default_model_instance, mcp_servers=[])
        git_agent = GitManagerAgent(model=default_model_instance, mcp_servers=[])

        coordinator = CoordinatorAgent(
             model=default_model_instance,
             team_tools=[
                 code_agent.as_tool(tool_name="Code", tool_description="Delegate coding tasks to the Code agent."),
                 architect_agent.as_tool(tool_name="Architect", tool_description="Delegate design/research tasks."),
                 qa_agent.as_tool(tool_name="QualityAssurance", tool_description="Delegate testing/linting tasks."),
                 git_agent.as_tool(tool_name="GitManager", tool_description="Delegate version control tasks.")
             ],
             mcp_servers=[]
        )

        logger.debug("RueCode agent team created. Coordinator is the starting agent.") # Changed to DEBUG
        return coordinator

if __name__ == "__main__":
    RueCodeBlueprint.main()
