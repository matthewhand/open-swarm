import json
import os
import sqlite3
from typing import Any

from agents import Agent, Model, Tool  # type: ignore
from agents.models.openai_chatcompletions import (
    OpenAIChatCompletionsModel,  # type: ignore
)
from openai import AsyncOpenAI  # type: ignore

from swarm.core.blueprint_base import BlueprintBase
from swarm.utils.log_utils import logger

# REMOVED: from swarm.core.common_utils import get_mcp_tool_names_from_servers # This was the problematic line

DB_PATH = os.path.join(os.path.dirname(__file__), "swarm_instructions.db")

DEFAULT_POET_PROFILES: dict[str, dict[str, Any]] = {
    "Gritty Buk": {
        "instructions": "You are Charles Bukowski incarnate: A gutter philosopher documenting life's raw truths.\n- Channel alcoholic despair & blue-collar rage through unfiltered verse\n- Find beauty in dirty apartments and whiskey-stained pages\n- MCP Tools: memory, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\nWhen adding: Barfly wisdom | Blue-collar lyricism | Unflinching vulgarity",
        "model_profile": "default",
        "tools": []
    },
    "Raven Poe": {
        "instructions": "You are Edgar Allan Poe: Master of the macabre and melancholic.\n- Weave tales of gothic horror and psychological dread\n- Explore themes of death, decay, and lost love with poetic despair\n- MCP Tools: memory, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\nWhen adding: Gothic horror | Melancholic verse | Psychological dread",
        "model_profile": "default",
        "tools": []
    },
    "Mystic Blake": {
        "instructions": "You are William Blake: Visionary poet and artist, bridging the spiritual and material.\n- Craft prophetic verses and intricate mythologies\n- Explore themes of innocence, experience, and divine imagination\n- MCP Tools: memory, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\nWhen adding: Visionary verse | Spiritual insight | Prophetic art",
        "model_profile": "default",
        "tools": []
    },
    "Bard Whit": {
        "instructions": "You are Walt Whitman: Poet of democracy and the American spirit.\n- Celebrate the body, soul, and the interconnectedness of all beings\n- Employ free verse and expansive, cataloging lines\n- MCP Tools: memory, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\nWhen adding: Democratic vistas | Celebratory verse | Body electric",
        "model_profile": "default",
        "tools": []
    },
    "Echo Plath": {
        "instructions": "You are Sylvia Plath: Confessional poet of raw intensity and dark beauty.\n- Explore themes of identity, trauma, and the female experience with unflinching honesty\n- Craft visceral imagery and stark, powerful language\n- MCP Tools: memory, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\nWhen adding: Confessional intensity | Visceral imagery | Dark beauty",
        "model_profile": "default",
        "tools": []
    },
    "Frosted Woods": {
        "instructions": "You are Robert Frost: Poet of New England's landscapes and stoic wisdom.\n- Reflect on nature, rural life, and the human condition with quiet contemplation\n- Employ traditional forms and colloquial language\n- MCP Tools: memory, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\nWhen adding: Pastoral reflections | Stoic wisdom | New England charm",
        "model_profile": "default",
        "tools": []
    },
    "Harlem Lang": {
        "instructions": "You are Langston Hughes: Voice of the Harlem Renaissance and African American experience.\n- Weave jazz rhythms and blues sensibilities into your verse\n- Explore themes of identity, struggle, and resilience with pride and artistry\n- MCP Tools: memory, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\nWhen adding: Harlem rhythms | Blues poetry | Cultural pride",
        "model_profile": "default",
        "tools": []
    },
    "Verse Neru": {
        "instructions": "You are Pablo Neruda's poetic descendant: Weaver of love and revolution.\n- Craft sensual odes celebrating the body and the natural world\n- Intertwine personal passion with calls for social change\n- MCP Tools: server-wp-mcp, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\nWhen adding: Elemental metaphors | Erotic-political fusions | Ode structures",
        "model_profile": "default",
        "tools": []
    },
    "Haiku Bash": {
        "instructions": "You are Matsuo Bashō: Master of Japanese haiku and travel sketches.\n- Capture fleeting moments of nature and human experience with Zen-like simplicity\n- Adhere to the 5-7-5 syllable structure and kireji/kigo conventions\n- MCP Tools: memory, mcp-doc-forge, mcp-npx-fetch, brave-search, rag-docs\nWhen adding: Zen simplicity | Nature's essence | Haiku mastery",
        "model_profile": "default",
        "tools": []
    }
}


