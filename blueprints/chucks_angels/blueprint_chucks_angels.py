import logging
import os
from typing import Dict, Any

from swarm.types import Agent
from swarm.extensions.blueprint import BlueprintBase

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

class TaskRiserBlueprint(BlueprintBase):
    """
    Blueprint for managing transcripts, computations, Flowise API, and compute resources with UVX servers.

    Features a coordinator (Greg) delegating to agents for transcript handling (Tom), computations (Louis),
    and Flowise API/compute management (Lasse), all WIP due to UVX server status.
    """
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "TaskRiser",
            "description": "Manages transcripts, computations, Flowise API, and compute resources (WIP).",
            "required_mcp_servers": ["youtube-transcript", "wolframalpha-llm-mcp", "mcp-flowise", "sqlite-uvx", "fly", "mcp-llms-txt"],
            "cli_name": "chuck",
            "env_vars": ["WOLFRAM_LLM_APP_ID", "FLY_API_TOKEN"]
        }

    def handoff_to_tom(self) -> Agent:
        return self.swarm.agents["Tom"]
    def handoff_to_louis(self) -> Agent:
        return self.swarm.agents["Louis"]
    def handoff_to_lasse(self) -> Agent:
        return self.swarm.agents["Lasse"]
    def handoff_to_greg(self) -> Agent:
        return self.swarm.agents["Greg"]

    def create_agents(self) -> Dict[str, Agent]:
        agents = {}
        agents["Greg"] = Agent(
            name="Greg",
            instructions="You are Greg, the coordinator. Delegate tasks to Tom, Louis, or Lasse.",
            functions=[self.handoff_to_tom, self.handoff_to_louis, self.handoff_to_lasse]
        )
        agents["Tom"] = Agent(
            name="Tom",
            instructions="You are Tom, managing transcripts with youtube-transcript and storing in sqlite-uvx.",
            functions=[self.handoff_to_greg],
            mcp_servers=["youtube-transcript", "sqlite-uvx"]
        )
        agents["Louis"] = Agent(
            name="Louis",
            instructions="You are Louis, handling computations with wolframalpha-llm-mcp.",
            functions=[self.handoff_to_greg],
            mcp_servers=["wolframalpha-llm-mcp"],
            env_vars={"WOLFRAM_LLM_APP_ID": os.getenv("WOLFRAM_LLM_APP_ID", "")}
        )
        agents["Lasse"] = Agent(
            name="Lasse",
            instructions="You are Lasse, managing Flowise API and compute resources with mcp-flowise and fly.",
            functions=[self.handoff_to_greg],
            mcp_servers=["mcp-flowise", "fly"],
            env_vars={"FLY_API_TOKEN": os.getenv("FLY_API_TOKEN", "")}
        )
        self.set_starting_agent(agents["Greg"])
        logger.info("Agents created: Greg, Tom, Louis, Lasse.")
        return agents

if __name__ == "__main__":
    TaskRiserBlueprint.main()
