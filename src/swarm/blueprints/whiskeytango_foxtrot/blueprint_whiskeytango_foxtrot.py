"""
WhiskeyTangoFoxtrot: Tracking Free Online Services
"""
from agents.mcp import MCPServer
import os
import sys
from dotenv import load_dotenv; load_dotenv(override=True)

import contextlib
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, ClassVar

try:
    from agents import Agent, Runner
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    from swarm.core.blueprint_base import BlueprintBase
    from swarm.core.blueprint_ux import BlueprintUXImproved
except ImportError as e:
    print(f"ERROR: Import failed in WhiskeyTangoFoxtrotBlueprint: {e}. Check dependencies.")
    sys.exit(1)

logger = logging.getLogger(__name__)

SQLITE_DB_PATH_STR = os.getenv("SQLITE_DB_PATH", "./wtf_services.db")
SQLITE_DB_PATH = Path(SQLITE_DB_PATH_STR).resolve()

valory_instructions = """Valory instructions..."""
tyril_instructions = """Tyril instructions..."""
tray_instructions = """Tray instructions..."""
larry_instructions = """Larry instructions..."""
kriegs_instructions = """Kriegs instructions..."""
vanna_instructions = """Vanna instructions..."""
marcher_instructions = """Marcher instructions..."""

class WhiskeyTangoFoxtrotBlueprint(BlueprintBase):
    metadata: ClassVar[dict[str, Any]] = {
        "name": "WhiskeyTangoFoxtrotBlueprint",
        "title": "WhiskeyTangoFoxtrot Service Tracker",
        "description": "Tracks free online services with SQLite and web search using a multi-tiered agent hierarchy.",
        "version": "1.2.2", # Incremented version
        "author": "Open Swarm Team (Refactored)",
        "tags": ["web scraping", "database", "sqlite", "multi-agent", "hierarchy", "mcp"],
        "required_mcp_servers": ["sqlite", "brave-search", "mcp-npx-fetch", "mcp-doc-forge", "filesystem"],
        "env_vars": ["BRAVE_API_KEY", "SQLITE_DB_PATH", "ALLOWED_PATH"]
    }

    _openai_client_cache: dict[str, AsyncOpenAI] = {}
    _model_instance_cache: dict[str, Model] = {}

    def __init__(self, blueprint_id: str = "whiskeytangofoxtrot", config_path: str | None = None, **kwargs: Any):
        # Initialize full BlueprintBase (loads configuration, including patched _load_configuration in tests)
        super().__init__(blueprint_id, config_path=config_path, **kwargs)
        # Provide a simple UX helper for optional pretty boxes/spinners if desired
        try:
            self.ux = BlueprintUXImproved(style="serious")
        except Exception:
            self.ux = None

        self._llm_profile_name: str | None = None
        self._llm_profile_data: dict[str, Any] | None = None
        self._markdown_output: bool | None = None
        # Snapshot the module-level DB path so tests can patch it reliably per-instance
        with contextlib.suppress(Exception):
            self.SQLITE_DB_PATH = SQLITE_DB_PATH


    def initialize_db(self) -> None:
        # Resolve DB path with strong test override support
        # The test patches the module-level SQLITE_DB_PATH.
        # The instance snapshots this path during __init__ into self.SQLITE_DB_PATH.
        db_path = getattr(self, 'SQLITE_DB_PATH', SQLITE_DB_PATH)
        if not isinstance(db_path, Path):
            db_path = Path(str(db_path)).resolve()
        logger.info(f"Ensuring database schema exists at: {db_path}")
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='services';")
            if not cursor.fetchone():
                logger.info("Initializing 'services' table in SQLite database.")
                cursor.execute("""
                    CREATE TABLE services (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        type TEXT NOT NULL,
                        url TEXT,
                        api_key TEXT,
                        usage_limits TEXT,
                        documentation_link TEXT,
                        last_checked TEXT
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_services_name ON services (name);")
                conn.commit()
                logger.info("'services' table created.")
            else:
                 logger.debug("'services' table already exists.")
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"SQLite error during DB initialization: {e}", exc_info=True)
        except Exception as e:
             logger.error(f"Unexpected error during DB initialization: {e}", exc_info=True)

    def _get_model_instance(self, profile_name: str) -> Model:
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]

        if not hasattr(self, '_config') or self._config is None:
            logger.critical("WTF._get_model_instance: self._config is missing or None.")
            raise RuntimeError("Configuration not loaded (self._config missing or None), cannot get model instance.")

        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        # Use self._config directly, as self.config property might be missing if BlueprintBase.__init__ didn't run
        profile_data = self._config.get('llm', {}).get(profile_name) if self._config else None
        if not profile_data:
            raise ValueError(f"Missing LLM profile '{profile_name}'. Current self._config: {self._config}")

        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name: raise ValueError(f"Missing 'model' in profile '{profile_name}'.")
        # Allow lightweight providers used in tests (e.g., 'mock') by returning the model name
        if provider in {"mock", "test", "none"}:
            logger.debug(f"Using lightweight provider '{provider}' with model '{model_name}' for profile '{profile_name}'.")
            # Cache as a simple string so downstream Agent can accept it
            self._model_instance_cache[profile_name] = model_name  # type: ignore[assignment]
            return model_name  # type: ignore[return-value]
        if provider != "openai":
            raise ValueError(f"Unsupported provider: {provider}")

        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_kwargs = {k:v for k,v in filtered_kwargs.items() if k != 'api_key'}
             logger.debug(f"Creating new AsyncOpenAI client for '{profile_name}': {log_kwargs}")
             try: self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_kwargs)
             except Exception as e: raise ValueError(f"Failed to init client: {e}") from e
        client = self._openai_client_cache[client_cache_key]

        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e: raise ValueError(f"Failed to init LLM: {e}") from e

    def render_prompt(self, template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

    async def run(self, messages: list[dict], **kwargs):
        logger.info("WhiskeyTangoFoxtrotBlueprint run method called.")
        instruction = messages[-1].get("content", "") if messages else ""
        # ... (rest of run method is likely fine for now) ...
        spinner_idx = 0
        start_time = time.time()
        spinner_yield_interval = 1.0
        last_spinner_time = start_time
        yielded_spinner = False
        result_chunks = []

        mcp_servers_for_run = kwargs.get("mcp_servers_override", [])

        try:
            starting_agent = self.create_starting_agent(mcp_servers=mcp_servers_for_run)
            runner_gen = Runner.run(starting_agent, instruction)

            while True:
                now = time.time()
                try:
                    chunk = next(runner_gen)
                    result_chunks.append(chunk)
                    if chunk and isinstance(chunk, dict) and "messages" in chunk:
                        content = chunk["messages"][0]["content"] if chunk["messages"] else ""
                        summary = self.ux_summary("Operation", len(result_chunks), {"instruction": instruction[:40]}) if hasattr(self, 'ux_summary') else ""
                        box = self.ux_ansi_emoji_box(
                            title="WhiskeyTangoFoxtrot Result", content=content, summary=summary,
                            params={"instruction": instruction[:40]}, result_count=len(result_chunks),
                            op_type="run", status="success"
                        ) if hasattr(self, 'ux_ansi_emoji_box') else content
                        yield {"messages": [{"role": "assistant", "content": box}]}
                    else:
                        yield chunk
                    yielded_spinner = False
                except StopIteration:
                    break
                except Exception as e_gen:
                    logger.error(f"Error in Runner.run generator: {e_gen}", exc_info=True)
                    yield {"messages": [{"role": "assistant", "content": f"Error processing: {e_gen}"}]}
                    return

                if not result_chunks or (now - last_spinner_time >= spinner_yield_interval):
                    taking_long = (now - start_time > 10)
                    spinner_msg = self.ux_spinner(spinner_idx, taking_long=taking_long) if hasattr(self, 'ux_spinner') else f"Processing... {spinner_idx}"
                    yield {"messages": [{"role": "assistant", "content": spinner_msg}]}
                    spinner_idx += 1
                    last_spinner_time = now
                    yielded_spinner = True

            if not result_chunks and not yielded_spinner:
                spinner_msg_final = self.ux_spinner(0) if hasattr(self, 'ux_spinner') else "Processing..."
                yield {"messages": [{"role": "assistant", "content": spinner_msg_final}]}

        except Exception as e:
            logger.error(f"Error during WhiskeyTangoFoxtrot run: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"An error occurred: {e}"}]}
        return


    def create_starting_agent(self, mcp_servers: list[MCPServer]) -> Agent:
        if not hasattr(self, '_config') or self._config is None:
            logger.error("WTF.create_starting_agent: self._config is missing or None. This should have been set by __init__.")
            raise RuntimeError("Configuration (self._config) is missing or None in create_starting_agent.")

        self.initialize_db()

        logger.debug("Creating WhiskeyTangoFoxtrot agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        # Use self._config directly as self.config property might be missing
        settings_config = self._config.get("settings", {})
        llm_profile_from_bp_config = self._config.get("llm_profile") # Blueprint-specific config for 'llm_profile'

        default_profile_name = llm_profile_from_bp_config or settings_config.get("default_llm_profile", "default")

        logger.debug(f"Using LLM profile '{default_profile_name}' for WTF agents. (From BP config: {llm_profile_from_bp_config}, from settings: {settings_config.get('default_llm_profile')})")
        model_instance = self._get_model_instance(default_profile_name)
        def _coerce_agent_model(candidate):
            try:
                from agents.models.interface import Model as _Model
            except Exception:
                _Model = None
            if isinstance(candidate, str):
                return candidate
            if _Model is not None and isinstance(candidate, _Model):
                return candidate
            cand_model_name = getattr(candidate, "model", None)
            if isinstance(cand_model_name, str):
                return cand_model_name
            try:
                prof = self._config.get('llm', {}).get(default_profile_name, {}) if hasattr(self, '_config') else {}
                if isinstance(prof, dict) and isinstance(prof.get("model"), str):
                    return prof["model"]
            except Exception:
                pass
            return "default"
        model_param = _coerce_agent_model(model_instance)

        def get_agent_mcps(names: list[str]) -> list[MCPServer]:
            {s.name for s in mcp_servers if hasattr(s, 'name')}
            required_found_servers = [s for s in mcp_servers if hasattr(s, 'name') and s.name in names]

            if len(required_found_servers) != len(names):
                found_names = {s.name for s in required_found_servers}
                missing = set(names) - found_names
                if missing:
                    logger.warning(f"Agent needing {names} is missing started MCP(s): {', '.join(missing)}")
            return required_found_servers

        agents: dict[str, Agent] = {}
        agents["Larry"] = Agent(name="Larry", model=model_param, instructions=larry_instructions, tools=[], mcp_servers=get_agent_mcps(["filesystem"]))
        agents["Kriegs"] = Agent(name="Kriegs", model=model_param, instructions=kriegs_instructions, tools=[], mcp_servers=get_agent_mcps(["sqlite"]))
        agents["Vanna"] = Agent(name="Vanna", model=model_param, instructions=vanna_instructions, tools=[], mcp_servers=get_agent_mcps(["brave-search", "mcp-npx-fetch"]))
        agents["Marcher"] = Agent(name="Marcher", model=model_param, instructions=marcher_instructions, tools=[], mcp_servers=get_agent_mcps(["mcp-doc-forge"]))

        agents["Tyril"] = Agent(
            name="Tyril", model=model_param, instructions=tyril_instructions,
            tools=[agents["Larry"].as_tool("Larry", "Delegate filesystem tasks."), agents["Kriegs"].as_tool("Kriegs", "Delegate SQLite DB ops.")],
            mcp_servers=get_agent_mcps(["sqlite"])
        )
        agents["Tray"] = Agent(
            name="Tray", model=model_param, instructions=tray_instructions,
            tools=[agents["Vanna"].as_tool("Vanna", "Delegate web search/fetch."), agents["Marcher"].as_tool("Marcher", "Delegate web data processing.")],
            mcp_servers=[]
        )
        agents["Valory"] = Agent(
            name="Valory", model=model_param, instructions=valory_instructions,
            tools=[agents["Tyril"].as_tool("Tyril", "Delegate DB/file tasks."), agents["Tray"].as_tool("Tray", "Delegate web tasks.")],
            mcp_servers=[]
        )
        logger.debug("WhiskeyTangoFoxtrot agents created. Starting with Valory.")
        return agents["Valory"]

if __name__ == "__main__":
    import asyncio
    import json
    from unittest.mock import MagicMock

    dummy_config_content = {
        "llm": { "default": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": os.getenv("OPENAI_API_KEY")}, },
        "mcpServers": { "sqlite": {"type": "sqlite", "config": {"db_path": "./wtf_services_main.db"}}, },
        "settings": {"default_llm_profile": "default"}
    }
    temp_config_path = Path("./temp_wtf_config.json")
    with open(temp_config_path, "w") as f: json.dump(dummy_config_content, f)

    blueprint = WhiskeyTangoFoxtrotBlueprint(config_path=str(temp_config_path))

    mock_mcp_sqlite = MagicMock(spec=MCPServer); mock_mcp_sqlite.name = "sqlite"
    mock_mcp_filesystem = MagicMock(spec=MCPServer); mock_mcp_filesystem.name = "filesystem"
    mock_mcp_brave = MagicMock(spec=MCPServer); mock_mcp_brave.name = "brave-search"
    mock_mcp_npx = MagicMock(spec=MCPServer); mock_mcp_npx.name = "mcp-npx-fetch"
    mock_mcp_docforge = MagicMock(spec=MCPServer); mock_mcp_docforge.name = "mcp-doc-forge"
    example_mcp_servers = [mock_mcp_sqlite, mock_mcp_filesystem, mock_mcp_brave, mock_mcp_npx, mock_mcp_docforge]

    messages = [{"role": "user", "content": "Find any new free tier AI services related to image generation."}]

    async def run_and_print():
        async for response in blueprint.run(messages, mcp_servers_override=example_mcp_servers):
            print(json.dumps(response, indent=2))

    asyncio.run(run_and_print())
    if temp_config_path.exists(): temp_config_path.unlink()
