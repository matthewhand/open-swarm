import logging
import asyncio
from typing import Dict, List, Any, AsyncGenerator, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live
import time
import os 
import sys 
import json 

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')) 
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

from swarm.core.blueprint_base import BlueprintBase
from swarm.core.blueprint_ux import BlueprintUXImproved 

try:
    from agents import Agent, Tool, function_tool, Runner 
    from agents.mcp import MCPServer as ActualMCPServerType
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
except ImportError as e:
    try:
        from swarm.core.agent import Agent 
        from swarm.core.llm import LLMConfig 
        print(f"Note: Using fallback imports for agents/models due to: {e}")
    except ImportError:
        print(f"CRITICAL ERROR: Core components (Agent, LLMConfig, etc.) or 'agents' library not found: {e}")
        sys.exit(1)


logger = logging.getLogger(__name__)

def _create_story_outline(topic: str) -> str:
    logger.info(f"Tool: Generating outline for: {topic}")
    return f"Story Outline for '{topic}':\n1. Beginning...\n2. Middle...\n3. End..."
@function_tool
def create_story_outline(topic: str) -> str: return _create_story_outline(topic)

def _write_story_part(part_name: str, outline: str, previous_parts: str) -> str:
    logger.info(f"Tool: Writing story part: {part_name}")
    return f"## {part_name}\nContent for {part_name} based on outline: {outline} and previous: {previous_parts}"
@function_tool
def write_story_part(part_name: str, outline: str, previous_parts: str) -> str: return _write_story_part(part_name, outline, previous_parts)

def _edit_story(full_story: str, edit_instructions: str) -> str:
    logger.info(f"Tool: Editing story with instructions: {edit_instructions}")
    return f"*** Edited Story ***\n{full_story}\n(Editor notes: {edit_instructions})"
@function_tool
def edit_story(full_story: str, edit_instructions: str) -> str: return _edit_story(full_story, edit_instructions)


