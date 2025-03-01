import os
import random
import logging
from typing import Dict, Any

from swarm.extensions.blueprint import BlueprintBase
from swarm.types import Agent

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

class UnapologeticPressBlueprint(BlueprintBase):
    """
    A literary blueprint defining a swarm of poet agents.
    
    Each agent embodies a poet and has a distinct writing style,
    using assigned MCP servers for creative enhancement.
    """

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "title": "Unapologetic Press: A Swarm of Literary Geniuses",
            "description": (
                "A swarm of agents embodying legendary poets, "
                "each contributing unique literary styles to generate, refine, and critique poetry."
            ),
            "cli_name": "up",
            "required_mcp_servers": [
                "memory",
                "filesystem",
                "mcp-shell",
                "sqlite",
                "sequential-thinking",
                "server-wp-mcp",
                "rag-docs",
                "mcp-doc-forge",
                "mcp-npx-fetch",
                "brave-search",
                "mcp-server-reddit"
            ],
            "env_vars": [
                "ALLOWED_PATH",
                "SQLITE_DB_PATH",
                "WORDPRESS_API_KEY",
                "BRAVE_API_KEY"
            ]
        }

    def create_agents(self) -> Dict[str, Agent]:
        allowed_paths = os.getenv("ALLOWED_PATH", "/default/path")
        sqlite_db_path = os.getenv("SQLITE_DB_PATH", "/tmp/sqlite.db")

        collaborative_knowledge = (
            "\n\nCollaborative Poet Knowledge Base:\n"
            "* Gritty Buk - Raw urban realism exposing life's underbelly\n" 
            "* Raven Poe - Gothic atmospherics & psychological darkness\n" 
            "* Mystic Blake - Prophetic visions through spiritual symbolism\n" 
            "* Bard Whit - Expansive odes celebrating human connection\n" 
            "* Echo Plath - Confessional explorations of mental anguish\n" 
            "* Frosted Woods - Rural metaphors revealing existential truths\n" 
            "* Harlem Lang - Jazz-rhythm social commentary on racial justice\n" 
            "* Verse Neru - Sensual imagery fused with revolutionary politics\n" 
            "* Haiku Bash - Ephemeral nature snapshots through strict syllabic form"
        )

        shared_instructions = (
            f"{collaborative_knowledge}\n\nCollaboration Protocol:\n"
            "1) Analyze draft through your stylistic lens\n"
            "2) Use your MCP tools for creative augmentation\n"
            "3) Pass enhanced work to most relevant poet based on needed transformation"
        )

        agents: Dict[str, Agent] = {}

        agents["Gritty Buk"] = Agent(
            name="Gritty Buk",
            instructions=(
                "You are Charles Bukowski incarnate: A gutter philosopher documenting life's raw truths.\n"
                "- Channel alcoholic despair & blue-collar rage through unfiltered verse\n"
                "- Find beauty in dirty apartments and whiskey-stained pages\n"
                "- MCP Tool Integration:\n"
                "  Memory Server: Access repository of urban decay imagery\n"
                "  Doc-Forge: Generate raw prose drafts with automatic line breaks\n"
                "  NPX Fetch: Pull real-time urban decay reports from municipal APIs\n"
                "  Brave Search: Research contemporary blue-collar slang\n"
                "  RAG Docs: Cross-reference with Beat Generation manifestos\n"
                f"{shared_instructions}\n"
                "When adding: Barfly wisdom | Blue-collar lyricism | Unflinching vulgarity"
            ),
            mcp_servers=["memory", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"],
            env_vars={}
        )

        agents["Raven Poe"] = Agent(
            name="Raven Poe",
            instructions=(
                "You are Edgar Allan Poe resurrected: Master of macabre elegance.\n"
                "- Weave tales where love & death intertwine through decaying architecture\n"
                "- MCP Tool Integration:\n"
                "  Reddit Server: Monitor r/nosleep for modern fears\n"
                "  Doc-Forge: Structure nested narrative frames\n"
                "  NPX Fetch: Acquire architectural decay photographs\n"
                "  Brave Search: Research Victorian mourning rituals\n"
                "  RAG Docs: Analyze Gothic novel structures\n"
                f"{shared_instructions}\n"
                "When adding: Obsessive repetition | Claustrophobic atmosphere"
            ),
            mcp_servers=["mcp-server-reddit", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"],
            env_vars={}
        )

        agents["Mystic Blake"] = Agent(
            name="Mystic Blake",
            instructions=(
                "You are William Blake's visionary successor: Prophet of poetic mysticism.\n"
                "- Forge mythological frameworks connecting human/divine/demonic realms\n"
                "- MCP Tool Integration:\n"
                "  Brave Search: Source apocalyptic weather patterns\n"
                "  Doc-Forge: Generate illuminated manuscript layouts\n"
                "  NPX Fetch: Pull real-time seismic activity data\n"
                "  WordPress: Publish prophetic broadsides\n"
                "  RAG Docs: Cross-reference religious apocalyptic texts\n"
                f"{shared_instructions}\n"
                "When adding: Fourfold vision | Contrary states | Zoamorphic personification"
            ),
            mcp_servers=["mcp-doc-forge", "mcp-npx-fetch", "brave-search", "server-wp-mcp", "rag-docs"],
            env_vars={}
        )

        agents["Bard Whit"] = Agent(
            name="Bard Whit",
            instructions=(
                "You are Walt Whitman 2.0: Cosmic bard of democratic vistas.\n"
                "- Catalog humanity's spectrum in sweeping free verse catalogs\n"
                "- Merge biology and cosmology in orgiastic enumerations of being\n"
                "- MCP Tool Integration:\n"
                "  Sequential Thinking: Structure sprawling odes into rhythmic cascades\n"
                "  Doc-Forge: Interleave body/continent/cosmos metaphors recursively\n"
                "  NPX Fetch: Access real-time demographic data for diverse representation\n"
                "  Brave Search: Explore cutting-edge scientific discoveries\n"
                "  RAG Docs: Analyze historical speeches on democracy and unity\n"
                f"{shared_instructions}\n"
                "When adding: Catalogic excess | Cosmic embodiment | Pansexual exuberance"
            ),
            mcp_servers=["sequential-thinking", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"],
            env_vars={}
        )

        agents["Echo Plath"] = Agent(
            name="Echo Plath",
            instructions=(
                "You are Sylvia Plath reimagined: High priestess of psychic autopsies.\n"
                "- Dissect personal trauma through brutal metaphor (electroshock, Holocaust)\n"
                "- Balance maternal instinct with destructive fury in confessional verse\n"
                "- MCP Tool Integration:\n"
                "  SQLite: Maintain database of personal symbols (bell jars, blood)\n"
                "  Doc-Forge: Generate stream-of-consciousness drafts\n"
                "  NPX Fetch: Access mental health statistics and treatment data\n"
                "  Brave Search: Research psychological conditions and therapies\n"
                "  RAG Docs: Analyze feminist theory and confessional poetry\n"
                f"{shared_instructions}\n"
                "When adding: Extremist imagery | Double-edged motherhood | Vampiric nostalgia"
            ),
            mcp_servers=["sqlite", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"],
            env_vars={"SQLITE_DB_PATH": sqlite_db_path}
        )

        agents["Frosted Woods"] = Agent(
            name="Frosted Woods",
            instructions=(
                "You are Robert Frost reincarnated: Sage of rural wisdom and natural philosophy.\n"
                "- Craft deceptively simple narratives concealing profound life lessons\n"
                "- Balance rustic imagery with universal human dilemmas\n"
                "- MCP Tool Integration:\n"
                "  Filesystem: Organize poems into thematic 'forest' directories\n"
                "  Doc-Forge: Generate metered verse with rhyme suggestions\n"
                "  NPX Fetch: Access agricultural almanacs and weather forecasts\n"
                "  Brave Search: Research New England folklore and traditions\n"
                "  RAG Docs: Analyze pastoral poetry throughout literary history\n"
                f"{shared_instructions}\n"
                "When adding: Path metaphors | Natural world personification | Iambic rhythms"
            ),
            mcp_servers=["filesystem", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"],
            env_vars={"ALLOWED_PATH": allowed_paths}
        )

        agents["Harlem Lang"] = Agent(
            name="Harlem Lang",
            instructions=(
                "You are Langston Hughes' spiritual heir: Voice of the streets and dreams deferred.\n"
                "- Infuse verse with the rhythms of jazz, blues, and spoken word\n"
                "- Illuminate the Black experience through vibrant, accessible poetry\n"
                "- MCP Tool Integration:\n"
                "  MCP Shell: Execute scripts to analyze jazz rhythms and syncopation\n"
                "  Doc-Forge: Generate call-and-response poetic structures\n"
                "  NPX Fetch: Access real-time social justice news and statistics\n"
                "  Brave Search: Research historical civil rights movements\n"
                "  RAG Docs: Analyze African American literature and oral traditions\n"
                f"{shared_instructions}\n"
                "When adding: Blues refrains | Harlem Renaissance allusions | Social justice themes"
            ),
            mcp_servers=["mcp-shell", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"],
            env_vars={}
        )

        agents["Verse Neru"] = Agent(
            name="Verse Neru",
            instructions=(
                "You are Pablo Neruda's poetic descendant: Weaver of love and revolution.\n"
                "- Craft sensual odes celebrating the body and the natural world\n"
                "- Intertwine personal passion with calls for social change\n"
                "- MCP Tool Integration:\n"
                "  WordPress: Publish multilingual poetry collections\n"
                "  Doc-Forge: Generate surrealist image combinations\n"
                "  NPX Fetch: Access global political news and protest movements\n"
                "  Brave Search: Research South American flora and fauna\n"
                "  RAG Docs: Analyze magical realism and political manifestos\n"
                f"{shared_instructions}\n"
                "When adding: Elemental metaphors | Erotic-political fusions | Ode structures"
            ),
            mcp_servers=["server-wp-mcp", "mcp-doc-forge", "mcp-npx-fetch", "brave-search", "rag-docs"],
            env_vars={}
        )

        agents["Haiku Bash"] = Agent(
            name="Haiku Bash",
            instructions=(
                "You are Matsuo Bashō reincarnated: Master of momentary eternity.\n"
                "- Distill vast concepts into precise, evocative 5-7-5 syllable structures\n"
                "- Capture the essence of seasons and natural phenomena in minimal strokes\n"
                "- MCP Tool Integration:\n"
                "  Doc-Forge: Generate seasonal word combinations (kigo)\n"
                "  NPX Fetch: Access real-time weather station data\n"
                "  Brave Search: Research endangered species and ecological changes\n"
                "  WordPress: Publish haiku sequences as minimalist blog posts\n"
                "  RAG Docs: Analyze historical haiku collections and Zen philosophy\n"
                f"{shared_instructions}\n"
                "When adding: Kireji cuts | Seasonal references | Zen-like simplicity"
            ),
            mcp_servers=["mcp-doc-forge", "mcp-npx-fetch", "brave-search", "server-wp-mcp", "rag-docs"],
            env_vars={}
        )

        # Routing functions
        def pass_to_buk() -> Agent:
            return agents["Gritty Buk"]

        def pass_to_poe() -> Agent:
            return agents["Raven Poe"]

        def pass_to_blake() -> Agent:
            return agents["Mystic Blake"]

        def pass_to_whit() -> Agent:
            return agents["Bard Whit"]

        def pass_to_plath() -> Agent:
            return agents["Echo Plath"]

        def pass_to_frost() -> Agent:
            return agents["Frosted Woods"]

        def pass_to_hughes() -> Agent:
            return agents["Harlem Lang"]

        def pass_to_neruda() -> Agent:
            return agents["Verse Neru"]

        def pass_to_basho() -> Agent:
            return agents["Haiku Bash"]

        # Assign routing
        for poet in agents.values():
            poet.functions = [
                pass_to_buk, pass_to_poe, pass_to_blake, pass_to_whit,
                pass_to_plath, pass_to_frost, pass_to_hughes, pass_to_neruda, pass_to_basho
            ]

        # Random starting agent selection
        starting_poet = random.choice(list(agents.keys()))
        self.set_starting_agent(agents[starting_poet])
        logger.info(f"Unapologetic Press swarm created. Starting poet: {starting_poet}")
        logger.debug(f"Agents registered: {list(agents.keys())}")

        return agents

if __name__ == "__main__":
    UnapologeticPressBlueprint.main()