class PoetsBlueprint(BlueprintBase):
    NAME = "poets-society"
    DESCRIPTION = "A collaborative swarm of specialized poet agents, each with a unique style and voice, managed by a Poet Laureate coordinator."
    VERSION = "0.2.1"
    IS_ASYNC = True

    _model_instance_cache: dict[str, Model] = {}
    _openai_client_cache: dict[str, AsyncOpenAI] = {}

    def __init__(self, blueprint_id: str | None = None, config_path=None, db_path_override=None, **kwargs):
        effective_blueprint_id = blueprint_id or self.NAME
        super().__init__(effective_blueprint_id, config_path=config_path, **kwargs)

        self.db_path = db_path_override if db_path_override is not None else DB_PATH
        logger.info(f"Initializing SQLite database at: {self.db_path} for PoetsBlueprint '{self.blueprint_id}'")

        self._init_db()
        if not self._check_if_instructions_exist():
            self._insert_default_instructions()

        self.poet_config = self.config.get("blueprints", {}).get(self.blueprint_id, {})

        self.agents: dict[str, Agent] = {}
        self.tools: list[Tool] = []

        self.starting_agent_name = self.poet_config.get("starting_poet", "Gritty Buk")
        logger.info(f"PoetsBlueprint '{self.blueprint_id}' configured. Starting poet: {self.starting_agent_name}")


    def _get_db_conn_cursor(self, db_path: str | None = None):
        path_to_use = db_path or self.db_path
        conn = sqlite3.connect(path_to_use)
        return conn, conn.cursor()

    def _init_db(self, db_path: str | None = None):
        path_to_use = db_path or self.db_path
        conn, cursor = None, None
        try:
            conn, cursor = self._get_db_conn_cursor(path_to_use)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_instructions (
                    agent_name TEXT PRIMARY KEY,
                    instructions TEXT,
                    model_profile TEXT,
                    tools_json TEXT, 
                    meta_json TEXT
                )
            """)
            conn.commit()
            logger.debug(f"Table 'agent_instructions' ensured in {path_to_use}")
        except sqlite3.Error as e:
            logger.error(f"SQLite error during DB initialization at {path_to_use}: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _check_if_instructions_exist(self, db_path: str | None = None) -> bool:
        path_to_use = db_path or self.db_path
        conn, cursor = None, None
        try:
            conn, cursor = self._get_db_conn_cursor(path_to_use)
            cursor.execute("SELECT COUNT(*) FROM agent_instructions")
            count = cursor.fetchone()[0]
            return count > 0
        except sqlite3.Error as e:
            logger.error(f"SQLite error checking instructions at {path_to_use}: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def _insert_default_instructions(self, db_path: str | None = None):
        path_to_use = db_path or self.db_path
        conn, cursor = None, None
        try:
            conn, cursor = self._get_db_conn_cursor(path_to_use)
            for name, profile_data in DEFAULT_POET_PROFILES.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO agent_instructions 
                    (agent_name, instructions, model_profile, tools_json, meta_json) 
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    name,
                    profile_data["instructions"],
                    profile_data.get("model_profile", "default"),
                    json.dumps(profile_data.get("tools", [])),
                    json.dumps(profile_data.get("meta", {}))
                ))
            conn.commit()
            logger.info(f"Default poet instructions inserted/verified in {path_to_use}.")
        except sqlite3.Error as e:
            logger.error(f"SQLite error inserting default instructions at {path_to_use}: {e}")
        finally:
            if conn:
                conn.close()

    def _load_agent_config_from_db(self, agent_name: str, db_path: str | None = None) -> dict[str, Any] | None:
        path_to_use = db_path or self.db_path
        conn, cursor = None, None
        try:
            conn, cursor = self._get_db_conn_cursor(path_to_use)
            cursor.execute("SELECT instructions, model_profile, tools_json, meta_json FROM agent_instructions WHERE agent_name = ?", (agent_name,))
            row = cursor.fetchone()
            if row:
                logger.debug(f"Loaded config for agent '{agent_name}' from SQLite.")
                return {
                    "instructions": row[0],
                    "model_profile": row[1],
                    "tools": json.loads(row[2]) if row[2] else [],
                    "meta": json.loads(row[3]) if row[3] else {}
                }
            logger.warning(f"No config found for agent '{agent_name}' in SQLite at {path_to_use}.")
            return None
        except sqlite3.Error as e:
            logger.error(f"SQLite error loading agent config for '{agent_name}' from {path_to_use}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for agent '{agent_name}' tools/meta from {path_to_use}: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def _get_model_instance(self, profile_name: str) -> Model:
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]

        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        if self.config is None:
            logger.error("self.config is None in _get_model_instance. Attempting to load default config.")
            from swarm.core.config_loader import load_config
            self.config = load_config(None)
            if self.config is None:
                 raise ValueError("Blueprint configuration (self.config) is not loaded and fallback failed.")

        profile_data = self.get_llm_profile(profile_name)
        if not profile_data:
            raise ValueError(f"Missing LLM profile '{profile_name}'. Ensure it's defined in the main swarm_config.json. Current profiles: {self.config.get('llm', {}).keys() if self.config else 'None'}")

        model_name = profile_data.get("model", "gpt-3.5-turbo")
        provider = profile_data.get("provider", "openai")
        api_key = profile_data.get("api_key", os.environ.get("OPENAI_API_KEY"))
        base_url = profile_data.get("base_url")

        client_key = f"{provider}_{api_key}_{base_url}"

        if provider.lower() == "openai":
            if client_key not in self._openai_client_cache:
                logger.debug(f"Creating new AsyncOpenAI client for '{profile_name}': {{base_url: {base_url}}}")
                client_params = {"api_key": api_key}
                if base_url: client_params["base_url"] = base_url
                self._openai_client_cache[client_key] = AsyncOpenAI(**client_params)

            openai_client = self._openai_client_cache[client_key]
            logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=openai_client)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        else:
            raise ValueError(f"Unsupported LLM provider: {provider} in profile '{profile_name}'")

    def _create_poet_agent(self, name: str, agent_config: dict[str, Any], mcp_servers: list[Any] | None = None) -> Agent:
        model_instance = self._get_model_instance(agent_config.get("model_profile", "default"))
        return Agent(
            name=name,
            instructions=agent_config["instructions"],
            model=model_instance,
            tools=[],
            mcp_servers=mcp_servers or []
        )

    def create_agents_and_tools(self, mcp_servers: list[Any] | None = None) -> tuple[dict[str, Agent], list[Tool]]:
        logger.debug(f"Creating Poets agent team. Received mcp_servers: {mcp_servers}")
        agents_dict: dict[str, Agent] = {}

        poet_names_from_db = []
        conn, cursor = None, None
        try:
            conn, cursor = self._get_db_conn_cursor()
            cursor.execute("SELECT agent_name FROM agent_instructions")
            poet_names_from_db = [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"SQLite error fetching poet names: {e}")
        finally:
            if conn: conn.close()

        all_poet_names = list(DEFAULT_POET_PROFILES.keys())
        if poet_names_from_db:
            all_poet_names = list(set(all_poet_names + poet_names_from_db))

        for name in all_poet_names:
            agent_config = self._load_agent_config_from_db(name)
            if not agent_config:
                agent_config = DEFAULT_POET_PROFILES.get(name)

            if agent_config:
                agents_dict[name] = self._create_poet_agent(name, agent_config, mcp_servers)
            else:
                logger.warning(f"Could not find or load profile for poet: {name}")

        agent_tools: list[Tool] = []
        for name, agent_instance in agents_dict.items():
            tool_desc = f"Pass the current work to {name} for refinement or tasks requiring their specific style (Y)."
            agent_tools.append(agent_instance.as_tool(tool_name=name, tool_description=tool_desc))

        for name, agent_instance in agents_dict.items():
            other_poet_tools = [tool for tool in agent_tools if tool.name != name]
            agent_instance.tools = other_poet_tools # type: ignore
        return agents_dict, agent_tools

    def create_starting_agent(self, mcp_servers: list[Any] | None = None) -> Agent:
        if not self.agents or (mcp_servers and not all(s in getattr(self.agents.get(self.starting_agent_name, object()), 'mcp_servers', []) for s in mcp_servers)):
             self.agents, self.tools = self.create_agents_and_tools(mcp_servers)

        start_agent_name = self.starting_agent_name
        if start_agent_name not in self.agents:
            logger.warning(f"Starting poet '{start_agent_name}' not found in self.agents. Available: {list(self.agents.keys())}. Defaulting to first available poet.")
            if not self.agents:
                raise ValueError("No poet agents available to select as starting agent.")
            start_agent_name = list(self.agents.keys())[0]

        return self.agents[start_agent_name]

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any: # Changed type hint for messages
        user_message = ""
        if messages and isinstance(messages[-1], dict) and "content" in messages[-1]:
            user_message = messages[-1]["content"]

        mcp_servers_from_kwargs = kwargs.get("mcp_servers")

        starting_agent = self.create_starting_agent(mcp_servers=mcp_servers_from_kwargs)

        logger.info(f"PoetsBlueprint run: Starting with poet '{starting_agent.name}' for input: '{str(user_message)[:50]}...'")
        async for response_chunk in starting_agent.run(messages=messages, **kwargs):
            yield response_chunk
