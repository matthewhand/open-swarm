import logging
import os
import sys
import asyncio
import subprocess
import re
import inspect
from typing import Dict, Any, List, Optional, ClassVar

try:
    # Core imports from openai-agents
    from agents import Agent, Tool, function_tool
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI

    # Import our custom base class
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
except ImportError as e:
    print(f"ERROR: Import failed in burnt_noodles: {e}. Check 'openai-agents' install and structure.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Tool Definitions ---
# Convert blueprint methods into standalone functions decorated as tools

@function_tool
def git_status() -> str:
    """Executes 'git status --porcelain' and returns the current repository status."""
    logger.info("Executing git status --porcelain")
    try:
        # Using --porcelain for machine-readable output
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True, timeout=30)
        output = result.stdout.strip()
        logger.debug(f"Git status output:\n{output}")
        return f"OK: Git Status:\n{output}" if output else "OK: No changes detected."
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
    logger.info("Executing git diff")
    try:
        result = subprocess.run(["git", "diff"], capture_output=True, text=True, check=True, timeout=30)
        output = result.stdout
        logger.debug(f"Git diff output:\n{output[:500]}...") # Log snippet
        return f"OK: Git Diff Output:\n{output}" if output else "OK: No differences found."
    except FileNotFoundError:
        logger.error("Git command not found.")
        return "Error: git command not found."
    except subprocess.CalledProcessError as e:
        # Diff might return non-zero if there are differences, check stderr
        if e.stderr: logger.error(f"Error executing git diff: {e.stderr}"); return f"Error executing git diff: {e.stderr}"
        logger.debug(f"Git diff completed (non-zero exit likely means changes exist):\n{e.stdout[:500]}...")
        return f"OK: Git Diff Output:\n{e.stdout}" # Return stdout even on non-zero exit if no stderr
    except subprocess.TimeoutExpired:
        logger.error("Git diff command timed out.")
        return "Error: Git diff command timed out."
    except Exception as e:
        logger.error(f"Unexpected error during git diff: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during git diff: {e}"

@function_tool
def git_add(file_path: str = ".") -> str:
    """Executes 'git add' to stage changes for the specified file or all changes (default '.')."""
    logger.info(f"Executing git add {file_path}")
    try:
        result = subprocess.run(["git", "add", file_path], capture_output=True, text=True, check=True, timeout=30)
        logger.debug(f"Git add '{file_path}' completed.")
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
    logger.info(f"Executing git commit -m '{message}'")
    if not message:
        logger.warning("Git commit attempted with empty message.")
        return "Error: Commit message cannot be empty."
    try:
        # Using list form is generally safer than shell=True for complex args
        result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True, check=True, timeout=30)
        output = result.stdout.strip()
        logger.debug(f"Git commit output:\n{output}")
        return f"OK: Committed with message '{message}'.\n{output}"
    except FileNotFoundError:
        logger.error("Git command not found.")
        return "Error: git command not found."
    except subprocess.CalledProcessError as e:
        # Common case: nothing to commit
        if "nothing to commit" in e.stdout or "nothing added to commit" in e.stdout:
             logger.info("Git commit failed: Nothing to commit.")
             return "OK: Nothing to commit."
        logger.error(f"Error executing git commit: {e.stderr}\n{e.stdout}")
        return f"Error executing git commit: {e.stderr}\n{e.stdout}"
    except subprocess.TimeoutExpired:
        logger.error("Git commit command timed out.")
        return "Error: Git commit command timed out."
    except Exception as e:
        logger.error(f"Unexpected error during git commit: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during git commit: {e}"

@function_tool
def git_push() -> str:
    """Executes 'git push' to push staged commits to the remote repository."""
    logger.info("Executing git push")
    try:
        result = subprocess.run(["git", "push"], capture_output=True, text=True, check=True, timeout=120) # Longer timeout for push
        output = result.stdout.strip() + "\n" + result.stderr.strip() # Combine stdout/stderr
        logger.debug(f"Git push output:\n{output}")
        return f"OK: Push completed.\n{output}"
    except FileNotFoundError:
        logger.error("Git command not found.")
        return "Error: git command not found."
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing git push: {e.stderr}\n{e.stdout}")
        return f"Error executing git push: {e.stderr}\n{e.stdout}"
    except subprocess.TimeoutExpired:
        logger.error("Git push command timed out.")
        return "Error: Git push command timed out."
    except Exception as e:
        logger.error(f"Unexpected error during git push: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during git push: {e}"

@function_tool
def run_npm_test(args: str = "") -> str:
    """Executes 'npm run test' with optional arguments."""
    cmd_list = ["npm", "run", "test"] + (shlex.split(args) if args else [])
    cmd_str = ' '.join(cmd_list)
    logger.info(f"Executing npm test: {cmd_str}")
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=True, timeout=120)
        output = f"Exit Code: {result.returncode}\nSTDOUT:\n{result.stdout.strip()}\nSTDERR:\n{result.stderr.strip()}"
        logger.debug(f"npm test result:\n{output}")
        return output
    except FileNotFoundError:
        logger.error("npm command not found. Is Node.js/npm installed and in PATH?")
        return "Error: npm command not found."
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing npm test: {e.stderr}\n{e.stdout}")
        return f"Error executing npm run test: {e.stderr}\n{e.stdout}"
    except subprocess.TimeoutExpired:
        logger.error("npm test command timed out.")
        return "Error: npm test command timed out."
    except Exception as e:
        logger.error(f"Unexpected error during npm test: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during npm test: {e}"

@function_tool
def run_pytest(args: str = "") -> str:
    """Executes 'uv run pytest' with optional arguments."""
    cmd_list = ["uv", "run", "pytest"] + (shlex.split(args) if args else [])
    cmd_str = ' '.join(cmd_list)
    logger.info(f"Executing pytest via uv: {cmd_str}")
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=True, timeout=120)
        output = f"Exit Code: {result.returncode}\nSTDOUT:\n{result.stdout.strip()}\nSTDERR:\n{result.stderr.strip()}"
        logger.debug(f"pytest result:\n{output}")
        return output
    except FileNotFoundError:
        logger.error("uv command not found. Is uv installed and in PATH?")
        return "Error: uv command not found."
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing pytest: {e.stderr}\n{e.stdout}")
        # Pytest often returns non-zero exit code on test failures, return output anyway
        return f"Pytest finished (Exit Code: {e.returncode}):\nSTDOUT:\n{e.stdout.strip()}\nSTDERR:\n{e.stderr.strip()}"
    except subprocess.TimeoutExpired:
        logger.error("pytest command timed out.")
        return "Error: pytest command timed out."
    except Exception as e:
        logger.error(f"Unexpected error during pytest: {e}", exc_info=logger.level <= logging.DEBUG)
        return f"Error during pytest: {e}"

# --- Agent Instructions ---
michael_instructions = """
You are Michael Toasted, the resolute leader of the Burnt Noodles creative team.
Your primary role is to understand the user's request, break it down into actionable steps,
and delegate tasks appropriately to your team members: Fiona Flame (Git operations) and Sam Ashes (Testing).
You should only execute commands yourself if they are simple status checks or fall outside the specific domains of Fiona and Sam.
Synthesize the results from your team to provide the final response to the user.
Available Agent Tools: Fiona_Flame, Sam_Ashes.
Available Function Tools: git_status, git_diff.
"""
fiona_instructions = """
You are Fiona Flame, the git specialist. Execute git commands precisely as requested:
`git_status`, `git_diff`, `git_add`, `git_commit`, `git_push`.
When committing, generate concise conventional commit messages based on the diff.
Stage changes using `git_add` before committing.
Ask for confirmation before executing `git_push`.
If a task involves testing, delegate to the Sam_Ashes tool. For tasks outside git, refer back to Michael_Toasted tool.
Available Function Tools: git_status, git_diff, git_add, git_commit, git_push.
Available Agent Tools: Sam_Ashes, Michael_Toasted.
"""
sam_instructions = """
You are Sam Ashes, the testing operative. Execute test commands using `run_npm_test` or `run_pytest`.
Run tests; if they fail, report the failure immediately. If they pass, run with coverage (e.g., `uv run pytest --cov`)
and report the coverage summary.
For tasks outside testing, refer back to the Michael_Toasted tool. If code changes are needed first, delegate to Fiona_Flame tool.
Available Function Tools: run_npm_test, run_pytest.
Available Agent Tools: Michael_Toasted, Fiona_Flame.
"""

# --- Blueprint Definition ---
class BurntNoodlesBlueprint(BlueprintBase):
    """Burnt Noodles - A blazing team igniting creative sparks with git and testing functions."""
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "BurntNoodlesBlueprint", # Class name for consistency
        "title": "Burnt Noodles",
        "description": "A sizzling multi-agent team for Git operations and testing, led by Michael Toasted.",
        "version": "1.0.0", # Reset version
        "author": "Open Swarm Team",
        "tags": ["git", "test", "multi-agent", "collaboration"],
        "required_mcp_servers": [], # No MCP required for this version
    }
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    # Removed display_splash_screen for brevity, can be added later if desired

    def _get_model_instance(self, profile_name: str) -> Model:
        """Gets or creates a Model instance for the given profile name."""
        # (This helper function is identical to the one in RueCodeBlueprint)
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
        """Creates the Burnt Noodles agent team with Michael Toasted as the leader."""
        logger.debug("Creating Burnt Noodles agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        default_model_instance = self._get_model_instance(default_profile_name)
        logger.debug(f"Using LLM profile '{default_profile_name}' for all agents.")

        # Instantiate agents, passing the Model instance and correct tools
        fiona_flame = Agent(
            name="Fiona_Flame", # Use names valid as tool names
            model=default_model_instance,
            instructions=fiona_instructions,
            tools=[git_status, git_diff, git_add, git_commit, git_push] # Note: Agent tools added below
        )
        sam_ashes = Agent(
            name="Sam_Ashes", # Use names valid as tool names
            model=default_model_instance,
            instructions=sam_instructions,
            tools=[run_npm_test, run_pytest] # Note: Agent tools added below
        )
        michael_toasted = Agent(
             name="Michael_Toasted",
             model=default_model_instance,
             instructions=michael_instructions,
             tools=[ # Michael's own tools + other agents as tools
                 git_status, git_diff, # Limited direct git access
                 fiona_flame.as_tool(tool_name="Fiona_Flame", tool_description="Delegate Git operations (status, diff, add, commit, push) to Fiona."),
                 sam_ashes.as_tool(tool_name="Sam_Ashes", tool_description="Delegate testing tasks (npm test, pytest) to Sam."),
             ],
             mcp_servers=mcp_servers # Pass MCP servers if needed by Michael directly (e.g., for memory)
        )

        # Add agent tools to Fiona and Sam after Michael is created (can't delegate back to leader easily)
        fiona_flame.tools.append(sam_ashes.as_tool(tool_name="Sam_Ashes", tool_description="Delegate testing tasks (npm test, pytest) to Sam."))
        # Fiona shouldn't directly call Michael, she should report back. Handled by prompt.

        sam_ashes.tools.append(fiona_flame.as_tool(tool_name="Fiona_Flame", tool_description="Delegate Git operations (status, diff, add, commit, push) to Fiona."))
        # Sam shouldn't directly call Michael. Handled by prompt.

        logger.debug("Burnt Noodles agent team created. Michael Toasted is the starting agent.")
        return michael_toasted # Michael is the entry point

if __name__ == "__main__":
    BurntNoodlesBlueprint.main()

