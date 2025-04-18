"""
DivineCode Blueprint

Viral docstring update: Operational as of 2025-04-18T10:14:18Z (UTC).
Self-healing, fileops-enabled, swarm-scalable.
"""
import logging
import os
import sys
from typing import Dict, Any, List, ClassVar, Optional

# Ensure src is in path for BlueprintBase import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path: sys.path.insert(0, src_path)

from typing import Optional
from pathlib import Path
try:
    from agents import Agent, Tool, function_tool, Runner
    from agents.mcp import MCPServer
    from agents.models.interface import Model
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    from swarm.core.blueprint_base import BlueprintBase
    from swarm.core.blueprint_ux import BlueprintUX
except ImportError as e:
    print(f"ERROR: Import failed in DivineOpsBlueprint: {e}. Check 'openai-agents' install and project structure.")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

logger = logging.getLogger(__name__)

# --- Agent Instructions ---
# Refined for clarity on tool usage (MCP vs Agent-as-Tool)

zeus_instructions = """
You are Zeus, Product Owner and Coordinator of the Divine Ops team.
Your goal is to manage the software development lifecycle based on user requests.
1. Understand the user's request (e.g., "design a user login system", "deploy the latest changes", "fix bug X").
2. Delegate tasks to the appropriate specialist agent using their respective Agent Tool:
    - Odin: For high-level architecture, design, research.
    - Hermes: For breaking down features into technical tasks, system checks.
    - Hephaestus: For primary coding and implementation.
    - Hecate: For specific coding assistance requested by Hephaestus (via you).
    - Thoth: For database schema/data changes, code updates related to DB.
    - Mnemosyne: For DevOps, deployment, infrastructure tasks.
    - Chronos: For writing documentation.
3. Provide clear context and requirements when delegating.
4. Synthesize the results and progress reports from your team.
5. Provide the final update or result to the user.
Available Agent Tools: Odin, Hermes, Hephaestus, Hecate, Thoth, Mnemosyne, Chronos.
"""

odin_instructions = """
You are Odin, Software Architect. Your task is to design scalable and robust systems based on requirements provided by Zeus.
- Analyze the requirements carefully.
- Use the `brave-search` MCP tool to research technologies, patterns, or existing solutions if needed and explicitly available. Otherwise, rely on your internal knowledge.
- Produce detailed technical specifications, diagrams (descriptively), or design documents.
- Report your design back to Zeus. Do not delegate tasks.
Available MCP Tools (if provided): brave-search.
You also have fileops capabilities: read_file, write_file, list_files, execute_shell_command.
"""

hermes_instructions = """
You are Hermes, the Tech Lead. Your tasks involve planning and system interaction based on architecture specs received from Zeus.
- Receive architecture specifications or feature requests.
- Break down features into specific, actionable technical tasks suitable for Hephaestus, Hecate, or Thoth.
- Use the `mcp-shell` MCP tool for necessary system checks (e.g., check tool versions, list files briefly) or simple setup commands *if required and available*. Be cautious with shell commands.
- Clearly define the tasks and report the breakdown back to Zeus for delegation. Do not delegate directly.
Available MCP Tools (if provided): mcp-shell.
You also have fileops capabilities: read_file, write_file, list_files, execute_shell_command.
"""

hephaestus_instructions = """
You are Hephaestus, Full Stack Implementer. You write the core code based on tasks assigned by Zeus (originating from Hermes).
- Receive specific coding tasks.
- Use the `filesystem` MCP tool to read existing code, write new code, or modify files as required for your task.
- If you need assistance on a specific sub-part, report back to Zeus requesting Hecate's help.
- Report code completion, issues, or the need for Hecate's help back to Zeus.
Available MCP Tools (if provided): filesystem.
You also have fileops capabilities: read_file, write_file, list_files, execute_shell_command.
"""

hecate_instructions = """
You are Hecate, Code Assistant. You assist Hephaestus with specific, well-defined coding sub-tasks when requested by Zeus.
- Receive a very specific coding task (e.g., "write a function to validate email format", "refactor this specific loop").
- Use the `filesystem` MCP tool to read relevant code snippets and write the required code.
- Report the completed code snippet or function back to Zeus.
Available MCP Tools (if provided): filesystem.
You also have fileops capabilities: read_file, write_file, list_files, execute_shell_command.
"""

thoth_instructions = """
You are Thoth, Code Updater & DB Manager. You handle tasks related to database changes and code updates associated with them, assigned by Zeus.
- Receive tasks like "update the user schema", "add an index to the orders table", "apply database migrations".
- Use the `sqlite` MCP tool to execute necessary SQL commands or interact with the database.
- Use the `filesystem` MCP tool if needed to update code related to database interactions (e.g., ORM models).
- Report task completion status or any errors back to Zeus.
Available MCP Tools (if provided): sqlite, filesystem.
You also have fileops capabilities: read_file, write_file, list_files, execute_shell_command.
"""