class GeeseBlueprint(BlueprintUXImproved): 
    _planner_agent_instance: Optional[Agent] = None
    _writer_agent_instance: Optional[Agent] = None
    _editor_agent_instance: Optional[Agent] = None
    coordinator_agent: Optional[Agent] = None

    def __init__(self, blueprint_id: str, config_path: str | None = None, **kwargs: Any):
        style = kwargs.pop('style', 'silly') 
        super().__init__(blueprint_id, config_path=config_path, style=style, **kwargs)
        
        self.mcp_servers_list: List = kwargs.get("mcp_servers", []) 
        self.mcp_servers_map: Dict[str, Any] = {
            mcp.name: mcp for mcp in self.mcp_servers_list if hasattr(mcp, 'name')
        }
        self.agent_mcp_assignments_config: Dict[str, List[Any]] = kwargs.get("agent_mcp_assignments_config", 
                                                                             kwargs.get("agent_mcp_assignments", {}))
        
        logger.debug(f"GeeseBlueprint '{self.blueprint_id}' __init__: agent_mcp_assignments_config = {self.agent_mcp_assignments_config}")
        logger.debug(f"GeeseBlueprint '{self.blueprint_id}' __init__: self.config is: {self.config}")
        
        self._setup_agents_and_llm(**kwargs)

    def _get_assigned_mcps_for_agent(self, agent_name: str) -> List[Any]:
        assigned_mcp_objects = []
        assigned_items = self.agent_mcp_assignments_config.get(agent_name, [])
        for item in assigned_items:
            if not getattr(item, 'disabled', False):
                assigned_mcp_objects.append(item)
        return assigned_mcp_objects

    def _setup_agents_and_llm(self, **kwargs):
        if not self.config: 
             logger.error(f"GeeseBlueprint '{self.blueprint_id}'._setup_agents_and_llm: self.config is empty.")
        
        llm_profile_name = self.llm_profile_name # Uses property from BlueprintBase
        
        logger.debug(f"GeeseBlueprint '{self.blueprint_id}'._setup_agents_and_llm: Using LLM profile '{llm_profile_name}'.")
        llm_model = self._get_model_instance(llm_profile_name) 

        self._planner_agent_instance = Agent(name="PlannerAgent", instructions="Planner instructions...", model=llm_model, mcp_servers=self._get_assigned_mcps_for_agent("PlannerAgent"))
        self._writer_agent_instance = Agent(name="WriterAgent", instructions="Writer instructions...", model=llm_model, mcp_servers=self._get_assigned_mcps_for_agent("WriterAgent"))
        self._editor_agent_instance = Agent(name="EditorAgent", instructions="Editor instructions...", model=llm_model, mcp_servers=self._get_assigned_mcps_for_agent("EditorAgent"))
        
        planner_tool = self._planner_agent_instance.as_tool("Planner", "Plan stories.")
        writer_tool = self._writer_agent_instance.as_tool("Writer", "Write sections.")
        editor_tool = self._editor_agent_instance.as_tool("Editor", "Edit stories.")
        
        self.coordinator_agent = Agent(
            name="GeeseCoordinator", instructions="Coordinate story writing.",
            tools=[planner_tool, writer_tool, editor_tool], model=llm_model,
            mcp_servers=self._get_assigned_mcps_for_agent("GeeseCoordinator") 
        )
        logger.info(f"GeeseBlueprint '{self.blueprint_id}': Coordinator and sub-agents created.")

    @property
    def planner_agent(self) -> Optional[Agent]: return self._planner_agent_instance
    @property
    def writer_agent(self) -> Optional[Agent]: return self._writer_agent_instance
    @property
    def editor_agent(self) -> Optional[Agent]: return self._editor_agent_instance

    def display_splash_screen(self, animated: bool = True):
        """Display the GeeseBlueprint splash screen."""
        welcome_text = Text("Welcome to GeeseBlueprint!", style="bold magenta")
        subtitle = Text("Creative Story Generation System", style="italic cyan")
        
        content = Text()
        content.append(welcome_text)
        content.append("\n")
        content.append(subtitle)
        content.append("\n\n")
        content.append("🪿 Coordinated storytelling with specialized agents\n", style="green")
        content.append("📖 Plot → Write → Edit workflow\n", style="blue")
        content.append("✨ Creative collaboration at its finest\n", style="yellow")
        
        panel = Panel(
            content,
            title="🪿 Geese Blueprint",
            border_style="bright_blue",
            padding=(1, 2)
        )
        
        # Ensure self.console is initialized (should be by BlueprintUXImproved)
        if not hasattr(self, 'console') or self.console is None:
            self.console = Console() # Fallback, though BlueprintUXImproved should handle this

        print(f"DEBUG GeeseBlueprint.display_splash_screen: self.console is {self.console}, type: {type(self.console)}") # DEBUG
        print(f"DEBUG GeeseBlueprint.display_splash_screen: panel is {panel}") # DEBUG

        if animated:
            with Live(panel, console=self.console, refresh_per_second=4):
                time.sleep(0.1) # Shortened for testing
        else:
            self.console.print(panel)


    async def run(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        query = messages[-1]["content"] if messages else ""
        if os.environ.get("SWARM_TEST_MODE"): 
            yield {"messages": [{"role": "assistant", "content": "This is a creative response about teamwork."}]}
            return
        agent_to_run = self.coordinator_agent 
        if not agent_to_run:
            logger.error(f"GeeseBlueprint '{self.blueprint_id}': Coordinator agent not initialized!")
            yield {"messages": [{"role": "assistant", "content": "Error: Coordinator not available."}]}
            return
        llm_response_content = ""
        try:
            if 'Runner' not in globals() or not callable(getattr(Runner, 'run', None)):
                raise RuntimeError("agents.Runner is not available or not callable.")

            async for response_chunk in Runner.run(agent_to_run, query): 
                llm_response_content = getattr(response_chunk, 'final_output', str(response_chunk)) 
            current_results = [llm_response_content.strip() or "(No response from LLM)"]
        except Exception as e:
            current_results = [f"[LLM ERROR] {e}"]
            logger.error(f"Error running Geese coordinator for '{self.blueprint_id}': {e}", exc_info=True)
        yield {"messages": [{"role": "assistant", "content": current_results[0] if current_results else ""}]}

    def create_starting_agent(self, mcp_servers: List[Any]) -> Agent: 
        if not self.coordinator_agent:
            logger.warning(f"GeeseBlueprint '{self.blueprint_id}'.create_starting_agent: Coordinator not set, attempting _setup_agents_and_llm.")
            self._setup_agents_and_llm(mcp_servers=mcp_servers) 
            if not self.coordinator_agent: 
                 raise RuntimeError(f"GeeseBlueprint '{self.blueprint_id}': Coordinator agent still not initialized.")
        return self.coordinator_agent

async def main_async(): 
    import argparse 
    parser = argparse.ArgumentParser(description="Geese: Swarm-powered collaborative story writing agent.")
    parser.add_argument("prompt", nargs="?", help="Prompt or story topic (quoted)")
    parser.add_argument("--config-path", help="Path to a custom swarm_config.json")
    args = parser.parse_args() 

    if not args.prompt: parser.print_help(); sys.exit(1)
    
    config_data = {}
    if args.config_path:
        try:
            with open(args.config_path, 'r') as f:
                config_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config from {args.config_path}: {e}")
            config_data = {"llm": {"default": {"provider": "mock", "model": "mock-cli-geese"}}} 
    else: 
        config_data = {"llm": {"default": {"provider": "mock", "model": "mock-cli-geese"}}}

    blueprint = GeeseBlueprint(blueprint_id="cli_geese", config_path=args.config_path, config=config_data, agent_mcp_assignments_config={}) 
    messages = [{"role": "user", "content": args.prompt}]
    
    async for chunk in blueprint.run(messages): 
        print(json.dumps(chunk, indent=2))

if __name__ == "__main__":
    asyncio.run(main_async())
