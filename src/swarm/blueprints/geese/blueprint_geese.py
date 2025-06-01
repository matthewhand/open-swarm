import asyncio
import json
import logging
import os
import random
import sys
import textwrap
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast, AsyncGenerator

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

# Core Swarm imports
from swarm.core.blueprint_base import BlueprintBase
from swarm.core.blueprint_ux import BlueprintUXImproved
from swarm.core.interaction_types import AgentInteraction
from swarm.core.tool_utils import tool
# from swarm.core.mcp_server_classes import MCPServer # REMOVE THIS - Incorrect custom MCPServer

# SDK Imports - Agent and MCPServer should come from here
from agents import Agent # This was used in BlueprintBase.make_agent
from agents.mcp import MCPServer # CORRECTED IMPORT for MCPServer from SDK - adjust if path is different (e.g. agents.mcp.server.MCPServer)

# Local Geese imports
from .agent_geese_coordinator import GooseCoordinator
from .agent_geese_writer import WriterAgent
from .agent_geese_editor import EditorAgent
from .agent_geese_researcher import ResearcherAgent
from .geese_memory_objects import StoryElement, StoryOutline, StoryContext, StoryOutput
from .geese_prompts import (
    COORDINATOR_PROMPT, WRITER_PROMPT, EDITOR_PROMPT, RESEARCHER_PROMPT,
    OUTLINE_GENERATION_PROMPT, STORY_PART_WRITING_PROMPT, EDITING_PROMPT
)
from .geese_spinner import GeeseSpinner

logger = logging.getLogger(__name__)
CONSOLE = Console()

ExpectedAgentClass = Agent 

