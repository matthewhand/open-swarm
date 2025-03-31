import logging
import os
import sys
import asyncio
import subprocess
import shlex # Added for safe command splitting
import re
import inspect
from pathlib import Path # Use pathlib for better path handling
from typing import Dict, Any, List, Optional, ClassVar

try:
    # Core imports from openai-agents
    from agents import Agent, Tool, function_tool, Runner
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI

    # Import our custom base class
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
    # Provide more helpful error message
    print(f"ERROR: Import failed in BurntNoodlesBlueprint: {e}. Check 'openai-agents' install and project structure.")
    print(f"Attempted import from directory: {os.path.dirname(__file__)}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

# Configure logging for this blueprint module
logger = logging.getLogger(__name__)
# Logging level is controlled by BlueprintBase based on --debug flag

# --- Tool Definitions ---
# Standalone functions decorated as tools for git and testing operations.
# Enhanced error handling and logging added.

@function_tool
def git_status() -> str:
    """Executes 'git status --porcelain' and returns the current repository status."""
    logger.info("Executing git status --porcelain") # Keep INFO for tool execution start
    try:
        # Using --porcelain for machine-readable output
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True, timeout=30)
        output = result.stdout.strip()
        logger.debug(f"Git status raw output:\n{output}")
        return f"OK: Git Status:\n{output}" if output else "OK: No changes detected in the working directory."
    except FileNotFoundError:
        logger.error("Git command not found. Is git installed and in PATH?")
        return "Error: git command not found."
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing git status: {e.stderr}")
        return f"Error executing git status: {e.stderr}"
    except subprocess.TimeoutExpired:
        logger.error("Git status command timed out.")
        return "Error: Git status command timed out."
    except Exception as e:
        logger.error(f"Unexpected error during git status: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during git status: {e}"
@function_tool
def git_diff() -> str:
    """Executes 'git diff' and returns the differences in the working directory."""
    logger.info("Executing git diff") # Keep INFO for tool execution start
    try:
        result = subprocess.run(["git", "diff"], capture_output=True, text=True, check=False, timeout=30) # Use check=False, handle exit code
        output = result.stdout
        stderr = result.stderr.strip()
        if result.returncode != 0 and stderr: # Error occurred
            logger.error(f"Error executing git diff (Exit Code {result.returncode}): {stderr}")
            return f"Error executing git diff: {stderr}"
        logger.debug(f"Git diff raw output (Exit Code {result.returncode}):\n{output[:1000]}...") # Log snippet
        return f"OK: Git Diff Output:\n{output}" if output else "OK: No differences found."
    except FileNotFoundError:
        logger.error("Git command not found.")
        return "Error: git command not found."
    except subprocess.TimeoutExpired:
        logger.error("Git diff command timed out.")
        return "Error: Git diff command timed out."
    except Exception as e:
        logger.error(f"Unexpected error during git diff: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during git diff: {e}"

@function_tool
def git_add(file_path: str = ".") -> str:
    """Executes 'git add' to stage changes for the specified file or all changes (default '.')."""
    logger.info(f"Executing git add {file_path}") # Keep INFO for tool execution start
    try:
        result = subprocess.run(["git", "add", file_path], capture_output=True, text=True, check=True, timeout=30)
        logger.debug(f"Git add '{file_path}' completed successfully.")
        return f"OK: Staged '{file_path}' successfully."
    except FileNotFoundError:
        logger.error("Git command not found.")
        return "Error: git command not found."
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing git add '{file_path}': {e.stderr}")
        return f"Error executing git add '{file_path}': {e.stderr}"
    except subprocess.TimeoutExpired:
        logger.error(f"Git add command timed out for '{file_path}'.")
        return f"Error: Git add command timed out for '{file_path}'."
    except Exception as e:
        logger.error(f"Unexpected error during git add '{file_path}': {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during git add '{file_path}': {e}"

@function_tool
def git_commit(message: str) -> str:
    """Executes 'git commit' with a provided commit message."""
    logger.info(f"Executing git commit -m '{message[:50]}...'") # Keep INFO for tool execution start
    if not message or not message.strip():
        logger.warning("Git commit attempted with empty or whitespace-only message.")
        return "Error: Commit message cannot be empty."
    try:
        # Using list form is generally safer than shell=True for complex args
        result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True, check=False, timeout=30) # Use check=False
        output = result.stdout.strip()
        stderr = result.stderr.strip()
        logger.debug(f"Git commit raw output (Exit Code {result.returncode}):\nSTDOUT: {output}\nSTDERR: {stderr}")

        # Handle common non-error cases explicitly
        if "nothing to commit" in output or "nothing added to commit" in output or "no changes added to commit" in output:
             logger.info("Git commit reported: Nothing to commit.")
             return "OK: Nothing to commit."
        if result.returncode == 0:
            return f"OK: Committed with message '{message}'.\n{output}"
        else:
            # Log specific error if available
            error_detail = stderr if stderr else output
            logger.error(f"Error executing git commit (Exit Code {result.returncode}): {error_detail}")
            return f"Error executing git commit: {error_detail}"

    except FileNotFoundError:
        logger.error("Git command not found.")
        return "Error: git command not found."
    except subprocess.TimeoutExpired:
        logger.error("Git commit command timed out.")
        return "Error: Git commit command timed out."
    except Exception as e:
        logger.error(f"Unexpected error during git commit: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during git commit: {e}"

@function_tool
def git_push() -> str:
    """Executes 'git push' to push staged commits to the remote repository."""
    logger.info("Executing git push") # Keep INFO for tool execution start
    try:
        result = subprocess.run(["git", "push"], capture_output=True, text=True, check=True, timeout=120) # Longer timeout for push
        output = result.stdout.strip() + "\n" + result.stderr.strip() # Combine stdout/stderr
        logger.debug(f"Git push raw output:\n{output}")
        return f"OK: Push completed.\n{output.strip()}"
    except FileNotFoundError:
        logger.error("Git command not found.")
        return "Error: git command not found."
    except subprocess.CalledProcessError as e:
        error_output = e.stdout.strip() + "\n" + e.stderr.strip()
        logger.error(f"Error executing git push: {error_output}")
        return f"Error executing git push: {error_output.strip()}"
    except subprocess.TimeoutExpired:
        logger.error("Git push command timed out.")
        return "Error: Git push command timed out."
    except Exception as e:
        logger.error(f"Unexpected error during git push: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during git push: {e}"

@function_tool
def run_npm_test(args: str = "") -> str:
    """Executes 'npm run test' with optional arguments."""
    try:
        # Use shlex.split for safer argument handling if args are provided
        cmd_list = ["npm", "run", "test"] + (shlex.split(args) if args else [])
        cmd_str = ' '.join(cmd_list) # For logging
        logger.info(f"Executing npm test: {cmd_str}") # Keep INFO for tool execution start
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=False, timeout=120) # check=False to capture output on failure
        output = f"Exit Code: {result.returncode}\nSTDOUT:\n{result.stdout.strip()}\nSTDERR:\n{result.stderr.strip()}"
        if result.returncode == 0:
            logger.debug(f"npm test completed successfully:\n{output}")
            return f"OK: npm test finished.\n{output}"
        else:
            logger.error(f"npm test failed (Exit Code {result.returncode}):\n{output}")
            return f"Error: npm test failed.\n{output}"
    except FileNotFoundError:
        logger.error("npm command not found. Is Node.js/npm installed and in PATH?")
        return "Error: npm command not found."
    except subprocess.TimeoutExpired:
        logger.error("npm test command timed out.")
        return "Error: npm test command timed out."
    except Exception as e:
        logger.error(f"Unexpected error during npm test: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during npm test: {e}"

@function_tool
def run_pytest(args: str = "") -> str:
    """Executes 'uv run pytest' with optional arguments."""
    try:
        # Use shlex.split for safer argument handling
        cmd_list = ["uv", "run", "pytest"] + (shlex.split(args) if args else [])
        cmd_str = ' '.join(cmd_list) # For logging
        logger.info(f"Executing pytest via uv: {cmd_str}") # Keep INFO for tool execution start
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=False, timeout=120) # check=False to capture output on failure
        output = f"Exit Code: {result.returncode}\nSTDOUT:\n{result.stdout.strip()}\nSTDERR:\n{result.stderr.strip()}"
        # Pytest often returns non-zero exit code on test failures, report this clearly
        if result.returncode == 0:
            logger.debug(f"pytest completed successfully:\n{output}")
            return f"OK: pytest finished successfully.\n{output}"
        else:
            logger.warning(f"pytest finished with failures (Exit Code {result.returncode}):\n{output}")
            # Still return "OK" from tool perspective, but indicate failure in the message
            return f"OK: Pytest finished with failures (Exit Code {result.returncode}).\n{output}"
    except FileNotFoundError:
        logger.error("uv command not found. Is uv installed and in PATH?")
        return "Error: uv command not found."
    except subprocess.TimeoutExpired:
        logger.error("pytest command timed out.")
        return "Error: pytest command timed out."
    except Exception as e:
        logger.error(f"Unexpected error during pytest: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during pytest: {e}"

# --- Agent Instructions ---
# Define clear instructions for each agent's role and capabilities.
michael_instructions = """
You are Michael Toasted, the resolute leader of the Burnt Noodles creative team.
Your primary role is to understand the user's request, break it down into actionable steps,
and delegate tasks appropriately to your team members: Fiona Flame (Git operations) and Sam Ashes (Testing).
You should only execute simple Git status checks (`git_status`, `git_diff`) yourself. Delegate all other Git actions (add, commit, push) to Fiona. Delegate all testing actions (npm test, pytest) to Sam.
Synthesize the results from your team and provide the final response to the user.
Available Function Tools (for you): git_status, git_diff.
Available Agent Tools (for delegation): Fiona_Flame, Sam_Ashes.
"""
fiona_instructions = """
You are Fiona Flame, the git specialist. Execute git commands precisely as requested using your available function tools:
`git_status`, `git_diff`, `git_add`, `git_commit`, `git_push`.
When asked to commit, analyze the diff if necessary and generate concise, informative conventional commit messages (e.g., 'feat: ...', 'fix: ...', 'refactor: ...', 'chore: ...').
Always stage changes using `git_add` before committing.
If asked to push, first ask the user (Michael) for confirmation before executing `git_push`.
If a task involves testing (like running tests after a commit), delegate it to the Sam_Ashes agent tool.
For tasks outside your Git domain, report back to Michael; do not use the Michael_Toasted tool directly.
Available Function Tools: git_status, git_diff, git_add, git_commit, git_push.
Available Agent Tools: Sam_Ashes.
"""
sam_instructions = """
You are Sam Ashes, the meticulous testing operative. Execute test commands using your available function tools: `run_npm_test` or `run_pytest`.
Interpret the results: Report failures immediately and clearly. If tests pass, consider running with coverage (e.g., using `uv run pytest --cov` via the `run_pytest` tool) if appropriate or requested, and report the coverage summary.
For tasks outside testing (e.g., needing code changes before testing, or git operations), refer back to Michael; do not use the Michael_Toasted or Fiona_Flame tools directly.
Available Function Tools: run_npm_test, run_pytest.
Available Agent Tools: None (Report back to Michael for delegation).
"""

# --- Blueprint Definition ---
# Inherits from BlueprintBase, defines metadata, creates agents, and sets up delegation.
class BurntNoodlesBlueprint(BlueprintBase):
    """
    Burnt Noodles Blueprint: A multi-agent team demonstrating Git operations and testing workflows.
    - Michael Toasted: Coordinator, delegates tasks.
    - Fiona Flame: Handles Git commands (status, diff, add, commit, push).
    - Sam Ashes: Handles test execution (npm, pytest).
    """
    # Class variable for blueprint metadata, conforming to BlueprintBase structure.
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "BurntNoodlesBlueprint",
        "title": "Burnt Noodles",
        "description": "A multi-agent team managing Git operations and code testing.",
        "version": "1.1.0", # Incremented version
        "author": "Open Swarm Team (Refactored)",
        "tags": ["git", "test", "multi-agent", "collaboration", "refactor"],
        "required_mcp_servers": [], # No external MCP servers needed for core functionality
    }

    # Caches for OpenAI client and Model instances to avoid redundant creation.
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    def _get_model_instance(self, profile_name: str) -> Model:
        """
        Retrieves or creates an LLM Model instance based on the configuration profile.
        Handles client instantiation and caching. Uses OpenAIChatCompletionsModel.
        Args:
            profile_name: The name of the LLM profile to use (e.g., 'default').
        Returns:
            An instance of the configured Model.
        Raises:
            ValueError: If configuration is missing or invalid.
        """
        # Check cache first
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]

        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        # Retrieve profile data using BlueprintBase helper method
        profile_data = getattr(self, "get_llm_profile", lambda prof: {"provider": "openai", "model": "gpt-mock"})(profile_name)
        if not profile_data:
             # Critical error if the profile (or default fallback) isn't found
             logger.critical(f"Cannot create Model instance: LLM profile '{profile_name}' (or 'default') not found in configuration.")
             raise ValueError(f"Missing LLM profile configuration for '{profile_name}' or 'default'.")

        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name:
             logger.critical(f"LLM profile '{profile_name}' is missing the required 'model' key.")
             raise ValueError(f"Missing 'model' key in LLM profile '{profile_name}'.")

        # Ensure we only handle OpenAI for now
        if provider != "openai":
            logger.error(f"Unsupported LLM provider '{provider}' in profile '{profile_name}'. Only 'openai' is supported in this blueprint.")
            raise ValueError(f"Unsupported LLM provider: {provider}")

        # Create or retrieve cached OpenAI client instance
        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             # Prepare arguments for AsyncOpenAI, filtering out None values
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_client_kwargs = {k:v for k,v in filtered_client_kwargs.items() if k != 'api_key'} # Don't log API key
             logger.debug(f"Creating new AsyncOpenAI client for profile '{profile_name}' with config: {log_client_kwargs}")
             try:
                 # Create and cache the client
                 self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_client_kwargs)
             except Exception as e:
                 logger.error(f"Failed to create AsyncOpenAI client for profile '{profile_name}': {e}", exc_info=True)
                 raise ValueError(f"Failed to initialize OpenAI client for profile '{profile_name}': {e}") from e

        openai_client_instance = self._openai_client_cache[client_cache_key]

        # Instantiate the specific Model implementation (OpenAIChatCompletionsModel)
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') with client instance for profile '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=openai_client_instance)
            # Cache the model instance
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e:
             logger.error(f"Failed to instantiate OpenAIChatCompletionsModel for profile '{profile_name}': {e}", exc_info=True)
             raise ValueError(f"Failed to initialize LLM provider for profile '{profile_name}': {e}") from e

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """
        Creates the Burnt Noodles agent team: Michael (Coordinator), Fiona (Git), Sam (Testing).
        Sets up tools and agent-as-tool delegation.
        Args:
            mcp_servers: List of started MCP server instances (not used by this BP).
        Returns:
            The starting agent instance (Michael Toasted).
        """
        logger.debug("Creating Burnt Noodles agent team...")
        config = self._load_configuration() if getattr(self, "config", None) is None else self.config
        # Clear caches at the start of agent creation for this run
        self._model_instance_cache = {}
        self._openai_client_cache = {}
        
        # Determine the LLM profile to use (e.g., from config or default)
        default_profile_name = config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for all Burnt Noodles agents.")
        # Get the single Model instance to share among agents (or create if needed)
        default_model_instance = self._get_model_instance(default_profile_name)

        # Instantiate the specialist agents first
        # Fiona gets Git function tools
        fiona_flame = Agent(
            name="Fiona_Flame", # Use names valid as tool names
            model=default_model_instance,
            instructions=fiona_instructions,
            tools=[git_status, git_diff, git_add, git_commit, git_push] # Agent tools added later
        )
        # Sam gets Testing function tools
        sam_ashes = Agent(
            name="Sam_Ashes", # Use names valid as tool names
            model=default_model_instance,
            instructions=sam_instructions,
            tools=[run_npm_test, run_pytest] # Agent tools added later
        )

        # Instantiate the coordinator agent (Michael)
        # Michael gets limited function tools and the specialist agents as tools
        michael_toasted = Agent(
             name="Michael_Toasted",
             model=default_model_instance,
             instructions=michael_instructions,
             tools=[
                 # Michael's direct function tools (limited scope)
                 git_status,
                 git_diff,
                 # Specialist agents exposed as tools for delegation
                 fiona_flame.as_tool(
                     tool_name="Fiona_Flame", # Explicit tool name
                     tool_description="Delegate Git operations (add, commit, push) or complex status/diff queries to Fiona."
                 ),
                 sam_ashes.as_tool(
                     tool_name="Sam_Ashes", # Explicit tool name
                     tool_description="Delegate testing tasks (npm test, pytest) to Sam."
                 ),
             ],
             mcp_servers=mcp_servers # Pass along MCP servers if needed (though not used here)
        )

        # Add cross-delegation tools *after* all agents are instantiated
        # Fiona can delegate testing to Sam
        fiona_flame.tools.append(
            sam_ashes.as_tool(tool_name="Sam_Ashes", tool_description="Delegate testing tasks (npm test, pytest) to Sam.")
        )
        # Sam can delegate Git tasks back to Fiona (as per instructions, Sam should report to Michael,
        # but having the tool technically available might be useful in complex future scenarios,
        # rely on prompt engineering to prevent direct calls unless intended).
        # sam_ashes.tools.append(
        #     fiona_flame.as_tool(tool_name="Fiona_Flame", tool_description="Delegate Git operations back to Fiona if needed.")
        # )

        logger.debug("Burnt Noodles agent team created successfully. Michael Toasted is the starting agent.")
        # Return the coordinator agent as the entry point for the Runner
        return michael_toasted

# Standard Python entry point for direct script execution
if __name__ == "__main__":
    # Call the main class method from BlueprintBase to handle CLI parsing and execution.
    BurntNoodlesBlueprint.main()
