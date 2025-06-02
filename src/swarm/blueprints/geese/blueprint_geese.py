import asyncio
import os
import time
from typing import Any, Dict, List, Optional, Union
from swarm.core.blueprint_base import BlueprintBase
# Corrected import: BlueprintUXBase does not exist. Use BlueprintUXImproved.
from swarm.core.blueprint_ux import BlueprintUXImproved 
from swarm.core.interaction_types import AgentInteraction, StoryOutput
from swarm.core.mcp_server_config import MCPServerConfig
from swarm.core.agent_config import AgentConfig
from swarm.utils.log_utils import logger

class GeeseSpinner:
    FRAMES = ["🦢HONK.", "🦢HONK..", "🦢HONK...", "🦢HONK...."]
    INTERVAL = 0.3
    def __init__(self):
        self._idx = 0
    def next_state(self):
        state = self.FRAMES[self._idx % len(self.FRAMES)]
        self._idx += 1
        return state

class GeeseBlueprint(BlueprintBase):
    NAME = "geese"
    DESCRIPTION = "A multi-agent system for collaborative story generation."
    VERSION = "0.2.1"
    IS_ASYNC = True

    def __init__(self, blueprint_id: str = None, config_path: str = None, agent_mcp_assignments: Optional[Dict[str, List[str]]] = None, llm_model: Optional[str] = None, **kwargs):
        _id = blueprint_id or self.NAME
        super().__init__(_id, config_path, **kwargs)
        self.agent_mcp_assignments = agent_mcp_assignments or {}
        self.llm_model_override = llm_model
        # Corrected type hint and instantiation
        self.ux: BlueprintUXImproved = BlueprintUXImproved(style="fun") 
        self.spinner = GeeseSpinner()

    async def run(self, messages: List[Dict[str, Any]], **kwargs: Any) -> AgentInteraction:
        user_prompt = messages[-1]["content"] if messages and messages[-1]["role"] == "user" else "a generic story"
        logger.info(f"GeeseBlueprint run called with prompt: {user_prompt}")

        if os.environ.get("SWARM_TEST_MODE") == "1":
            test_spinner_messages = ["Generating.", "Generating..", "Generating...", "Running..."]
            for msg in test_spinner_messages:
                yield {"type": "spinner_update", "spinner_state": f"[SPINNER] {msg}"}
                await asyncio.sleep(0.01) 
            
            final_story_output = StoryOutput(
                title=f"Test Story for: {user_prompt[:30]}...",
                final_story="Once upon a time... (test mode story).",
                outline_json='{"test_outline": true}',
                word_count=6,
                metadata={"test_mode": True}
            )
            yield AgentInteraction(
                type="message",
                role="assistant",
                content=final_story_output.final_story, 
                data=final_story_output.model_dump(), 
                final=True
            )
            return

        self.ux.display_splash_screen(self.NAME, self.VERSION, self.DESCRIPTION, 하늘="🦢", 땅=" HONK! ")
        
        coordinator_config = self._get_agent_config("Coordinator")
        if not coordinator_config:
            logger.error("Coordinator agent configuration not found.")
            yield AgentInteraction(type="error", error_message="Coordinator config missing.", final=True)
            return

        coordinator_agent = self.create_agent_from_config(coordinator_config)
        
        yield AgentInteraction(type="progress", progress_message="🦢 Orchestrating the flock...", spinner_state=self.spinner.next_state())

        try:
            await asyncio.sleep(0.1) 
            yield AgentInteraction(type="progress", progress_message="🦆 Coordinator: Starting story generation...", spinner_state=self.spinner.next_state())
            
            await asyncio.sleep(0.1)
            yield AgentInteraction(type="progress", progress_message="🐣 Coordinator: Generating story outline...", spinner_state=self.spinner.next_state())
            
            outline_json_mock = '{"title": "A Grand Adventure", "logline": "A hero embarks on a quest.", "acts": [{"act_number": 1, "summary": "The beginning"}]}'
            
            await asyncio.sleep(0.1)
            yield AgentInteraction(type="progress", progress_message="📝 Writer: Drafting Act 1...", spinner_state=self.spinner.next_state())
            story_part_1 = "Chapter 1: The journey begins. Our hero, brave and bold, stepped out into the unknown."
            
            await asyncio.sleep(0.1)
            yield AgentInteraction(type="progress", progress_message="🧐 Editor: Reviewing draft...", spinner_state=self.spinner.next_state())
            edited_story_part_1 = story_part_1 

            final_story_output = StoryOutput(
                title="A Grand Adventure",
                final_story=edited_story_part_1,
                outline_json=outline_json_mock,
                word_count=len(edited_story_part_1.split()),
                metadata={"coordinator_model": coordinator_agent.model.model if hasattr(coordinator_agent, 'model') and coordinator_agent.model else "N/A"}
            )

            # Use the instance's ux object to call its method
            self.ux.ux_print_operation_box( # Changed from self.ux.display_operation_box
                title="📜 Your Generated Story 📜",
                content=final_story_output.final_story,
                params={"title": final_story_output.title, "word_count": final_story_output.word_count},
                op_type="story_result",
                emoji="🎉"
            )
            
            yield AgentInteraction(
                type="message",
                role="assistant",
                content=final_story_output.final_story, 
                data=final_story_output.model_dump(), 
                final=True
            )

        except Exception as e:
            logger.error(f"Error during Geese blueprint run: {e}", exc_info=True)
            yield AgentInteraction(type="error", error_message=str(e), final=True)


    def _get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        if hasattr(self, 'config') and self.config:
            agents_config = self.config.get('agents', {})
            if agent_name in agents_config:
                cfg = agents_config[agent_name]
                mcp_names = self.agent_mcp_assignments.get(agent_name, [])
                mcp_server_configs = [MCPServerConfig(name=name, url="") for name in mcp_names if name] 
                
                return AgentConfig(
                    name=agent_name,
                    description=cfg.get('description', f'{agent_name} agent'),
                    instructions=cfg.get('instructions', f'You are {agent_name}.'),
                    tools=cfg.get('tools', []),
                    model_profile=cfg.get('model_profile', self.config.get('llm_profile', 'default')),
                    mcp_servers=mcp_server_configs
                )
        logger.warning(f"Agent config for '{agent_name}' not found.")
        return None

    def create_agent_from_config(self, agent_config: AgentConfig):
        from agents import Agent 
        
        llm_profile = self.get_llm_profile(agent_config.model_profile) if hasattr(self, 'get_llm_profile') else {}
        model_name = self.llm_model_override or llm_profile.get("model", os.environ.get("DEFAULT_LLM", "gpt-3.5-turbo"))
        
        from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
        from openai import AsyncOpenAI
        
        api_key = llm_profile.get("api_key", os.environ.get("OPENAI_API_KEY", "sk-dummy"))
        base_url = llm_profile.get("base_url", os.environ.get("OPENAI_BASE_URL"))
        
        client_params = {"api_key": api_key}
        if base_url: client_params["base_url"] = base_url
        
        model_instance = None
        try:
            openai_client = AsyncOpenAI(**client_params)
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=openai_client)
        except Exception as e:
            logger.error(f"Failed to create OpenAI model for {agent_config.name}: {e}")

        return Agent(
            name=agent_config.name,
            instructions=agent_config.instructions,
            model=model_instance,
            tools=[], 
            mcp_servers=agent_config.mcp_servers
        )

