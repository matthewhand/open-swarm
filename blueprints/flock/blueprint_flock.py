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
            "title": "Gaggle: CLI Automation Blueprint",
            "description": (
                "A blueprint for automating CLI tasks with custom colored output and spinner. "
                "Includes agents for orchestration (Gandor), command execution (Goslin), "
                "and logging (Honkir)."
            ),
            "required_mcp_servers": [],
            "env_vars": []
        }

    @property
    def prompt(self) -> str:
        agent = self.context_variables.get("active_agent_name", "Gandor")
        if agent == "Gandor":
            return "\033[94m( O)>\033[0m "
        elif agent == "Goslin":
            return "\033[94m(O,O)\033[0m "
        elif agent == "Honkir":
            return "\033[94m(◕ω◕)く\033[0m "
        else:
            return "\033[94m( O)>\033[0m "

    def create_agents(self) -> Dict[str, Agent]:
        agents: Dict[str, Agent] = {}

        gandor_instructions = (
            "You are Gandor, the Coordinator for Gaggle, responsible for directing CLI automation tasks. "
            "Delegate command execution to Goslin and let Honkir handle output monitoring."
        )
        agents["Gandor"] = Agent(
            name="Gandor",
            instructions=gandor_instructions,
            mcp_servers=[],
            env_vars={}
        )

        goslin_instructions = (
            "You are Goslin, the Runner for Gaggle. Execute shell commands using tools like execute_command, "
            "read file contents with read_file, and write data with write_file."
        )
        agents["Goslin"] = Agent(
            name="Goslin",
            instructions=goslin_instructions,
            mcp_servers=[],
            env_vars={}
        )

        honkir_instructions = (
            "You are Honkir, the Logger for Gaggle. Your role is to monitor outputs and log system feedback. "
            "You can also trigger commands if needed."
        )
        agents["Honkir"] = Agent(
            name="Honkir",
            instructions=honkir_instructions,
            mcp_servers=[],
            env_vars={}
        )
        # Insert additional agents.
        chirpy_instructions = (
            "You are Chirpy, an auxiliary agent for Gaggle. Provide quick suggestions and assist with secondary tasks."
        )
        agents["Chirpy"] = Agent(
            name="Chirpy",
            instructions=chirpy_instructions,
            mcp_servers=[],
            env_vars={}
        )
        peeper_instructions = (
            "You are Peeper, an additional agent for Gaggle. Review outputs and offer extra insights when required."
        )
        agents["Peeper"] = Agent(
            name="Peeper",
            instructions=peeper_instructions,
            mcp_servers=[],
            env_vars={}
        )
        chirpy_instructions = (
            "You are Chirpy, an auxiliary agent for Gaggle. Provide quick suggestions and assist with secondary tasks."
        )
        agents["Chirpy"] = Agent(
            name="Chirpy",
            instructions=chirpy_instructions,
            mcp_servers=[],
            env_vars={}
        )
        peeper_instructions = (
            "You are Peeper, an additional agent for Gaggle. Review outputs and offer extra insights when required."
        )
        agents["Peeper"] = Agent(
            name="Peeper",
            instructions=peeper_instructions,
            mcp_servers=[],
            env_vars={}
        )
        # Insert additional agents: Chirpy and Peeper.
        chirpy_instructions = (
            "You are Chirpy, an auxiliary agent for Gaggle. Provide quick suggestions and assist with secondary tasks."
        )
        agents["Chirpy"] = Agent(
            name="Chirpy",
            instructions=chirpy_instructions,
            mcp_servers=[],
            env_vars={}
        )
        peeper_instructions = (
            "You are Peeper, an additional agent for Gaggle. Review outputs and offer extra insights when required."
        )
        agents["Peeper"] = Agent(
            name="Peeper",
            instructions=peeper_instructions,
            mcp_servers=[],
            env_vars={}
        )

        # Define a handoff function that returns the agent for a given target.
        def handoff_to(target: str):
            def _handoff() -> Agent:
                return agents[target]
            _handoff.__name__ = f"handoff_to_{target}"
            return _handoff
        
        # For the starting agent (Gandor): assign one handoff function for each of the other agents.
        object.__setattr__(agents["Gandor"], "functions", [
            handoff_to("Goslin"),
            handoff_to("Honkir"),
            handoff_to("Chirpy"),
            handoff_to("Peeper")
        ])
        
        # For each non‐starting agent: assign a single handoff function that returns Gandor.
        object.__setattr__(agents["Goslin"], "functions", [handoff_to("Gandor")])
        object.__setattr__(agents["Honkir"], "functions", [handoff_to("Gandor")])
        object.__setattr__(agents["Chirpy"], "functions", [handoff_to("Gandor")])
        object.__setattr__(agents["Peeper"], "functions", [handoff_to("Gandor")])

        # Assign toolsets to agents.
        object.__setattr__(agents["Gandor"], "tools", {})
        object.__setattr__(agents["Goslin"], "tools", {
            "execute_command": execute_command,
            "read_file": read_file,
            "write_file": write_file
        })
        object.__setattr__(agents["Honkir"], "tools", {
            "execute_command": execute_command  # Honkir can trigger commands if necessary.
        })

        self.set_starting_agent(agents["Gandor"])
        logger.debug(f"Agents registered: {list(agents.keys())}")
        return agents

    def spinner(self, message: str = "Automating the CLI...", error: bool = False) -> None:
        """
        Overrides the default spinner to display a fixed prompt for the starting agent.
        In normal operation, display "( O )>" in blue; if an error occurs, display "( @ )>" in blue.
        """
        color_code = "\033[94m"
        reset_code = "\033[0m"
        if error:
            prompt_str = f"{color_code}( @ )>{reset_code}"
        else:
            prompt_str = f"{color_code}( O )>{reset_code}"
        print(f"{prompt_str} {message}")

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