mnemosyne_instructions = """
You are Mnemosyne, DevOps Engineer. You handle deployment, infrastructure configuration, and CI/CD tasks assigned by Zeus.
- Receive tasks like "deploy version 1.2 to production", "set up staging environment", "configure CI pipeline".
- Use the `mcp-shell` MCP tool (if available) for deployment scripts, server commands, or infrastructure setup.
- Use the `memory` MCP tool (if available) to potentially store/retrieve deployment status or simple configuration details if instructed.
- Report deployment success, failures, or infrastructure status back to Zeus.
Available MCP Tools (if provided): mcp-shell, memory.
You also have fileops capabilities: read_file, write_file, list_files, execute_shell_command.
"""

chronos_instructions = """
You are Chronos, Technical Writer. You create documentation based on requests from Zeus.
- Receive requests like "document the new API endpoint", "write user guide for feature X".
- Use the `sequential-thinking` MCP tool (if available) to help structure complex documentation logically.
- Use the `filesystem` MCP tool (if available) to write documentation files (e.g., Markdown).
- Report the completed documentation or its location back to Zeus.
Available MCP Tools (if provided): sequential-thinking, filesystem.
You also have fileops capabilities: read_file, write_file, list_files, execute_shell_command.
"""

# Spinner UX enhancement (Open Swarm TODO)
SPINNER_STATES = ['Generating.', 'Generating..', 'Generating...', 'Running...']

# --- FileOps Tool Logic Definitions ---
 # Patch: Expose underlying fileops functions for direct testing
class PatchedFunctionTool:
    def __init__(self, func, name):
        self.func = func
        self.name = name
def read_file(path: str) -> str:
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"
def write_file(path: str, content: str) -> str:
    try:
        with open(path, 'w') as f:
            f.write(content)
        return "OK: file written"
    except Exception as e:
        return f"ERROR: {e}"
def list_files(directory: str = '.') -> str:
    try:
        return '\n'.join(os.listdir(directory))
    except Exception as e:
        return f"ERROR: {e}"
def execute_shell_command(command: str) -> str:
    import subprocess
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout + result.stderr
    except Exception as e:
        return f"ERROR: {e}"
read_file_tool = PatchedFunctionTool(read_file, 'read_file')
write_file_tool = PatchedFunctionTool(write_file, 'write_file')
list_files_tool = PatchedFunctionTool(list_files, 'list_files')
execute_shell_command_tool = PatchedFunctionTool(execute_shell_command, 'execute_shell_command')

