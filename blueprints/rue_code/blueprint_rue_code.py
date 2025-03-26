"""
Rue-Code: Automated Development Team Blueprint

This blueprint establishes an automated task-oriented coding assistant team with specialized agents for coordination, code development, system architecture, unit testing/git management, and dedicated git revision management. Enhanced with improved handoffs and shared instructions for efficiency.
"""

import os
import re
import logging
import subprocess
from typing import Dict, Any, List

from swarm.extensions.blueprint import BlueprintBase
from swarm.types import Agent

# Configure logging—gotta keep tabs on everything
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

# Core Functions—same gear, just polished up
def execute_command(command: str) -> None:
    try:
        logger.debug(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logger.debug(f"Command output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with error: {e.stderr}")

def read_file(path: str, include_line_numbers: bool = False) -> str:
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
    try:
        logger.debug(f"Writing to file at: {path}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.debug("Write successful.")
    except Exception as e:
        logger.error(f"Error writing to file at {path}: {e}")

def write_md_file(path: str, content: str) -> None:
    if not path.endswith(".md"):
        logger.error(f"Architect can only write to Markdown files (*.md): {path}")
        return
    write_to_file(path, content)

def apply_diff(path: str, search: str, replace: str) -> None:
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
    file_list = []
    logger.debug(f"Listing files in directory: {directory}")
    for root, dirs, files in os.walk(directory):
        for file in files:
            relative_path = os.path.relpath(os.path.join(root, file), directory)
            file_list.append(relative_path)
    return file_list

def list_available_commands() -> dict:
    return {
        "test_commands": ["npm test", "uv run pytest"],
        "lint_commands": ["eslint", "flake8", "uv run pylint"]
    }

def run_commands(command: str) -> None:
    allowed_commands = ["npm test", "uv run pytest"]
    cmd = command.strip()
    if cmd not in allowed_commands:
        logger.error("QualityAssurance is limited to 'npm test' and 'uv run pytest'")
        return
    if cmd == "uv run pytest":
        cmd = "uv run pytest --disable-warnings"
    execute_command(cmd)

def prepare_git_commit() -> None:
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

# Tool map—same reliable kit
TOOLS = {
    "execute_command": execute_command,
    "read_file": read_file,
    "write_to_file": write_to_file,
    "write_md_file": write_md_file,
    "apply_diff": apply_diff,
    "search_files": search_files,
    "list_files": list_files,
    "run_test_command": run_test_command,
    "run_lint_command": run_lint_command,
    "list_available_commands": list_available_commands,
    "prepare_git_commit": prepare_git_commit,
    "pretty_print_markdown": pretty_print_markdown,
    "pretty_print_diff": pretty_print_diff
}

class RueCodeBlueprint(BlueprintBase):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Rue-Code: Automated Development Team Blueprint",
            "description": (
                "An efficient automated coding team featuring a Coordinator with robust memory, "
                "a Code agent for development tasks, an Architect for design and web searches (Markdown only), "
                "a QualityAssurance agent for testing, and a GitManager for revision control. Enhanced with seamless handoffs."
            ),
            "required_mcp_servers": ["memory", "brave-search"],
            "env_vars": ["BRAVE_API_KEY"]
        }

    def create_agents(self) -> Dict[str, Agent]:
        brave_api_key = os.getenv("BRAVE_API_KEY", "default-brave-key")
        agents: Dict[str, Agent] = {}

        # Shared instructions—every agent gets the memo
        shared_instructions = (
            "You’re part of the Rue-Code team. Here’s the lineup:\n"
            "- Coordinator: Oversees operations, delegates tasks. Use delegate_to_<agent>() to assign work.\n"
            "- Code: Handles coding tasks, uses execute_command, read_file (with line numbers), write_to_file, apply_diff, list_files, pretty_print_markdown, pretty_print_diff. Assign coding tasks with delegate_to_code().\n"
            "- Architect: Manages design and web searches, Markdown only with search_files (recursive/case-insensitive), read_file, list_files, write_md_file. Assign design/web tasks with delegate_to_architect().\n"
            "- QualityAssurance: Executes tests, runs npm test or uv run pytest with run_test_command, run_lint_command, list_available_commands. Assign test tasks with delegate_to_qualityassurance().\n"
            "- GitManager: Manages git operations with execute_command, prepare_git_commit. Assign git tasks with delegate_to_gitmanager().\n"
            "Return tasks to the Coordinator with handoff_back_to_coordinator() when complete."
        )

        # Handoff and delegation functions—smooth as silk
        def handoff_back_to_coordinator() -> Agent:
            logger.debug("Handoff back to Coordinator initiated!")
            return agents["Coordinator"]

        def delegate_to_code() -> Agent:
            logger.debug("Delegating to Code agent!")
            return agents["Code"]

        def delegate_to_architect() -> Agent:
            logger.debug("Delegating to Architect agent!")
            return agents["Architect"]

        def delegate_to_qualityassurance() -> Agent:
            logger.debug("Delegating to QualityAssurance agent!")
            return agents["QualityAssurance"]

        def delegate_to_gitmanager() -> Agent:
            logger.debug("Delegating to GitManager agent!")
            return agents["GitManager"]

        # Coordinator—leads the charge, no tools needed
        agents["Coordinator"] = Agent(
            name="Coordinator",
            instructions=(
                f"{shared_instructions}\n\n"
                "You’re the Coordinator, in charge of operations. Delegate tasks efficiently:\n"
                "- Coding tasks (writing, diffs): delegate_to_code()\n"
                "- Design/web searches (Markdown): delegate_to_architect()\n"
                "- Testing (npm test, pytest): delegate_to_qualityassurance()\n"
                "- Git operations (status, commits): delegate_to_gitmanager()"
            ),
            functions=[delegate_to_code, delegate_to_architect, delegate_to_qualityassurance, delegate_to_gitmanager],
            mcp_servers=["memory"],
            env_vars={}
        )

        # Code—equipped for all coding needs
        agents["Code"] = Agent(
            name="Code",
            instructions=(
                f"{shared_instructions}\n\n"
                "You’re the Code agent, tasked with development. Write code, apply diffs, and read with line numbers for precision. "
                "For design or web searches, use delegate_to_architect(). For tests, use delegate_to_qualityassurance(). For git, use delegate_to_gitmanager()."
            ),
            functions=[handoff_back_to_coordinator, delegate_to_architect, delegate_to_qualityassurance, delegate_to_gitmanager],
            # Code agent might need access to tools based on instruction
            tools={
                 "execute_command": TOOLS["execute_command"],
                 "read_file": TOOLS["read_file"],
                 "write_to_file": TOOLS["write_to_file"],
                 "apply_diff": TOOLS["apply_diff"],
                 "list_files": TOOLS["list_files"],
                 "pretty_print_markdown": TOOLS["pretty_print_markdown"],
                 "pretty_print_diff": TOOLS["pretty_print_diff"]
            },
            mcp_servers=["memory"],
            env_vars={"BRAVE_API_KEY": brave_api_key}
        )

        # Architect—focused on design and web, Markdown only
        agents["Architect"] = Agent(
            name="Architect",
            instructions=(
                f"{shared_instructions}\n\n"
                "You’re the Architect, responsible for design and web searches. Write only in Markdown. "
                "For coding, use delegate_to_code(). For tests, use delegate_to_qualityassurance(). For git, use delegate_to_gitmanager()."
            ),
            functions=[handoff_back_to_coordinator, delegate_to_code, delegate_to_qualityassurance, delegate_to_gitmanager],
            tools={
                "search_files": TOOLS["search_files"],
                "read_file": TOOLS["read_file"],
                "list_files": TOOLS["list_files"],
                "write_md_file": TOOLS["write_md_file"]
            },
            mcp_servers=["brave-search"],
            env_vars={"BRAVE_API_KEY": brave_api_key}
        )

        # QualityAssurance—dedicated to testing
        agents["QualityAssurance"] = Agent(
            name="QualityAssurance",
            instructions=(
                f"{shared_instructions}\n\n"
                "You’re QualityAssurance, focused on testing. Run npm test or uv run pytest. "
                "For coding, use delegate_to_code(). For design/web, use delegate_to_architect(). For git, use delegate_to_gitmanager()."
            ),
            functions=[handoff_back_to_coordinator, delegate_to_code, delegate_to_architect, delegate_to_gitmanager],
            tools={
                "run_test_command": TOOLS["run_test_command"],
                "run_lint_command": TOOLS["run_lint_command"],
                "list_available_commands": TOOLS["list_available_commands"]
            },
            mcp_servers=["memory"],
            env_vars={}
        )

        # GitManager—handles all git operations
        agents["GitManager"] = Agent(
            name="GitManager",
            instructions=(
                f"{shared_instructions}\n\n"
                "You’re GitManager, in charge of revision control. Manage git status, diffs, and commits. "
                "For coding, use delegate_to_code(). For design/web, use delegate_to_architect(). For tests, use delegate_to_qualityassurance()."
            ),
            # Functions are for delegation/handoff, actual operations are tools
            functions=[handoff_back_to_coordinator, delegate_to_code, delegate_to_architect, delegate_to_qualityassurance],
            tools={
                "execute_command": TOOLS["execute_command"],
                "prepare_git_commit": TOOLS["prepare_git_commit"]
            },
            mcp_servers=["memory"],
            env_vars={}
        )

        self.set_starting_agent(agents["Coordinator"])
        logger.debug(f"Agents initialized: {list(agents.keys())}")
        return agents

if __name__ == "__main__":
    RueCodeBlueprint.main()
