"""
Flock: CLI Automation Blueprint with Custom Colored Output

This blueprint provides CLI automation capabilities with the following customizations:
  - A custom colored spinner override.
  - A custom render_output method that prints output in color on the CLI.
  - Three agents: Coordinator, Runner, and Logger.
"""

import os
import sys
import time
import logging
import subprocess
from typing import Dict, Any

from swarm.extensions.blueprint import BlueprintBase
from swarm.types import Agent

# Configure logging for our blueprint.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


def execute_command(command: str) -> None:
    """
    Executes a shell command and logs its output.
    """
    try:
        logger.debug(f"Executing command: {command}")
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.debug(f"Command output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with error: {e.stderr}")


def read_file(path: str) -> str:
    """
    Reads the file from the specified path.
    """
    try:
        logger.debug(f"Reading file at: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file at {path}: {e}")
        return ""


def write_file(path: str, content: str) -> None:
    """
    Writes content to a file at the specified path.
    """
    try:
        logger.debug(f"Writing to file at: {path}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.debug("File write successful.")
    except Exception as e:
        logger.error(f"Error writing file at {path}: {e}")


class FlockBlueprint(BlueprintBase):
    """
    Flock: CLI Automation Blueprint

    Agents:
      - Coordinator: Orchestrates overall CLI automation tasks.
      - Runner: Executes shell commands and performs file operations.
      - Logger: Monitors outputs and logs system feedback.
    """

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Flock: CLI Automation Blueprint",
            "description": (
                "A blueprint for automating CLI tasks with custom colored output and spinner. "
                "Includes agents for orchestration (Coordinator), command execution (Runner), "
                "and logging (Logger)."
            ),
            "required_mcp_servers": [],
            "env_vars": []
        }

    def create_agents(self) -> Dict[str, Agent]:
        agents: Dict[str, Agent] = {}

        coordinator_instructions = (
            "You are the Coordinator for Flock, responsible for directing CLI automation tasks. "
            "Delegate command execution to the Runner and let the Logger handle output monitoring."
        )
        agents["Coordinator"] = Agent(
            name="Coordinator",
            instructions=coordinator_instructions,
            mcp_servers=[],
            env_vars={}
        )

        runner_instructions = (
            "You are the Runner for Flock. Execute shell commands using tools like execute_command, "
            "read file contents with read_file, and write data with write_file."
        )
        agents["Runner"] = Agent(
            name="Runner",
            instructions=runner_instructions,
            mcp_servers=[],
            env_vars={}
        )

        logger_instructions = (
            "You are the Logger for Flock. Your role is to monitor outputs and log system feedback. "
            "You can also trigger commands if needed."
        )
        agents["Logger"] = Agent(
            name="Logger",
            instructions=logger_instructions,
            mcp_servers=[],
            env_vars={}
        )

        # Define a common handoff function so agents can return control to the Coordinator.
        def handoff_to_coordinator() -> Agent:
            return agents["Coordinator"]

        object.__setattr__(agents["Coordinator"], "functions", [handoff_to_coordinator])
        object.__setattr__(agents["Runner"], "functions", [handoff_to_coordinator])
        object.__setattr__(agents["Logger"], "functions", [handoff_to_coordinator])

        # Assign toolsets to agents.
        object.__setattr__(agents["Coordinator"], "tools", {})
        object.__setattr__(agents["Runner"], "tools", {
            "execute_command": execute_command,
            "read_file": read_file,
            "write_file": write_file
        })
        object.__setattr__(agents["Logger"], "tools", {
            "execute_command": execute_command  # Logger can trigger commands if necessary.
        })

        self.set_starting_agent(agents["Coordinator"])
        logger.debug(f"Agents registered: {list(agents.keys())}")
        return agents

    def spinner(self, message: str = "Automating the CLI...") -> None:
        """
        Overrides the default spinner to display a custom spinner with a different color.
        """
        spin_symbols = ["◐", "◓", "◑", "◒"]
        color_code = "\033[94m"  # Blue for spinner
        reset_code = "\033[0m"

        # Display the starting message.
        print(f"{color_code}{message}{reset_code}")
        for _ in range(8):
            for symbol in spin_symbols:
                sys.stdout.write(f"\r{color_code}{symbol} {message}{reset_code}")
                sys.stdout.flush()
                time.sleep(0.2)
        # Clear spinner on completion.
        sys.stdout.write("\r")
        sys.stdout.flush()

    def render_output(self, text: str, color: str = "green") -> None:
        """
        Renders output text on the CLI with a specified ANSI color.
        By default, it renders text in green.

        Supported colors: red, green, yellow, blue, magenta, cyan, white.
        """
        colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "magenta": "\033[95m",
            "cyan": "\033[96m",
            "white": "\033[97m",
        }
        reset_code = "\033[0m"
        color_code = colors.get(color.lower(), "\033[92m")
        print(f"{color_code}{text}{reset_code}")


if __name__ == "__main__":
    FlockBlueprint.main()
