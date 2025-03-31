import logging
import os
import sys
import asyncio
import subprocess
import shlex # Added for safe command splitting
import re
import inspect
from pathlib import Path # Use pathlib for better path handling
from typing import Dict, Any, List, Optional, ClassVar, AsyncGenerator

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

# --- Tool Logic Definitions (Undecorated) ---
def _git_status_logic() -> str:
    """Executes 'git status --porcelain' and returns the current repository status."""
    logger.info("Executing git status --porcelain")
    try:
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True, timeout=30)
        output = result.stdout.strip()
        logger.debug(f"Git status raw output:\n{output}")
        return f"OK: Git Status:\n{output}" if output else "OK: No changes detected in the working directory."
    except FileNotFoundError: logger.error("Git command not found."); return "Error: git command not found."
    except subprocess.CalledProcessError as e: logger.error(f"Error executing git status: {e.stderr}"); return f"Error executing git status: {e.stderr}"
    except subprocess.TimeoutExpired: logger.error("Git status command timed out."); return "Error: Git status command timed out."
    except Exception as e: logger.error(f"Unexpected error during git status: {e}", exc_info=logger.level <= logging.DEBUG); return f"Error during git status: {e}"

def _git_diff_logic() -> str:
    """Executes 'git diff' and returns the differences in the working directory."""
    logger.info("Executing git diff")
    try:
        result = subprocess.run(["git", "diff"], capture_output=True, text=True, check=False, timeout=30)
        output = result.stdout; stderr = result.stderr.strip()
        if result.returncode != 0 and stderr: logger.error(f"Error executing git diff (Exit Code {result.returncode}): {stderr}"); return f"Error executing git diff: {stderr}"
        logger.debug(f"Git diff raw output (Exit Code {result.returncode}):\n{output[:1000]}...")
        return f"OK: Git Diff Output:\n{output}" if output else "OK: No differences found."
    except FileNotFoundError: logger.error("Git command not found."); return "Error: git command not found."
    except subprocess.TimeoutExpired: logger.error("Git diff command timed out."); return "Error: Git diff command timed out."
    except Exception as e: logger.error(f"Unexpected error during git diff: {e}", exc_info=logger.level <= logging.DEBUG); return f"Error during git diff: {e}"

def _git_add_logic(file_path: str = ".") -> str:
    """Executes 'git add' to stage changes for the specified file or all changes (default '.')."""
    logger.info(f"Executing git add {file_path}")
    try:
        result = subprocess.run(["git", "add", file_path], capture_output=True, text=True, check=True, timeout=30)
        logger.debug(f"Git add '{file_path}' completed successfully.")
        return f"OK: Staged '{file_path}' successfully."
    except FileNotFoundError: logger.error("Git command not found."); return "Error: git command not found."
    except subprocess.CalledProcessError as e: logger.error(f"Error executing git add '{file_path}': {e.stderr}"); return f"Error executing git add '{file_path}': {e.stderr}"
    except subprocess.TimeoutExpired: logger.error(f"Git add command timed out for '{file_path}'."); return f"Error: Git add command timed out for '{file_path}'."
    except Exception as e: logger.error(f"Unexpected error during git add '{file_path}': {e}", exc_info=logger.level <= logging.DEBUG); return f"Error during git add '{file_path}': {e}"

def _git_commit_logic(message: str) -> str:
    """Executes 'git commit' with a provided commit message."""
    logger.info(f"Executing git commit -m '{message[:50]}...'")
    if not message or not message.strip(): logger.warning("Git commit attempted with empty message."); return "Error: Commit message cannot be empty."
    try:
        result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True, check=False, timeout=30)
        output = result.stdout.strip(); stderr = result.stderr.strip()
        logger.debug(f"Git commit raw output (Exit Code {result.returncode}):\nSTDOUT: {output}\nSTDERR: {stderr}")
        if "nothing to commit" in output or "nothing added to commit" in output or "no changes added to commit" in output:
             logger.info("Git commit reported: Nothing to commit."); return "OK: Nothing to commit."
        if result.returncode == 0: return f"OK: Committed with message '{message}'.\n{output}"
        else: error_detail = stderr if stderr else output; logger.error(f"Error executing git commit (Exit Code {result.returncode}): {error_detail}"); return f"Error executing git commit: {error_detail}"
    except FileNotFoundError: logger.error("Git command not found."); return "Error: git command not found."
    except subprocess.TimeoutExpired: logger.error("Git commit command timed out."); return "Error: Git commit command timed out."
    except Exception as e: logger.error(f"Unexpected error during git commit: {e}", exc_info=logger.level <= logging.DEBUG); return f"Error during git commit: {e}"

