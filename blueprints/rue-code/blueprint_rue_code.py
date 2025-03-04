"""
Rue-Code: Automated Development Team Blueprint

This blueprint sets up an automated task-oriented coding assistant team with specialized agents for coordination, code development, system architecture, unit testing/git management, and dedicated git revision management.

This blueprint now includes full implementations of core functions from the previous Roo-Code project.
"""

import os
import re
import logging
import subprocess
from typing import Dict, Any, List

from swarm.extensions.blueprint import BlueprintBase
from swarm.types import Agent

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# Core Functions Implementations

def execute_command(command: str) -> None:
    """
    Executes a CLI command and logs its output.
    """
    try:
        logger.debug(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logger.debug(f"Command output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with error: {e.stderr}")

def read_file(path: str, include_line_numbers: bool = False) -> str:
    """
    Reads the content of a file located at 'path'.
    """
    try:
        logger.debug(f"Reading file at: {path}")
        with open(path, "r", encoding="utf-8") as f:
            if include_line_numbers:
                content = ''.join(f'{i + 1}: {line}' for i, line in enumerate(f))
            else:
                content = f.read()
            return content
    except Exception as e:
        logger.error(f"Error reading file at {path}: {e}")
        return ""

def write_to_file(path: str, content: str) -> None:
    """
    Writes 'content' to a file at 'path'. Overwrites any existing content.
    """
    try:
        logger.debug(f"Writing to file at: {path}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.debug("Write successful.")
    except Exception as e:
        logger.error(f"Error writing to file at {path}: {e}")

def write_md_file(path: str, content: str) -> None:
    """
    Writes 'content' to a Markdown file at 'path'. Only allows writing to files ending with '.md'.
    """
    if not path.endswith(".md"):
        logger.error(f"Architect can only write to Markdown files (*.md): {path}")
        return
    write_to_file(path, content)

def apply_diff(path: str, search: str, replace: str) -> None:
    """
    Applies a simple diff by replacing occurrences of 'search' with 'replace' in the file at 'path'.
    """
    try:
        logger.debug(f"Applying diff in file at: {path}")
        original = read_file(path)
        if not original:
            logger.error("Original content empty; diff not applied.")
            return
        updated = original.replace(search, replace)
        write_to_file(path, updated)
        logger.debug("Diff applied successfully.")
    except Exception as e:
        logger.error(f"Error applying diff in file at {path}: {e}")

def search_files(directory: str, pattern: str, recursive: bool = False, case_insensitive: bool = False) -> List[str]:
    """
    Searches for files in 'directory' whose contents match the regex 'pattern'.
    Returns a list of file paths that contain a match.
    """
    matches = []
    flags = re.IGNORECASE if case_insensitive else 0
    regex = re.compile(pattern, flags=flags)
    logger.debug(f"Grep-like search for pattern: {pattern} in directory: {directory}, Recursive: {recursive}, Case Insensitive: {case_insensitive}")
    for root, dirs, files in os.walk(directory):
        if not recursive:
            dirs.clear()

        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if regex.search(content):
                    matches.append(file_path)
                    logger.debug(f"Match found in: {file_path}")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
    return matches

def list_files(directory: str) -> List[str]:
    ''' Lists all available test and lint commands for QualityAssurance. '''
    available_commands = list_available_commands()
    logger.info(f"Available test commands: {', '.join(available_commands['test_commands'])}")
    logger.info(f"Available lint commands: {', '.join(available_commands['lint_commands'])}")
    """
    Lists all file paths (relative to 'directory') recursively.
    """
    file_list = []
    logger.debug(f"Listing files in directory: {directory}")
    for root, dirs, files in os.walk(directory):
        for file in files:
            relative_path = os.path.relpath(os.path.join(root, file), directory)
            file_list.append(relative_path)
    return file_list


def list_available_commands() -> dict:
    """Lists all available test and lint commands."""
    return {
        'test_commands': ["npm test", "uv run pytest"],
        'lint_commands': ["eslint", "flake8", "uv run pylint"]
    }

def run_commands(command: str) -> None:
    """
    Runs a test command, limited to 'npm test' and 'uv run pytest'.
    For 'uv run pytest', it appends flags to stop after the first error and to suppress warnings.
    For 'npm test', if applicable, similar flags may be added.
    """
    allowed_commands = ["npm test", "uv run pytest"]
    cmd = command.strip()
    if cmd not in allowed_commands:
        logger.error("QualityAssurance is limited to 'npm test' and 'uv run pytest'")
        return
    # Modify command for uv run pytest to stop at first error and suppress warnings
    if cmd == "uv run pytest":
        cmd = "uv run pytest -x --disable-warnings"
    # For "npm test", you might add equivalent flags if supported. Uncomment the following line if needed.
    # elif cmd == "npm test":
    #     cmd = "npm test -- --bail"
    execute_command(cmd)

def prepare_git_commit() -> None:
    """
    Runs git status and git diff, then prepares a one-line conventional commit message.
    Executes 'git add' and commits with a default conventional commit message.
    """
    logger.debug("GitManager: Preparing git commit...")
    execute_command("git status")
    execute_command("git diff")
    commit_message = "chore: update relevant files"
    execute_command(f'git add . && git commit -m "{commit_message}"')
    
def run_test_command(command: str) -> None:
    allowed = {"npm test", "uv run pytest"}
    if command in allowed:
        run_commands(command)
    else:
        logger.error("Test command not allowed")

def run_lint_command(command: str) -> None:
    allowed = {"eslint", "flake8", "uv run pylint"}
    if command in allowed:
        run_commands(command)
    else:
        logger.error("Lint command not allowed")

def pretty_print_markdown(markdown_text: str) -> None:
    """
    Pretty prints markdown content using ANSI color formatting for headers.
    """
    try:
        lines = markdown_text.splitlines()
        formatted_lines = []
        for line in lines:
            if line.startswith("#"):
                formatted_lines.append("\033[94m" + line + "\033[0m")
            else:
                formatted_lines.append(line)
        pretty_output = "\n".join(formatted_lines)
        print(pretty_output)
        logger.debug("Markdown content pretty printed.")
    except Exception as e:
        logger.error(f"Error pretty printing markdown: {e}")

def pretty_print_diff(diff_text: str) -> None:
    """
    Pretty prints diff patches with color formatting for additions and deletions.
    Additions (lines starting with '+') are green, deletions (lines starting with '-') are red.
    """
    try:
        lines = diff_text.splitlines()
        formatted_lines = []
        for line in lines:
            if line.startswith("+") and not line.startswith("+++"):
                formatted_lines.append("\033[92m" + line + "\033[0m")
            elif line.startswith("-") and not line.startswith("---"):
                formatted_lines.append("\033[91m" + line + "\033[0m")
            else:
                formatted_lines.append(line)
        pretty_output = "\n".join(formatted_lines)
        print(pretty_output)
        logger.debug("Diff patch pretty printed.")
    except Exception as e:
        logger.error(f"Error pretty printing diff: {e}")
    
# Map of tool names to their implementations
TOOLS = {
    "execute_command": execute_command,
    "read_file": read_file,
    "write_to_file": write_to_file,       # Full write for Code agent.
    "write_md_file": write_md_file,         # Restricted write for Architect.
    "apply_diff": apply_diff,
    "search_files": search_files,
    "list_files": list_files,
    "run_test_command": run_test_command,
    "run_lint_command": run_lint_command,
    "list_available_commands": list_available_commands,   # For QualityAssurance.
    "prepare_git_commit": prepare_git_commit,  # For GitManager.
    "pretty_print_markdown": pretty_print_markdown,
    "pretty_print_diff": pretty_print_diff
}


class RueCodeBlueprint(BlueprintBase):
    """
    Rue-Code Blueprint for automated development tasks.

    Agents:
      - Coordinator: Central agent managing task delegation with persistent memory.
      - Code: Responsible for coding (full write allowed); Available agents: Architect (design, Markdown writing, web search), QualityAssurance (runs tests), GitManager (revision management).
      - Architect: Provides design guidance, web search, and can only write Markdown files; Available agents: Code (full coding), QualityAssurance (runs tests), GitManager (revision management).
      - QualityAssurance: Runs test commands ("npm test" or "uv run pytest"); Available agents: Code (full coding), Architect (design), GitManager (revision management).
      - GitManager: Dedicated to git revision management; always checks git status, reviews git diff, and prepares one-line conventional commits; Available agents: Code (full coding), Architect (design), QualityAssurance (test execution).
    """
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Rue-Code: Automated Development Team Blueprint",
            "description": (
                "An automated task-oriented coding assistant team featuring a Coordinator with persistent memory, "
                "a Code agent for full-scale development, an Architect for design support and web search (Markdown-only writing), "
                "a QualityAssurance agent for test execution, and a GitManager for revision management (git status, git diff, "
                "and one-line conventional commits). This blueprint integrates core functions from the previous Roo-Code project."
            ),
            "required_mcp_servers": [
                "memory",
                "brave-search"
            ],
            "env_vars": [
                "BRAVE_API_KEY"
            ],
        }

    def create_agents(self) -> Dict[str, Agent]:
        # Retrieve environment variables.
        brave_api_key = os.getenv("BRAVE_API_KEY", "default-brave-key")

        agents: Dict[str, Agent] = {}

        # Coordinator: manages task delegation.
        coordinator_instructions = (
            "You are the Coordinator, managing task delegation with persistent memory. "
            "Available agents: Code (full coding), Architect (design, Markdown writing, web search), "
            "QualityAssurance (runs tests), GitManager (revision management)."
        )
        agents["Coordinator"] = Agent(
            name="Coordinator",
            instructions=coordinator_instructions,
            mcp_servers=["memory"],
            env_vars={},
        )

        # Code: full coding capability.
        code_instructions = (
            "You are the Code agent, responsible for writing, modifying, and analyzing code with full write access. "
            "Use tools: execute_command, read_file (with optional line numbers), write_to_file, apply_diff, list_files, pretty_print_markdown, and pretty_print_diff. "
            "Available agents: Architect (design, Markdown writing, web search), QualityAssurance (test execution), GitManager (revision management). Use line numbers in `read_file` for precise diff patches."
        )
        agents["Code"] = Agent(
            name="Code",
            instructions=code_instructions,
            mcp_servers=["memory"],
            env_vars={"BRAVE_API_KEY": brave_api_key},
        )

        # Architect: design and web search; Markdown-only writing.
        architect_instructions = (
            "You are the Architect, providing design guidance, architectural planning, and web search capabilities via search_files. "
            "Use tools: search_files (with recursive and case insensitive options), list_files, read_file (with optional line numbers), write_md_file (Markdown-only). "
            "Available agents: Code (full coding), QualityAssurance (test execution), GitManager (revision management). Use line numbers in `read_file` for precise diff patches."
        )
        agents["Architect"] = Agent(
            name="Architect",
            instructions=architect_instructions,
            mcp_servers=["brave-search"],
            env_vars={"BRAVE_API_KEY": brave_api_key},
        )

        # QualityAssurance: runs limited test commands.
        quality_assurance_instructions = (
            "You are the QualityAssurance agent, responsible for executing tests using tools limited to 'npm test' and 'uv run pytest'. "
            "Available agents: Code (full coding), Architect (design, Markdown writing), GitManager (revision management)."
        )
        agents["QualityAssurance"] = Agent(
            name="QualityAssurance",
            instructions=quality_assurance_instructions,
            mcp_servers=["memory"],
            env_vars={},
        )

        # GitManager: dedicated to git revision management.
        git_manager_instructions = (
            "You are the GitManager agent, dedicated to revision management. Always run 'git status' and 'git diff', "
            "and prepare one-line conventional commit messages using prepare_git_commit. "
            "Available agents: Code (full coding), Architect (design), QualityAssurance (test execution)."
        )
        agents["GitManager"] = Agent(
            name="GitManager",
            instructions=git_manager_instructions,
            mcp_servers=["memory"],
            env_vars={},
        )

        # Define a handoff function for returning control.
        def handoff_back_to_coordinator() -> Agent:
            return agents["Coordinator"]

        # Define delegation functions with valid names.
        def delegate_to_code() -> Agent:
            return agents["Code"]

        def delegate_to_architect() -> Agent:
            return agents["Architect"]

        def delegate_to_qualityassurance() -> Agent:
            return agents["QualityAssurance"]

        def delegate_to_gitmanager() -> Agent:
            return agents["GitManager"]

        # Assign functions for delegation.
        object.__setattr__(agents["Coordinator"], "functions", [
            delegate_to_code,
            delegate_to_architect,
            delegate_to_qualityassurance,
            delegate_to_gitmanager,
        ])
        # Each specialized agent should include a handoff function to return control.
        object.__setattr__(agents["Code"], "functions", [handoff_back_to_coordinator])
        object.__setattr__(agents["Architect"], "functions", [handoff_back_to_coordinator])
        object.__setattr__(agents["QualityAssurance"], "functions", [handoff_back_to_coordinator])
        # GitManager gets its dedicated git revision management function in addition to handing off.
        object.__setattr__(agents["GitManager"], "functions", [prepare_git_commit, handoff_back_to_coordinator])

        # Assign tool sets to agents using object.__setattr__ to bypass pydantic restrictions.
        object.__setattr__(agents["Coordinator"], "tools", {})
        object.__setattr__(agents["Code"], "tools", {
            "execute_command": TOOLS["execute_command"],
            "read_file": TOOLS["read_file"],
            "search_files": TOOLS["search_files"],
            "write_to_file": TOOLS["write_to_file"],
            "apply_diff": TOOLS["apply_diff"],
            "list_files": TOOLS["list_files"],
            "pretty_print_markdown": TOOLS["pretty_print_markdown"],
            "pretty_print_diff": TOOLS["pretty_print_diff"],
        })
        object.__setattr__(agents["Architect"], "tools", {
            "search_files": TOOLS["search_files"],
            "read_file": TOOLS["read_file"],
            "list_files": TOOLS["list_files"],
            "write_md_file": TOOLS["write_md_file"],
        })
        object.__setattr__(agents["QualityAssurance"], "tools", {
            "run_test_command": TOOLS["run_test_command"],
            "run_lint_command": TOOLS["run_lint_command"],
            "list_available_commands": TOOLS["list_available_commands"],
        })
        object.__setattr__(agents["GitManager"], "tools", {
            "execute_command": TOOLS["execute_command"],
            "prepare_git_commit": TOOLS["prepare_git_commit"],
        })

        self.set_starting_agent(agents["Coordinator"])
        logger.debug(f"Agents registered: {list(agents.keys())}")
        return agents


if __name__ == "__main__":
    RueCodeBlueprint.main()