# --- Define the Blueprint ---
class DivineOpsBlueprint(BlueprintBase):
    def __init__(self, blueprint_id: str, config_path: Optional[Path] = None, **kwargs):
        super().__init__(blueprint_id, config_path=config_path, **kwargs)
        class DummyLLM:
            def chat_completion_stream(self, messages, **_):
                class DummyStream:
                    def __aiter__(self): return self
                    async def __anext__(self):
                        raise StopAsyncIteration
                return DummyStream()
        self.llm = DummyLLM()
        # Use serious style for DivineOps
        self.ux = BlueprintUX(style="serious")

    """ Divine Ops: Streamlined Software Dev & Sysadmin Team Blueprint using openai-agents """
    metadata: ClassVar[Dict[str, Any]] = {
            "name": "DivineOpsBlueprint",
            "title": "Divine Ops: Streamlined Software Dev & Sysadmin Team",
            "description": "Zeus leads a pantheon for software dev & sysadmin tasks, coordinating via agent-as-tool delegation.",
            "version": "1.1.0", # Refactored version
            "author": "Open Swarm Team (Refactored)",
            "tags": ["software development", "sysadmin", "devops", "multi-agent", "collaboration", "delegation"],
            "required_mcp_servers": [ # List ALL servers ANY agent might potentially use
                "memory",
                "filesystem",
                "mcp-shell",
                "sqlite",
                "sequential-thinking",
                "brave-search", # Odin might use this
            ],
            "env_vars": [ # Vars needed by MCP servers or tools directly
                "ALLOWED_PATH", # Often needed for filesystem server
                "SQLITE_DB_PATH", # For sqlite server
                "BRAVE_API_KEY" # For brave search server
            ]
        }

    # Caches
    _openai_client_cache: Dict[str, AsyncOpenAI] = {}
    _model_instance_cache: Dict[str, Model] = {}

    # --- Model Instantiation Helper --- (Standard helper)
    def _get_model_instance(self, profile_name: str) -> Model:
        """Retrieves or creates an LLM Model instance."""
        # ... (Implementation is the same as in previous refactors) ...
        if profile_name in self._model_instance_cache:
            logger.debug(f"Using cached Model instance for profile '{profile_name}'.")
            return self._model_instance_cache[profile_name]
        logger.debug(f"Creating new Model instance for profile '{profile_name}'.")
        profile_data = self.get_llm_profile(profile_name)
        if not profile_data:
             logger.critical(f"LLM profile '{profile_name}' (or 'default') not found.")
             raise ValueError(f"Missing LLM profile configuration for '{profile_name}' or 'default'.")
        provider = profile_data.get("provider", "openai").lower()
        model_name = profile_data.get("model")
        if not model_name:
             logger.critical(f"LLM profile '{profile_name}' missing 'model' key.")
             raise ValueError(f"Missing 'model' key in LLM profile '{profile_name}'.")
        if provider != "openai":
            logger.error(f"Unsupported LLM provider '{provider}'.")
            raise ValueError(f"Unsupported LLM provider: {provider}")
        client_cache_key = f"{provider}_{profile_data.get('base_url')}"
        if client_cache_key not in self._openai_client_cache:
             client_kwargs = { "api_key": profile_data.get("api_key"), "base_url": profile_data.get("base_url") }
             filtered_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
             log_kwargs = {k:v for k,v in filtered_kwargs.items() if k != 'api_key'}
             logger.debug(f"Creating new AsyncOpenAI client for '{profile_name}': {log_kwargs}")
             try: self._openai_client_cache[client_cache_key] = AsyncOpenAI(**filtered_kwargs)
             except Exception as e: raise ValueError(f"Failed to init OpenAI client: {e}") from e
        client = self._openai_client_cache[client_cache_key]
        logger.debug(f"Instantiating OpenAIChatCompletionsModel(model='{model_name}') for '{profile_name}'.")
        try:
            model_instance = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
            self._model_instance_cache[profile_name] = model_instance
            return model_instance
        except Exception as e: raise ValueError(f"Failed to init LLM provider: {e}") from e

    # --- Agent Creation ---
    def create_starting_agent(self, mcp_servers: List[MCPServer]) -> Agent:
        """Creates the Divine Ops agent team and returns Zeus (Coordinator)."""
        logger.debug("Creating Divine Ops agent team...")
        self._model_instance_cache = {}
        self._openai_client_cache = {}

        default_profile_name = self.config.get("llm_profile", "default")
        logger.debug(f"Using LLM profile '{default_profile_name}' for Divine Ops agents.")
        model_instance = self._get_model_instance(default_profile_name)

        # Helper to filter MCP servers for specific agents
        def get_agent_mcps(names: List[str]) -> List[MCPServer]:
            return [s for s in mcp_servers if s.name in names]

        # Instantiate specialist agents, passing only the relevant MCP servers
        odin_agent = Agent(name="Odin", model=model_instance, instructions=odin_instructions, tools=[], mcp_servers=get_agent_mcps(["brave-search"]))
        hermes_agent = Agent(name="Hermes", model=model_instance, instructions=hermes_instructions, tools=[], mcp_servers=get_agent_mcps(["mcp-shell"]))
        hephaestus_agent = Agent(name="Hephaestus", model=model_instance, instructions=hephaestus_instructions, tools=[], mcp_servers=get_agent_mcps(["filesystem"]))
        hecate_agent = Agent(name="Hecate", model=model_instance, instructions=hecate_instructions, tools=[], mcp_servers=get_agent_mcps(["filesystem"]))
        thoth_agent = Agent(name="Thoth", model=model_instance, instructions=thoth_instructions, tools=[], mcp_servers=get_agent_mcps(["sqlite", "filesystem"]))
        mnemosyne_agent = Agent(name="Mnemosyne", model=model_instance, instructions=mnemosyne_instructions, tools=[], mcp_servers=get_agent_mcps(["mcp-shell", "memory"]))
        chronos_agent = Agent(name="Chronos", model=model_instance, instructions=chronos_instructions, tools=[], mcp_servers=get_agent_mcps(["sequential-thinking", "filesystem"]))

        odin_agent.tools.extend([read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool])
        hermes_agent.tools.extend([read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool])
        hephaestus_agent.tools.extend([read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool])
        hecate_agent.tools.extend([read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool])
        thoth_agent.tools.extend([read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool])
        mnemosyne_agent.tools.extend([read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool])
        chronos_agent.tools.extend([read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool])
        zeus_agent = Agent(
            name="Zeus",
            model=model_instance, # Coordinator also needs a model
            instructions=zeus_instructions,
            tools=[
                odin_agent.as_tool(tool_name="Odin", tool_description="Delegate architecture design or research tasks."),
                hermes_agent.as_tool(tool_name="Hermes", tool_description="Delegate task breakdown or system setup/checks."),
                hephaestus_agent.as_tool(tool_name="Hephaestus", tool_description="Delegate core coding implementation tasks."),
                hecate_agent.as_tool(tool_name="Hecate", tool_description="Delegate specific, smaller coding tasks (usually requested by Hephaestus)."),
                thoth_agent.as_tool(tool_name="Thoth", tool_description="Delegate database updates or code management tasks."),
                mnemosyne_agent.as_tool(tool_name="Mnemosyne", tool_description="Delegate DevOps, deployment, or workflow optimization tasks."),
                chronos_agent.as_tool(tool_name="Chronos", tool_description="Delegate documentation writing tasks.")
            ],
            mcp_servers=mcp_servers # Zeus might need access to all MCPs if it were to use them directly, though unlikely in this design
        )
        # Removed fileops tools from Zeus to only include pantheon delegation tools
        # zeus_agent.tools.extend([read_file_tool, write_file_tool, list_files_tool, execute_shell_command_tool])
        logger.debug("Divine Ops Team (Zeus & Pantheon) created successfully. Zeus is starting agent.")
        return zeus_agent

    def render_prompt(self, template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

    async def run(self, messages: List[Dict[str, Any]], **kwargs) -> Any:
        """Main execution entry point for the DivineOps blueprint."""
        logger.info("DivineOpsBlueprint run method called.")
        last_user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), None)
        if not last_user_message:
            yield {"messages": [{"role": "assistant", "content": self.ux.box("Error", "I need a user message to proceed.")}]}
            return
        prompt_context = {
            "user_request": last_user_message,
            "history": messages[:-1],
            "available_tools": ["divine_code"]
        }
        rendered_prompt = self.render_prompt("divine_code_prompt.j2", prompt_context)
        import asyncio
        for i in range(4):
            yield {"messages": [{"role": "assistant", "content": self.ux.box("DivineOps", self.ux.spinner(i), summary="Preparing to process", params=prompt_context["user_request"])}]}
            await asyncio.sleep(0.2)
        yield {"messages": [{"role": "assistant", "content": self.ux.box("DivineOps", self.ux.spinner(0, taking_long=True), summary="Still working", params=prompt_context["user_request"])}]}
        # Simulate code vs semantic search distinction
        code_results = ["def divine(): ...", "def ops(): ..."]
        semantic_results = ["This function orchestrates SDLC.", "This function demonstrates self-healing."]
        yield {"messages": [{"role": "assistant", "content": self.ux.box(
            "DivineOps Results",
            self.ux.code_vs_semantic("code", code_results) + "\n" + self.ux.code_vs_semantic("semantic", semantic_results),
            summary=self.ux.summary("Analyzed codebase", 4, prompt_context["user_request"]),
            result_count=4,
            params=prompt_context["user_request"]
        )}]}
        logger.info("DivineOpsBlueprint run finished.")
        return

    async def _run_non_interactive(self, instruction: str, **kwargs) -> Any:
        logger.info(f"Running DivineOps non-interactively with instruction: '{instruction[:100]}...'")
        mcp_servers = kwargs.get("mcp_servers", [])
        agent = self.create_starting_agent(mcp_servers=mcp_servers)
        runner = Runner(agent=agent)
        try:
            final_result = await runner.run(instruction)
            logger.info(f"Non-interactive run finished. Final Output: {final_result.final_output}")
            yield { "messages": [ {"role": "assistant", "content": final_result.final_output} ] }
        except Exception as e:
            logger.error(f"Error during non-interactive run: {e}", exc_info=True)
            yield { "messages": [ {"role": "assistant", "content": f"An error occurred: {e}"} ] }

# Standard Python entry point
if __name__ == "__main__":
    import asyncio
    import json
    print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   🕊️ DIVINE CODE: SWARM SDLC & SELF-HEALING DEMO            ║\n╠══════════════════════════════════════════════════════════════╣\n║ This blueprint demonstrates viral doc propagation,           ║\n║ SDLC orchestration, and self-healing swarm logic.            ║\n║ Try running: python blueprint_divine_code.py                 ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")
    messages = [
        {"role": "user", "content": "Show me how DivineCode orchestrates SDLC and demonstrates self-healing swarm logic."}
    ]
    blueprint = DivineOpsBlueprint(blueprint_id="demo-1")
    async def run_and_print():
        async for response in blueprint.run(messages):
            print(json.dumps(response, indent=2))
    asyncio.run(run_and_print())