def _git_push_logic() -> str:
    """Executes 'git push' to push staged commits to the remote repository."""
    logger.info("Executing git push")
    try:
        result = subprocess.run(["git", "push"], capture_output=True, text=True, check=True, timeout=120)
        output = result.stdout.strip() + "\n" + result.stderr.strip()
        logger.debug(f"Git push raw output:\n{output}")
        return f"OK: Push completed.\n{output.strip()}"
    except FileNotFoundError: logger.error("Git command not found."); return "Error: git command not found."
    except subprocess.CalledProcessError as e: error_output = e.stdout.strip() + "\n" + e.stderr.strip(); logger.error(f"Error executing git push: {error_output}"); return f"Error executing git push: {error_output.strip()}"
    except subprocess.TimeoutExpired: logger.error("Git push command timed out."); return "Error: Git push command timed out."
    except Exception as e: logger.error(f"Unexpected error during git push: {e}", exc_info=logger.level <= logging.DEBUG); return f"Error during git push: {e}"

def _run_npm_test_logic(args: str = "") -> str:
    """Executes 'npm run test' with optional arguments."""
    try:
        cmd_list = ["npm", "run", "test"] + (shlex.split(args) if args else []); cmd_str = ' '.join(cmd_list)
        logger.info(f"Executing npm test: {cmd_str}")
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=False, timeout=120)
        output = f"Exit Code: {result.returncode}\nSTDOUT:\n{result.stdout.strip()}\nSTDERR:\n{result.stderr.strip()}"
        if result.returncode == 0: logger.debug(f"npm test completed successfully:\n{output}"); return f"OK: npm test finished.\n{output}"
        else: logger.error(f"npm test failed (Exit Code {result.returncode}):\n{output}"); return f"Error: npm test failed.\n{output}"
    except FileNotFoundError: logger.error("npm command not found."); return "Error: npm command not found."
    except subprocess.TimeoutExpired: logger.error("npm test command timed out."); return "Error: npm test command timed out."
    except Exception as e: logger.error(f"Unexpected error during npm test: {e}", exc_info=logger.level <= logging.DEBUG); return f"Error during npm test: {e}"

def _run_pytest_logic(args: str = "") -> str:
    """Executes 'uv run pytest' with optional arguments."""
    try:
        cmd_list = ["uv", "run", "pytest"] + (shlex.split(args) if args else []); cmd_str = ' '.join(cmd_list)
        logger.info(f"Executing pytest via uv: {cmd_str}")
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=False, timeout=120)
        output = f"Exit Code: {result.returncode}\nSTDOUT:\n{result.stdout.strip()}\nSTDERR:\n{result.stderr.strip()}"
        if result.returncode == 0: logger.debug(f"pytest completed successfully:\n{output}"); return f"OK: pytest finished successfully.\n{output}"
        else: logger.warning(f"pytest finished with failures (Exit Code {result.returncode}):\n{output}"); return f"OK: Pytest finished with failures (Exit Code {result.returncode}).\n{output}"
    except FileNotFoundError: logger.error("uv command not found."); return "Error: uv command not found."
    except subprocess.TimeoutExpired: logger.error("pytest command timed out."); return "Error: pytest command timed out."
    except Exception as e: logger.error(f"Unexpected error during pytest: {e}", exc_info=logger.level <= logging.DEBUG); return f"Error during pytest: {e}"

# --- Tool Definitions (Decorated - reverted to default naming) ---
git_status = function_tool(_git_status_logic)
git_diff = function_tool(_git_diff_logic)
git_add = function_tool(_git_add_logic)
git_commit = function_tool(_git_commit_logic)
git_push = function_tool(_git_push_logic)
run_npm_test = function_tool(_run_npm_test_logic)
run_pytest = function_tool(_run_pytest_logic)

