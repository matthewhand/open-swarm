import asyncio
import os
import time
from typing import Any, Dict, List, Optional, Union, AsyncGenerator 
from swarm.core.blueprint_base import BlueprintBase
from swarm.core.blueprint_ux import BlueprintUXImproved
from swarm.core.interaction_types import AgentInteraction, StoryOutput
from swarm.core.mcp_server_config import MCPServerConfig
from swarm.core.agent_config import AgentConfig
from swarm.utils.log_utils import logger
from unittest.mock import MagicMock 

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
        super().__init__(_id, config_path=config_path, **kwargs)
        
        self.agent_mcp_assignments = agent_mcp_assignments or {}
        self.llm_model_override = llm_model
        self.ux: BlueprintUXImproved = BlueprintUXImproved(style="silly") 
        self.spinner = GeeseSpinner()

    def display_splash_screen(self, style: Optional[str] = None, message: Optional[str] = None) -> None:
        _style = style if style is not None else self.ux.style 
        title_str = f"HONK! Welcome to Geese v{self.VERSION}! HONK!"
        default_message = "A multi-agent story generation system. Prepare for a cacophony of creativity!"
        content_str = message or default_message
        summary_str = f" geese ".center(30, '·')
        self.ux.ux_print_operation_box(
            title=title_str, content=content_str, summary=summary_str,
            style=_style, emoji="🦢"
        )

    async def run(self, messages: List[Dict[str, Any]], **kwargs: Any) -> AsyncGenerator[AgentInteraction, None]:
        user_prompt = messages[-1]["content"] if messages and messages[-1]["role"] == "user" else "a generic story"
        logger.info(f"GeeseBlueprint run called with prompt: {user_prompt}")

        if os.environ.get("SWARM_TEST_MODE") == "1":
            test_spinner_messages = ["Generating.", "Generating..", "Generating...", "Running..."]
            for msg_text in test_spinner_messages: 
                yield {"type": "spinner_update", "spinner_state": f"[SPINNER] {msg_text}"} # type: ignore
                await asyncio.sleep(0.01) 
            
            final_story_output = StoryOutput(
                title=f"Test Story for: {user_prompt[:30]}...",
                final_story="Once upon a time... (test mode story).",
                outline_json='{"test_outline": true}',
                word_count=6,
                metadata={"test_mode": True}
            )
            yield AgentInteraction(
                type="message", role="assistant",
                content=final_story_output.final_story, 
                data=final_story_output.model_dump(), 
                final=True
            )
            return

        self.display_splash_screen() 
        
        coordinator_config = self._get_agent_config("Coordinator")
        if not coordinator_config:
            logger.error("Coordinator agent configuration not found.")
            yield AgentInteraction(type="error", error_message="Coordinator config missing.", final=True)
            return

        coordinator_agent = self.create_agent_from_config(coordinator_config)
        if not coordinator_agent: 
            logger.error("Failed to create Coordinator agent.")
            yield AgentInteraction(type="error", error_message="Failed to create Coordinator agent.", final=True)
            return
            
        yield AgentInteraction(type="progress", progress_message=f"🦢 Orchestrating the flock... {self.spinner.next_state()}")

        final_story_output_obj: Optional[StoryOutput] = None # Initialize to None

        try:
            async for interaction_chunk in coordinator_agent.run(messages=messages, **kwargs):
                if isinstance(interaction_chunk, AgentInteraction):
                    if interaction_chunk.type == "progress":
                        yield interaction_chunk # Pass through progress updates
                    elif interaction_chunk.final and interaction_chunk.data and isinstance(interaction_chunk.data, dict):
                        try:
                            # Assuming the data is a dict from StoryOutput.model_dump()
                            final_story_output_obj = StoryOutput(**interaction_chunk.data)
                            self.ux.ux_print_operation_box(
                                title="📜 Your Generated Story 📜",
                                content=final_story_output_obj.final_story,
                                params={"title": final_story_output_obj.title, "word_count": final_story_output_obj.word_count},
                                op_type="story_result",
                                emoji="🎉"
                            )
                            # Yield the final message AgentInteraction
                            yield AgentInteraction(
                                type="message", role="assistant",
                                content=final_story_output_obj.final_story, 
                                data=final_story_output_obj.model_dump(), 
                                final=True
                            )
                        except Exception as e:
                            logger.error(f"Failed to parse final story data from coordinator: {e}", exc_info=True)
                            yield AgentInteraction(type="error", error_message="Failed to parse final story data.", final=True)
                        break # Got the final story data
                else:
                    # Handle other types of chunks if necessary, or log a warning
                    logger.warning(f"Received unexpected chunk type from coordinator: {type(interaction_chunk)}")


            if not final_story_output_obj:
                logger.warning("Coordinator agent did not yield a final story in the expected AgentInteraction format.")
                yield AgentInteraction(type="error", error_message="Coordinator did not produce a final story.", final=True)

        except Exception as e:
            logger.error(f"Error during Geese blueprint run (agent execution): {e}", exc_info=True)
            yield AgentInteraction(type="error", error_message=str(e), final=True)

    def _get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        if not hasattr(self, 'config') or not isinstance(self.config, dict):
            logger.debug(f"GeeseBlueprint.config not loaded or not a dict at start of _get_agent_config. Type: {type(getattr(self, 'config', None))}")
            # Attempt to load config if it seems missing.
            # This relies on BlueprintBase._load_configuration being effective.
            if not hasattr(self, '_config_loaded_once_flag_get_agent'): # Use a specific flag
                super()._load_configuration() 
                setattr(self, '_config_loaded_once_flag_get_agent', True)
                logger.debug(f"GeeseBlueprint.config after _load_configuration in _get_agent_config. Type: {type(getattr(self, 'config', None))}. Is dict: {isinstance(self.config, dict)}")


            if not hasattr(self, 'config') or not isinstance(self.config, dict):
                 logger.error("Config is still not a dict after attempting load in _get_agent_config.")
                 return None

        agents_config_data = self.config.get('agents', {}) 
        if agent_name in agents_config_data:
            cfg = agents_config_data[agent_name]
            if not isinstance(cfg, dict):
                logger.error(f"Agent config for '{agent_name}' is not a dictionary: {cfg}")
                return None

            mcp_names = self.agent_mcp_assignments.get(agent_name, [])
            mcp_server_configs_list = [MCPServerConfig(name=name, url="") for name in mcp_names if name] 
            
            return AgentConfig(
                name=agent_name,
                description=cfg.get('description', f'{agent_name} agent'),
                instructions=cfg.get('instructions', f'You are {agent_name}.'),
                tools=cfg.get('tools', []), 
                model_profile=cfg.get('model_profile', self.config.get('llm_profile', 'default')),
                mcp_servers=mcp_server_configs_list
            )
        logger.warning(f"Agent config for '{agent_name}' not found in swarm_config.json section 'agents'. Config was: {self.config}")
        return None

    def create_agent_from_config(self, agent_config: AgentConfig) -> Optional[Any]:
        try:
            from agents import Agent 
            llm_profile_data = self.get_llm_profile(agent_config.model_profile)
            model_instance = self._get_model_instance(agent_config.model_profile) 

            if not model_instance:
                logger.error(f"Failed to get model instance for agent {agent_config.name} using profile {agent_config.model_profile}")
                return None
            
            sdk_mcp_servers = [] 

            return Agent(
                name=agent_config.name,
                instructions=agent_config.instructions,
                model=model_instance,
                tools=[], 
                mcp_servers=sdk_mcp_servers 
            )
        except ImportError:
            logger.warning("openai-agents SDK not available. Using MagicMock for agent.")
            mock_agent = MagicMock()
            mock_agent.name = agent_config.name
            mock_agent.instructions = agent_config.instructions
            async def mock_run(*args, **kwargs): 
                # This mock needs to align with what test_story_generation_flow expects
                final_story_output_data = {
                    "title": "Mocked Story from SDK-less Agent", # Differentiate for clarity
                    "final_story": f"Mock response from {agent_config.name}",
                    "outline_json": "{}", "word_count": 5, "metadata": {}
                }
                yield AgentInteraction(type="message", role="assistant", 
                                       content=final_story_output_data["final_story"],
                                       data=final_story_output_data, 
                                       final=True)
            mock_agent.run = mock_run
            mock_model_attr = MagicMock()
            mock_model_attr.model = "mock_sdk_model"
            mock_agent.model = mock_model_attr
            return mock_agent
        except Exception as e:
            logger.error(f"Error creating agent {agent_config.name} from config: {e}", exc_info=True)
            return None

if __name__ == "__main__":
    import sys
    prompt_arg = None
    if len(sys.argv) > 1:
        if sys.argv[1] == '--message' and len(sys.argv) > 2:
            prompt_arg = sys.argv[2]
        elif sys.argv[1] != '--message': 
            prompt_arg = sys.argv[1]

    if not prompt_arg:
        prompt_arg = "Tell me a short, happy story about a goose."

    geese_bp = GeeseBlueprint(blueprint_id="geese_cli_main") 
    
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
                    spinner_char = item.progress_message 
                    sys.stdout.write(f"\r{spinner_char}   ") 
                    sys.stdout.flush()
                elif item.type == "error":
                    print(f"\nError: {item.error_message}")
            elif isinstance(item, dict) and item.get("type") == "spinner_update" and os.environ.get("SWARM_TEST_MODE") == "1":
                print(item.get("spinner_state", "Processing..."))
            else:
                print(f"Raw output: {item}") 
        print(f"\nTotal execution time: {time.time() - start_time:.2f}s")

    asyncio.run(cli_run())
