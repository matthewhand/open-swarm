"""
Gaggle: CLI Automation Blueprint with Custom Colored Output

This blueprint is a fork of Gotchaman, demonstrating CLI automation capabilities with a custom set of characters:
  - Harvey Birdman
  - Foghorn Leghorn
  - Daffy Duck
  - Big Bird
Each character has a unique ANSI prompt and role descriptors.
"""

import os
import sys
import time
import logging
import subprocess
import itertools
from typing import Dict, Any

from swarm.extensions.blueprint import BlueprintBase
from swarm.types import Agent

import threading, time
class GaggleSpinner:
    def __init__(self):
        self.running = False
        self.thread = None
        self.status = ""
    def start(self, status: str = "Automating the CLI..."):
        if self.running:
            return
        self.running = True
        self.status = status
        def spinner_thread():
            spin_symbols = ["<(^_^)>", "<(~_~)>", "<(O_O)>", "<(>_<)>"]
            index = 0
            while self.running:
                symbol = spin_symbols[index % len(spin_symbols)]
                sys.stdout.write(f"\r\033[92m{symbol}\033[0m {self.status}")
                sys.stdout.flush()
                index += 1
                time.sleep(0.2)
        import threading
        th = threading.Thread(target=spinner_thread, daemon=True)
        th.start()
        self.thread = th
    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.thread:
            self.thread.join()
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

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

class GaggleBlueprint(BlueprintBase):
    """
    Gaggle: CLI Automation Blueprint

    Characters:
      - Harvey Birdman: PaperPusher
      - Foghorn Leghorn: NoiseBoss
      - Daffy Duck: ChaosDuck
      - Big Bird: HugMonger
    """
    def __init__(self, config: dict, **kwargs):
       super().__init__(config, **kwargs)
       self.spinner = GaggleSpinner()

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Gaggle: CLI Automation Blueprint",
            "description": (
                "A blueprint for automating CLI tasks with custom colored output and a set of pop-culture bird characters. "
                "Each character demonstrates a different ANSI prompt and specialized role."
            ),
            "required_mcp_servers": ["mondayDotCom", "basic-memory", "mcp-doc-forge", "getzep"],
            "env_vars": ["MONDAY_API_KEY", "GETZEP_API_KEY"]
        }

    @property
    def prompt(self) -> str:
        agent = self.context_variables.get("active_agent_name", "Harvey Birdman")
        if agent == "Harvey Birdman":
            return "\033[94m(v>~)\033[0m "
        elif agent == "Foghorn Leghorn":
            return "\033[94m(O>!)\033[0m "
        elif agent == "Daffy Duck":
            return "\033[94m(O>=)\033[0m "
        else:
            return "\033[94m(OO>)\033[0m "

    def create_agents(self) -> Dict[str, Agent]:
        agents: Dict[str, Agent] = {}

        # Starting agent
        agents["Harvey Birdman"] = Agent(
            name="Harvey Birdman",
            instructions="You are Harvey Birdman: LegalLimp & PaperPusher. Provide legal assistance and handle paperwork tasks.",
            mcp_servers=[],
            env_vars={}
        )
        # Non-starting agents
        agents["Foghorn Leghorn"] = Agent(
            name="Foghorn Leghorn",
            instructions="You are Foghorn Leghorn: NoiseBoss & StrutLord. Oversee loud announcements and maintain swagger.",
            mcp_servers=[],
            env_vars={}
        )
        agents["Daffy Duck"] = Agent(
            name="Daffy Duck",
            instructions="You are Daffy Duck: ChaosDuck & QuackFixer. Embrace chaos and offer creative, if wacky, solutions.",
            mcp_servers=[],
            env_vars={}
        )
        agents["Big Bird"] = Agent(
            name="Big Bird",
            instructions="You are Big Bird: FluffTank & HugMonger. Provide comfort, positivity, and large scale presence to tasks.",
            mcp_servers=[],
            env_vars={}
        )

        # Define a handoff function that returns the specified agent.
        def handoff_to(target: str):
            def _handoff() -> Agent:
                return agents[target]
            _handoff.__name__ = f"handoff_to_{target}"
            return _handoff

        # For Harvey Birdman, assign one handoff function for each non-starting agent.
        object.__setattr__(agents["Harvey Birdman"], "functions", [
            handoff_to("Foghorn Leghorn"),
            handoff_to("Daffy Duck"),
            handoff_to("Big Bird")
        ])
        # For each non-starting agent, assign a single handoff function that returns Harvey Birdman.
        object.__setattr__(agents["Foghorn Leghorn"], "functions", [handoff_to("Harvey Birdman")])
        object.__setattr__(agents["Daffy Duck"], "functions", [handoff_to("Harvey Birdman")])
        object.__setattr__(agents["Big Bird"], "functions", [handoff_to("Harvey Birdman")])

        # Assign toolsets to agents.
        object.__setattr__(agents["Harvey Birdman"], "tools", {
            "execute_command": execute_command,
            "read_file": read_file,
            "write_file": write_file
        })
        object.__setattr__(agents["Foghorn Leghorn"], "tools", {
            "execute_command": execute_command
        })
        object.__setattr__(agents["Daffy Duck"], "tools", {
            "execute_command": execute_command
        })
        object.__setattr__(agents["Big Bird"], "tools", {
            "execute_command": execute_command
        })

        # Set starting agent as Harvey Birdman
        self.set_starting_agent(agents["Harvey Birdman"])

        logger.debug(f"Agents registered: {list(agents.keys())}")
        return agents


    def render_output(self, text: str, color: str = "green") -> None:
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
    GaggleBlueprint.main()