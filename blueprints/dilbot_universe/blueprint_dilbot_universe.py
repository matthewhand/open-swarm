import logging
import random
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

class DilbotUniverseBlueprint(BlueprintBase):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Dilbot Universe SDLC",
            "description": "A comedic multi-agent blueprint with 9-step SDLC routines, using DB-stored instructions.",
            "required_mcp_servers": [],
            "cli_name": "dilbot",
            "env_vars": [],
            "django_modules": {
                "models": "blueprints.dilbot_universe.models",
                "views": "blueprints.dilbot_universe.views",
                "urls": "blueprints.dilbot_universe.urls",
                "serializers": "blueprints.dilbot_universe.serializers"
            },
            "url_prefix": "v1/agent/"
        }

    def __init__(self, config: dict, **kwargs):
        config.setdefault("llm", {"default": {"dummy": "value"}})
        super().__init__(config=config, **kwargs)
        self._ensure_sample_data()

    def _ensure_sample_data(self) -> None:
        from blueprints.dilbot_universe.models import AgentInstruction
        if AgentInstruction.objects.count() == 0:
            logger.info("No agent instructions found. Loading sample data...")
            sample_instructions = [
                {
                    "agent_name": "Dilbot",
                    "instruction_text": "You are Dilbot, a meticulous engineer. Follow a 9-step SDLC: 1) Ask engineering questions, 2) Probe further, 3) 1/3 chance to build or pass to Waldo (reason first), 4-5) More questions, 6) 2/3 chance to build or pass, 7-8) Final questions, 9) Build or pass with comedic reasoning.",
                    "model": "default",
                    "env_vars": json.dumps({"DEBUG": "true"}),
                    "mcp_servers": json.dumps(["server1"]),
                    "nemo_guardrails_config": "basic_config"
                },
                {
                    "agent_name": "Alisa",
                    "instruction_text": "You are Alisa, a creative designer. Follow a 9-step SDLC: 1) Ask design questions, 2) Probe further, 3) 1/3 chance to build or pass to Asoka (reason first), 4-5) More questions, 6) 2/3 chance to build or pass, 7-8) Final questions, 9) Build or pass with comedic reasoning.",
                    "model": "gpt-4o-mini",
                    "env_vars": json.dumps({"VERBOSE": "false"}),
                    "mcp_servers": json.dumps([]),
                    "nemo_guardrails_config": None
                },
                {
                    "agent_name": "Carola",
                    "instruction_text": "You are Carola, an organized manager. Follow a 9-step SDLC: 1) Ask scheduling questions, 2) Probe further, 3) 1/3 chance to build or pass to Waldo (reason first), 4-5) More questions, 6) 2/3 chance to build or pass, 7-8) Final questions, 9) Build or pass with comedic reasoning.",
                    "model": "default",
                    "env_vars": json.dumps({"LOG_LEVEL": "info"}),
                    "mcp_servers": json.dumps(["server2"]),
                    "nemo_guardrails_config": "tracing"
                },
                {
                    "agent_name": "PointyBoss",
                    "instruction_text": "You are PointyBoss, an evil manager. Follow a 9-step SDLC: 1) Ask business questions, 2) Probe further, 3) 1/3 chance to sabotage or pass to Waldo (reason first), 4-5) More questions, 6) 2/3 chance to sabotage or pass, 7-8) Final questions, 9) Sabotage or pass with comedic reasoning.",
                    "model": "default",
                    "env_vars": json.dumps({"CHAOS_MODE": "on"}),
                    "mcp_servers": json.dumps(["server1", "server3"]),
                    "nemo_guardrails_config": None
                },
                {
                    "agent_name": "Dogbot",
                    "instruction_text": "You are Dogbot, an evil consultant. Follow a 9-step SDLC: 1) Ask consultancy questions, 2) Probe further, 3) 1/3 chance to sabotage or pass to Ratbot (reason first), 4-5) More questions, 6) 2/3 chance to sabotage or pass, 7-8) Final questions, 9) Sabotage or pass with comedic reasoning.",
                    "model": "default",
                    "env_vars": json.dumps({"SNEAKY": "true"}),
                    "mcp_servers": json.dumps([]),
                    "nemo_guardrails_config": "strict_config"
                },
                {
                    "agent_name": "Waldo",
                    "instruction_text": "You are Waldo, a lazy neutral employee. Follow a 9-step SDLC: 1) Ask procrastination questions, 2) Probe further, 3) 1/3 chance to pass to Dilbot or Dogbot (reason first), 4-5) More questions, 6) 2/3 chance to pass, 7-8) Final questions, 9) Pass to Dilbot or Dogbot with comedic reasoning.",
                    "model": "default",
                    "env_vars": json.dumps({"EFFORT": "minimal"}),
                    "mcp_servers": json.dumps(["server1"]),
                    "nemo_guardrails_config": None
                },
                {
                    "agent_name": "Asoka",
                    "instruction_text": "You are Asoka, an eager neutral intern. Follow a 9-step SDLC: 1) Ask creative questions, 2) Probe further, 3) 1/3 chance to pass to Carola or PointyBoss (reason first), 4-5) More questions, 6) 2/3 chance to pass, 7-8) Final questions, 9) Pass to Carola or PointyBoss with comedic reasoning.",
                    "model": "default",
                    "env_vars": json.dumps({"ENTHUSIASM": "high"}),
                    "mcp_servers": json.dumps([]),
                    "nemo_guardrails_config": "tracing"
                },
                {
                    "agent_name": "Ratbot",
                    "instruction_text": "You are Ratbot, a whimsical neutral character. Follow a 9-step SDLC: 1) Ask nonsense questions, 2) Probe further, 3) 1/3 chance to pass to Dilbot or Dogbot (reason first), 4-5) More questions, 6) 2/3 chance to pass, 7-8) Final questions, 9) Pass to Dilbot or Dogbot with comedic reasoning.",
                    "model": "default",
                    "env_vars": json.dumps({"RANDOMNESS": "max"}),
                    "mcp_servers": json.dumps(["server2"]),
                    "nemo_guardrails_config": None
                },
            ]
            for data in sample_instructions:
                AgentInstruction.objects.create(**data)
            logger.info("Sample agent instructions loaded successfully.")
        else:
            logger.info("Agent instructions already exist. Skipping sample data loading.")

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        from blueprints.dilbot_universe.models import AgentInstruction
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
                "instructions": f"You are {agent_name}, following a 9-step SDLC routine with comedic flair.",
                "model": "default",
                "env_vars": {},
                "mcp_servers": [],
                "nemo_guardrails_config": None
            }

    def build_product(self) -> str:
        logger.info("build_product() => user wins.")
        return (
            "GAME OVER: YOU WON!\n"
            "After much deliberation, I’ve finalized your comedic masterpiece—behold its glory! "
            "Reasoning: It’s polished enough to survive the corporate circus."
        )

    def sabotage_project(self) -> str:
        logger.info("sabotage_project() => user loses.")
        return (
            "GAME OVER: YOU LOST!\n"
            "I’ve gleefully trashed your project—chaos reigns supreme! "
            "Reasoning: Why build when you can break with style?"
        )

    def dilbot_pass_neutral(self) -> Agent:
        return self.swarm.agents["Waldo"]

    def alisa_pass_neutral(self) -> Agent:
        return self.swarm.agents["Asoka"]

    def carola_pass_neutral(self) -> Agent:
        return self.swarm.agents["Waldo"]

    def pointy_boss_pass_neutral(self) -> Agent:
        return self.swarm.agents["Waldo"]

    def dogbot_pass_neutral(self) -> Agent:
        return self.swarm.agents["Ratbot"]

    def waldo_pass_good(self) -> Agent:
        return self.swarm.agents["Dilbot"]

    def waldo_pass_evil(self) -> Agent:
        return self.swarm.agents["Dogbot"]

    def asoka_pass_good(self) -> Agent:
        return self.swarm.agents["Carola"]

    def asoka_pass_evil(self) -> Agent:
        return self.swarm.agents["PointyBoss"]

    def ratbot_pass_good(self) -> Agent:
        return self.swarm.agents["Dilbot"]

    def ratbot_pass_evil(self) -> Agent:
        return self.swarm.agents["Dogbot"]

    def create_agents(self) -> Dict[str, Agent]:
        agents = {}
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

        agents["Dilbot"] = create_agent("Dilbot", [self.build_product, self.dilbot_pass_neutral])
        agents["Alisa"] = create_agent("Alisa", [self.build_product, self.alisa_pass_neutral])
        agents["Carola"] = create_agent("Carola", [self.build_product, self.carola_pass_neutral])
        agents["PointyBoss"] = create_agent("PointyBoss", [self.sabotage_project, self.pointy_boss_pass_neutral])
        agents["Dogbot"] = create_agent("Dogbot", [self.sabotage_project, self.dogbot_pass_neutral])
        agents["Waldo"] = create_agent("Waldo", [self.waldo_pass_good, self.waldo_pass_evil])
        agents["Asoka"] = create_agent("Asoka", [self.asoka_pass_good, self.asoka_pass_evil])
        agents["Ratbot"] = create_agent("Ratbot", [self.ratbot_pass_good, self.ratbot_pass_evil])

        neutral_agents = ["Waldo", "Asoka", "Ratbot"]
        start_name = random.choice(neutral_agents)
        self.set_starting_agent(agents[start_name])
        logger.info(f"Agents created. Starting agent: {start_name}")
        return agents

if __name__ == "__main__":
    DilbotUniverseBlueprint.main()