class GeeseBlueprint(BlueprintBase):
    VERSION = "0.2.1"

    def __init__(self, blueprint_id: str, config_path: str | None = None, **kwargs: Any):
        style = kwargs.pop('style', 'silly')
        super().__init__(blueprint_id, config_path=config_path, **kwargs)
        
        self.ux = BlueprintUXImproved(style=style)

        # These mcp_servers are expected to be instances of the SDK's MCPServer or its subclasses
        self.mcp_servers: List[MCPServer] = kwargs.get('mcp_servers', [])
        self.agent_mcp_assignments_config: Dict[str, List[MCPServer]] = kwargs.get('agent_mcp_assignments_config', {})
        logger.debug(f"GeeseBlueprint '{self.blueprint_id}' __init__: agent_mcp_assignments_config = {self.agent_mcp_assignments_config}")
        
        self._llm_profile_name = self._resolve_llm_profile()
        logger.debug(f"GeeseBlueprint '{self.blueprint_id}': Using LLM profile name '{self._llm_profile_name}'.")

        self.llm = self._get_model_instance(self._llm_profile_name) 
        logger.debug(f"GeeseBlueprint '{self.blueprint_id}': LLM instance type: {type(self.llm)}.")

        self.coordinator_agent: GooseCoordinator = self._create_agent(GooseCoordinator, "GooseCoordinator", COORDINATOR_PROMPT)
        self.writer_agent: WriterAgent = self._create_agent(WriterAgent, "WriterAgent", WRITER_PROMPT)
        self.editor_agent: EditorAgent = self._create_agent(EditorAgent, "EditorAgent", EDITING_PROMPT)
        self.researcher_agent: ResearcherAgent = self._create_agent(ResearcherAgent, "ResearcherAgent", RESEARCHER_PROMPT)

        self.coordinator_agent.writer = self.writer_agent
        self.coordinator_agent.editor = self.editor_agent
        self.coordinator_agent.researcher = self.researcher_agent
        logger.info(f"GeeseBlueprint '{self.blueprint_id}': Coordinator and sub-agents created.")
        self.spinner = GeeseSpinner(console=self.ux.console)

    def _get_assigned_mcps_for_agent(self, agent_name: str) -> List[MCPServer]: # Type hint uses SDK MCPServer
        if agent_name in self.agent_mcp_assignments_config:
            assigned_by_name = self.agent_mcp_assignments_config[agent_name]
            logger.debug(f"MCPs for {agent_name} (direct assign): {[s.name for s in assigned_by_name if hasattr(s, 'name')]}")
            return assigned_by_name
        logger.debug(f"MCPs for {agent_name} (blueprint default): {[s.name for s in self.mcp_servers if hasattr(s, 'name')]}")
        return self.mcp_servers

    def _create_agent(self, agent_class: type[Agent], agent_name: str, system_prompt: str) -> Any:
        assigned_mcps = self._get_assigned_mcps_for_agent(agent_name) # List of SDK MCPServer instances
        
        agent_instance = agent_class(
            name=agent_name, 
            model=self.llm, 
            instructions=system_prompt, 
            mcp_servers=assigned_mcps, # Pass SDK MCPServer instances to the SDK Agent
            blueprint_id=self.blueprint_id, 
            max_llm_calls=self._config.get('blueprints', {}).get(self.blueprint_id, {}).get('max_llm_calls', 10)
        )
        logger.debug(f"Created agent {agent_name} (type: {agent_class.__name__}) with MCPs: {[s.name for s in assigned_mcps if hasattr(s, 'name')]}")
        return agent_instance

    def display_splash_screen(self, style: str = "default", message: Optional[str] = None) -> None:
        title = " geese ".center(30, '·')
        header = f"HONK! Welcome to Geese v{self.VERSION}! HONK!"
        default_message = "A multi-agent story generation system. Prepare for a cacophony of creativity!"
        content = message or default_message
        splash_box = self.ux.ansi_emoji_box(
            title=header, content=content, summary=title,
            style=style if style != "default" else self.ux.style, emoji="🦢"
        )
        self.ux.console.print(splash_box)

    async def run(self, messages: List[Dict[str, Any]], **kwargs: Any) -> AsyncGenerator[AgentInteraction, None]:
        self.display_splash_screen()
        user_prompt = messages[-1]["content"] if messages and messages[-1]["role"] == "user" else "Tell me a story about a brave goose."
        logger.info(f"GeeseBlueprint run initiated with prompt: {user_prompt}")
        self.spinner.start("Orchestrating the flock...")
        story_context = StoryContext(user_prompt=user_prompt)
        final_story_output: Optional[StoryOutput] = None
        try:
            async for sdk_interaction_chunk in self.coordinator_agent.run(
                messages=[{"role": "user", "content": user_prompt}],
                **{'story_context': story_context} 
            ):
                if isinstance(sdk_interaction_chunk, str):
                    self.spinner.update_message(sdk_interaction_chunk)
                elif isinstance(sdk_interaction_chunk, dict):
                    if "story_output" in sdk_interaction_chunk: 
                        final_story_output = sdk_interaction_chunk["story_output"]
                        current_part = sdk_interaction_chunk.get("current_part_title", "Working...")
                        self.spinner.update_message(f"Coordinator working on: {current_part}")

            if not final_story_output and hasattr(self.coordinator_agent, 'get_final_story_output'):
                 final_story_output = self.coordinator_agent.get_final_story_output()

        except Exception as e:
            logger.error(f"Error during Geese story generation: {e}", exc_info=True)
            self.spinner.stop()
            self.ux.console.print(Panel(Text(f"An error occurred: {e}", style="bold red"), title="Error"))
            yield AgentInteraction(type="error", error_message=str(e), final=True) 
            return
        self.spinner.stop()

        if final_story_output and final_story_output.final_story:
            logger.info("GeeseBlueprint story generation complete.")
            self.ux.console.print(Panel(Markdown(final_story_output.final_story), title="📜 Your Generated Story 📜", border_style="green"))
            yield AgentInteraction(
                type="message", role="assistant", content=final_story_output.final_story,
                final=True, data=final_story_output.to_dict()
            )
        else:
            logger.warning("GeeseBlueprint did not produce a final story.")
            self.ux.console.print(Panel("No story was generated. The geese seem to be on strike.", title="Result", border_style="yellow"))
            yield AgentInteraction(type="message", role="assistant", content="No story generated.", final=True)

    @tool(name="geese_request_research", description="Requests the ResearcherAgent to find information on a topic.")
    async def request_research(self, topic: str) -> str:
        logger.info(f"GeeseBlueprint tool 'request_research' called for topic: {topic}")
        full_response_content = ""
        try:
            async for interaction_chunk in self.researcher_agent.run(messages=[{"role": "user", "content": f"Research: {topic}"}]):
                if hasattr(interaction_chunk, 'content') and isinstance(interaction_chunk.content, str):
                    full_response_content += interaction_chunk.content
                if hasattr(interaction_chunk, 'final') and interaction_chunk.final:
                    break 
            return full_response_content.strip() if full_response_content else f"No research results found for '{topic}'."
        except Exception as e:
            logger.error(f"Error in request_research tool for topic '{topic}': {e}", exc_info=True)
            return f"Error researching '{topic}': {e}"