# --- Agent Instructions ---
# (Instructions remain the same)
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
class BurntNoodlesBlueprint(BlueprintBase):
    metadata: ClassVar[Dict[str, Any]] = {
        "name": "BurntNoodlesBlueprint",
        "title": "Burnt Noodles",
        "description": "A multi-agent team managing Git operations and code testing.",
        "version": "1.1.0",
        "author": "Open Swarm Team (Refactored)",
        "tags": ["git", "test", "multi-agent", "collaboration", "refactor"],
        "required_mcp_servers": [],
    }

    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    def _get_model_instance(self, profile_name: str) -> Model:
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]

        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = getattr(self, "get_llm_profile", lambda prof: {"provider": "openai", "model": "gpt-mock"})(profile_name)
        if not profile_data:
             logger.critical(f"Cannot create Model instance: LLM profile '{profile_name}' (or 'default') not found in configuration.")
             raise ValueError(f"Missing LLM profile configuration for '{profile_name}' or 'default'.")

        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name:
             logger.critical(f"LLM profile '{profile_name}' is missing the required 'model' key.")
             raise ValueError(f"Missing 'model' key in LLM profile '{profile_name}'.")

        if provider != "openai":
            logger.error(f"Unsupported LLM provider '{provider}' in profile '{profile_name}'. Only 'openai' is supported in this blueprint.")
            raise ValueError(f"Unsupported LLM provider: {provider}")

        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_client_kwargs = {k:v for k,v in filtered_client_kwargs.items() if k != 'api_key'}
             logger.debug(f"Creating new AsyncOpenAI client for profile '{profile_name}' with config: {log_client_kwargs}")
             try:
                 self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_client_kwargs)
             except Exception as e:
                 logger.error(f"Failed to create AsyncOpenAI client for profile '{profile_name}': {e}", exc_info=True)
                 raise ValueError(f"Failed to initialize OpenAI client for profile '{profile_name}': {e}") from e

        openai_client_instance = self._openai_client_cache[client_cache_key]

        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') with client instance for profile '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=openai_client_instance)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e:
             logger.error(f"Failed to instantiate OpenAIChatCompletionsModel for profile '{profile_name}': {e}", exc_info=True)
             raise ValueError(f"Failed to initialize LLM provider for profile '{profile_name}': {e}") from e

    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        logger.debug("Creating Burnt Noodles agent team...")
        config = self._load_configuration() if getattr(self, "config", None) is None else self.config
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for all Burnt Noodles agents.")
        default_model_instance = self._get_model_instance(default_profile_name)

        # --- Use the decorated tool variables ---
        fiona_flame = Agent(
            name="Fiona_Flame",
            model=default_model_instance,
            instructions=fiona_instructions,
            tools=[git_status, git_diff, git_add, git_commit, git_push] # Agent tools added later
        )
        sam_ashes = Agent(
            name="Sam_Ashes",
            model=default_model_instance,
            instructions=sam_instructions,
            tools=[run_npm_test, run_pytest] # Agent tools added later
        )
        michael_toasted = Agent(
             name="Michael_Toasted",
             model=default_model_instance,
             instructions=michael_instructions,
             tools=[
                 git_status, # Michael's direct tools
                 git_diff,
                 fiona_flame.as_tool(
                     tool_name="Fiona_Flame",
                     tool_description="Delegate Git operations (add, commit, push) or complex status/diff queries to Fiona."
                 ),
                 sam_ashes.as_tool(
                     tool_name="Sam_Ashes",
                     tool_description="Delegate testing tasks (npm test, pytest) to Sam."
                 ),
             ],
             mcp_servers=mcp_servers
        )
        # --- End tool variable usage ---

        fiona_flame.tools.append(
            sam_ashes.as_tool(tool_name="Sam_Ashes", tool_description="Delegate testing tasks (npm test, pytest) to Sam.")
        )

        logger.debug("Burnt Noodles agent team created successfully. Michael Toasted is the starting agent.")
        return michael_toasted

    async def run(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Main execution entry point for the Burnt Noodles blueprint.
        Delegates to _run_non_interactive for CLI-like execution.
        """
        logger.info("BurntNoodlesBlueprint run method called.")
        instruction = messages[-1].get("content", "") if messages else ""
        async for chunk in self._run_non_interactive(instruction, **kwargs):
            yield chunk
        logger.info("BurntNoodlesBlueprint run method finished.")

    async def _run_non_interactive(self, instruction: str, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Helper to run the agent flow based on an instruction."""
        logger.info(f"Running Burnt Noodles non-interactively with instruction: '{instruction[:100]}...'")
        mcp_servers = kwargs.get("mcp_servers", [])
        starting_agent = self.create_starting_agent(mcp_servers=mcp_servers)
        runner = Runner(agent=starting_agent)
        try:
            final_result = await runner.run(instruction)
            logger.info(f"Non-interactive run finished. Final Output: {final_result.final_output}")
            yield { "messages": [ {"role": "assistant", "content": final_result.final_output} ] }
        except Exception as e:
            logger.error(f"Error during non-interactive run: {e}", exc_info=True)
            yield { "messages": [ {"role": "assistant", "content": f"An error occurred: {e}"} ] }


# Standard Python entry point for direct script execution
if __name__ == "__main__":
    BurntNoodlesBlueprint.main()