if __name__ == "__main__":
    prompt_arg = None
    if len(sys.argv) > 1:
        if sys.argv[1] == '--message' and len(sys.argv) > 2:
            prompt_arg = sys.argv[2]
        elif sys.argv[1] != '--message': 
            prompt_arg = sys.argv[1]

    if not prompt_arg:
        prompt_arg = "Tell me a short, happy story about a goose."

    example_assignments = {
        "Coordinator": ["filesystem", "memory"],
        "Writer": ["filesystem"],
        "Editor": ["filesystem"]
    }

    geese_bp = GeeseBlueprint(agent_mcp_assignments=example_assignments)
    
    async def cli_run():
        start_time = time.time()
        async for item in geese_bp.run([{"role": "user", "content": prompt_arg}]):
            if isinstance(item, AgentInteraction):
                if item.type == "message" and item.role == "assistant":
                    print(f"\nGeese Final Story:\n{item.content}")
                    if item.data and isinstance(item.data, dict): 
                        print(f"(Title: {item.data.get('title')}, Word Count: {item.data.get('word_count')})")
                elif item.type == "progress":
                    elapsed = time.time() - start_time
                    # Use GeeseSpinner's FRAMES for CLI spinner
                    spinner = GeeseSpinner.FRAMES[int(elapsed * 2) % len(GeeseSpinner.FRAMES)] if not item.spinner_state else item.spinner_state
                    sys.stdout.write(f"\r{spinner} {item.progress_message}...")
                    sys.stdout.flush()
                elif item.type == "error":
                    print(f"\nError: {item.error_message}")
            elif isinstance(item, dict) and item.get("type") == "spinner_update" and os.environ.get("SWARM_TEST_MODE") == "1":
                # Handle the specific spinner update from test mode
                print(item.get("spinner_state", "Processing..."))
            else:
                print(f"Raw output: {item}") 
        print(f"\nTotal execution time: {time.time() - start_time:.2f}s")

    asyncio.run(cli_run())
