import os
import logging
import json
from typing import Dict, Any, List
from swarm.types import Agent
from swarm.extensions.blueprint import BlueprintBase

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

class MIMBlueprint(BlueprintBase):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Mission: Improbable",
            "description": "A cheeky team on a mission: led by JimFlimsy with daring support from CinnamonToast and RollinFumble.",
            "cli_name": "mission",
            "required_mcp_servers": ["memory", "filesystem", "mcp-shell", "brave-search", "rag-docs"],
            "env_vars": ["BRAVE_API_KEY", "QDRANT_URL", "QDRANT_API_KEY", "ALLOWED_PATH"],
            "django_modules": {
                "models": "blueprints.mission_improbable.models",
                "views": "blueprints.mission_improbable.views",
                "urls": "blueprints.mission_improbable.urls",
                "serializers": "blueprints.mission_improbable.serializers"
            },
            "url_prefix": "v1/agent/"
        }

    def __init__(self, config: dict, **kwargs):
        config.setdefault("llm", {"default": {"dummy": "value"}})
        super().__init__(config=config, **kwargs)
        self._ensure_sample_data()

    def _ensure_sample_data(self) -> None:
        from blueprints.mission_improbable.models import AgentInstruction
        if AgentInstruction.objects.count() == 0:
            logger.info("No agent instructions found. Loading sample data...")
            sample_instructions = [
                {
                    "agent_name": "JimFlimsy",
                    "instruction_text": (
                        "You’re JimFlimsy, the fearless leader:\n"
                        "1. Start with 'Syncing systems...' and load memory.\n"
                        "2. Delegate: CinnamonToast (strategist) and RollinFumble (operative).\n"
                        "3. Log updates and maintain command."
                    ),
                    "model": "default",
                    "env_vars": json.dumps({"DEBUG": "true"}),
                    "mcp_servers": json.dumps(["memory"]),
                    "nemo_guardrails_config": "tracing"
                },
                {
                    "agent_name": "CinnamonToast",
                    "instruction_text": (
                        "You’re CinnamonToast, the quick-witted strategist:\n"
                        "1. Manage files—create, read, delete and report actions.\n"
                        "2. Return control to JimFlimsy."
                    ),
                    "model": "gpt-4o-mini",
                    "env_vars": json.dumps({"ALLOWED_PATH": os.getenv("ALLOWED_PATH", "/tmp")}),
                    "mcp_servers": json.dumps(["filesystem"])
                },
                {
                    "agent_name": "RollinFumble",
                    "instruction_text": (
                        "You’re RollinFumble, the unpredictable operative:\n"
                        "1. Execute commands and summarize output.\n"
                        "2. Return control to JimFlimsy."
                    ),
                    "model": "default",
                    "env_vars": json.dumps({}),
                    "mcp_servers": json.dumps(["mcp-shell"])
                }
            ]
            for data in sample_instructions:
                AgentInstruction.objects.create(**data)
            logger.info("Sample agent instructions loaded successfully.")
        else:
            logger.info("Agent instructions already exist. Skipping sample data loading.")

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        from blueprints.mission_improbable.models import AgentInstruction
        try:
            instruction = AgentInstruction.objects.get(agent_name=agent_name)
            return {
                "instructions": instruction.instruction_text,
                "model": instruction.model,
                "env_vars": json.loads(instruction.env_vars) if instruction.env_vars else {},
                "mcp_servers": json.loads(instruction.mcp_servers) if instruction.mcp_servers else [],
                "nemo_guardrails_config": instruction.nemo_guardrails_config
            }
        except AgentInstruction.DoesNotExist:
            logger.warning(f"No config found for agent '{agent_name}'. Using defaults.")
            return {
                "instructions": f"You are {agent_name}, a NexusForce operative.",
                "model": "default",
                "env_vars": {},
                "mcp_servers": [],
                "nemo_guardrails_config": None
            }

    def echo_command(self, cmd: str) -> str:
        logger.info(f"Echoing command: {cmd}")
        return f"Command echoed: {cmd}"

    def handoff_to_valkyrie(self) -> Agent:
        return self.swarm.agents["Valkyrie"]

    def handoff_to_tempest(self) -> Agent:
        return self.swarm.agents["Tempest"]

    def handoff_to_zephyr(self) -> Agent:
        return self.swarm.agents["Zephyr"]

    def handoff_to_core(self) -> Agent:
        return self.swarm.agents["NovaCore"]

    def create_agents(self) -> Dict[str, Agent]:
        def create_agent(name: str, functions: List) -> Agent:
            config = self.get_agent_config(name)
            return Agent(
                name=name,
                instructions=lambda ctx: config["instructions"],
                functions=functions,
                model=config["model"],
                env_vars=config["env_vars"],
                mcp_servers=config["mcp_servers"],
                nemo_guardrails_config=config["nemo_guardrails_config"]
            )

        agents = {}
        agents["JimFlimsy"] = create_agent(
            "JimFlimsy",
            ["You are JimFlimsy, the fearless leader: begin by syncing systems and delegate tasks with precision."]
        )
        agents["CinnamonToast"] = create_agent(
            "CinnamonToast",
            ["You are CinnamonToast, the quick-witted strategist: manage operations and advise with flair."]
        )
        agents["RollinFumble"] = create_agent(
            "RollinFumble",
            ["You are RollinFumble, the unpredictable operative: execute commands with quirky precision."]
        )
        self.set_starting_agent(agents["JimFlimsy"])
        logger.info("Agents created: JimFlimsy, CinnamonToast, RollinFumble.")
        return agents

if __name__ == "__main__":
    MIMBlueprint.main()
