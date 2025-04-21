# Blueprints Overview

This directory contains example blueprints for the Open Swarm framework, showcasing agent coordination, external data handling, database operations, and more via parody-themed agent teams. Each blueprint achieves a practical outcome while demonstrating specific framework capabilities. Blueprints are generally ordered by complexity.

## Compliance Table: Blueprint Feature Demonstration

| Blueprint      | Agentic | ANSI/Emoji UX | Spinner | Fallback | Test Coverage | Key Demo Features |
|---------------|:-------:|:-------------:|:-------:|:--------:|:-------------:|------------------|
| FamilyTies    |   ✅    |      ✅      |   ✅    |    ✅    |      ✅      | Agentic search/analysis, summaries, counts, test mode |
| WhingeSurf    |   ✅    |      ✅      |   ✅    |    ✅    |      ✅      | Agentic web search/analysis, summaries, fallback UX |
| Codey         |   ✅    |      ✅      |   ✅    |    ✅    |      ✅      | Code/semantic search, summaries, spinner, fallback |
| Chatbot       |   ✅    |      ✅      |   ✅    |    ✅    |      ✅      | Conversational agent, fallback, spinner, test mode |
| Suggestion    |   ✅    |      ✅      |   ✅    |    ✅    |      ✅      | Suggestion/idea generation, summaries, fallback |
| Zeus          |   ✅    |      ✅      |   ✅    |    ✅    |      ✅      | Multi-agent delegation, DevOps, summaries |
| Omniplex      |   ✅    |      ✅      |   ✅    |    ✅    |      ✅      | Dynamic agent orchestration, npx/uvx/MCP |
| Jeeves        |   ✅    |      ✅      |   ✅    |    ✅    |      ✅      | Multi-agent home/web orchestration, fallback |

- **Agentic**: Demonstrates agent-based orchestration or delegation
- **ANSI/Emoji UX**: Uses unified result/progress boxes and emoji for output
- **Spinner**: Custom spinner messages ('Generating.', 'Generating..', ...)
- **Fallback**: Robust user-friendly fallback for LLM/agent errors
- **Test Coverage**: Blueprint includes or supports robust tests

---

## Refactored Blueprints (Using `BlueprintBase`)

These blueprints have been updated to use the `BlueprintBase` class, `openai-agents` library conventions (like `Agent`, `@function_tool`, agent-as-tool delegation), and standardized configuration loading.

| Blueprint Name                  | CLI (`uv run ...`) Example Instruction                | What it Demonstrates                                                           | Key Features                                                              | MCP Servers Used (Examples) |
|---------------------------------|-------------------------------------------------------|--------------------------------------------------------------------------------|---------------------------------------------------------------------------|-----------------------------|
| **EchoCraft**                   | `--instruction "Repeat this message"`                 | Simplest blueprint, direct input echo                                          | Basic `BlueprintBase` structure, Agent `process` override                 | None                        |
| **Suggestion**                  | `--instruction "Topic: AI Ethics"`                    | Generating structured JSON output                                              | Agent `output_type=TypedDict`, JSON mode                                  | None                        |
| **Chatbot**                     | `--instruction "Tell me a joke"`                      | Basic single-agent conversation                                                | Standard `Agent` interaction with LLM                                     | None                        |
| **BurntNoodles**                | `--instruction "Check git status"`                    | Coordinating Git & testing tasks via function tools & agent delegation       | `@function_tool` for CLI commands, Agent-as-tool delegation             | None                        |
| **RueCode**                     | `--instruction "Refactor this python code..."`        | Multi-agent code generation/refactoring workflow                             | Agent-as-tool delegation, specialized agent roles (Coordinator, Code, etc.), **Code/semantic search**; agent-as-tool delegation; supports both code and semantic search, with tailored output and progress boxes; demonstrates fileops/analysis UX. | memory                      |
| **NebulaShellzzar**             | `--instruction "List files in /tmp"`                  | Matrix-themed sysadmin/coding tasks with delegation                        | Agent-as-tool delegation, `@function_tool` for shell/code analysis    | memory                      |
| **DigitalButlers**              | `--instruction "Search for nearby restaurants"`       | Delegating tasks requiring specific MCPs (search, home automation)         | Agent-as-tool delegation, MCP usage by specialist agents                  | duckduckgo-search, home-assistant |
| **DilbotUniverse (SQLite)**     | `--instruction "Start the SDLC"`                      | Comedic SDLC simulation, instructions loaded from SQLite                     | Agent-as-tool delegation, SQLite integration for dynamic prompts          | sqlite                      |
| **FamilyTies**                  | `--instruction "Create WP post titled 'Hello'..."`    | Coordinating WordPress operations via MCP                                    | Agent-as-tool delegation, specialized agent using specific MCP (WP)     | server-wp-mcp               |
| **MissionImprobable (SQLite)**  | `--instruction "Use RollinFumble to run 'pwd'"`       | Spy-themed ops, instructions from SQLite, multi-level delegation             | Agent-as-tool delegation, SQLite integration, MCP usage (fs, shell, mem)  | memory, filesystem, mcp-shell |
| **WhiskeyTangoFoxtrot**       | `--instruction "Find free vector DBs"`                  | Hierarchical agents tracking services using DB & web search                | Multi-level agent delegation, SQLite, various search/scrape/doc MCPs    | sqlite, brave-search, mcp-npx-fetch, mcp-doc-forge, filesystem |
| **DivineOps**                   | `--instruction "Design user auth API"`                | Large-scale SW dev coordination (Design, Implement, DB, DevOps, Docs)      | Complex delegation, wide range of MCP usage (search, shell, db, fs...)  | memory, filesystem, mcp-shell, sqlite, sequential-thinking, brave-search |
| **Gaggle**                      | `--instruction "Write story: cat library"`            | Collaborative story writing (Planner, Writer, Editor)                        | Agent-as-tool delegation, function tools for writing steps, **parallel/consensus agent runs**; aggregates multiple LLM outputs for brainstorming, analysis, or creative divergence. | None                        |
| **MonkaiMagic**                 | `--instruction "List AWS S3 buckets"`                 | Cloud operations (AWS, Fly, Vercel) via direct CLI function tools          | `@function_tool` for external CLIs, agent-as-tool delegation            | mcp-shell (for Sandy)       |
| **UnapologeticPress (SQLite)** | `--instruction "Write poem: city rain"`               | Collaborative poetry writing by distinct "poet" agents, SQLite instructions | Agent-as-tool (all-to-all), SQLite, broad MCP usage                       | Various (see blueprint)     |
| **Omniplex**                    | `--instruction "Use filesystem to read README.md"`    | Dynamically routes tasks based on MCP server type (npx, uvx, other)      | Dynamic agent/tool creation based on available MCPs                     | Dynamic (all available)     |
| **Geese**                       | `--instruction "Tell me a story about teamwork"`      | Multi-step creative generation with specialized agents (Planner, Writer, Editor) | **Multi-agent teamwork**; agent-as-tool delegation; demonstrates collaborative agent workflows, creative output, and enhanced UX with spinners/emoji. | None |
| **Divine Code**                 | `--instruction "Find a bug in this code"`             | Inspirational code suggestions, bug finding, code review                     | Themed agent for creative/code tasks; demonstrates **agent specialization and themed UX**; output formatted for developer readability. | None                        |
| **Zeus**                        | `--instruction "Design a scalable API architecture"`  | Hierarchical agent orchestration for software dev/sysadmin tasks              | **Hierarchical delegation**; Zeus agent leads a "pantheon" of specialists (Odin, Hermes, etc.); demonstrates advanced agent team management and SDLC orchestration. | None |

## WIP / Needs Refactoring

These blueprints still use older patterns or have known issues (e.g., UVX/NeMo dependencies) and need refactoring to the `BlueprintBase` standard.

| Blueprint Name          | CLI      | Description                                                  | Status          |
|-------------------------|----------|--------------------------------------------------------------|-----------------|
| chucks_angels           | chuck    | Manages transcripts, compute, Flowise (UVX/NeMo WIP)         | Needs Refactor  |
| django_chat             | djchat   | Django-integrated chatbot example                            | Needs Review    |
| flock                   | flock    | (Details TBC)                                                | Needs Refactor  |
| messenger               | msg      | (Details TBC)                                                | Needs Refactor  |

## Configuration (`swarm_config.json`)

The framework uses a central `swarm_config.json` file (usually in the project root) to define:

*   **`llm`**: Profiles for different language models (provider, model name, API keys via `${ENV_VAR}`, base URL, etc.).
*   **`mcpServers`**: Definitions for starting external MCP servers. Each entry includes:
    *   `command`: The command to run (e.g., `npx`, `uvx`, `python`, `docker`). Can be a string or list.
    *   `args`: A list of arguments for the command.
    *   `env`: A dictionary of environment variables to set for the server process.
    *   `cwd`: (Optional) Working directory for the server process.
    *   `description`: (Optional) A human-readable description of the server's function.
    *   `startup_timeout`: (Optional) Seconds to wait for the server to start and connect (default: 30).
*   **`blueprints`**: Optional section for blueprint-specific overrides (e.g., default profile, max calls).
*   **`defaults`**: Global default settings (e.g., `default_markdown_cli`).

## Environment Variables

Many blueprints or their required MCP servers depend on environment variables (e.g., API keys). These should ideally be set in a `.env` file in the project root. `BlueprintBase` will automatically load this file. See individual blueprint metadata (`env_vars`) or `swarm_config.json` for potentially required variables. The `BlueprintBase` will warn if variables listed in a blueprint's `metadata["env_vars"]` are not set.

## Running Blueprints (Development)

Use `uv run python <path_to_blueprint.py> --instruction "Your instruction"`

Common flags:
*   `--debug`: Enable detailed DEBUG logging.
*   `--quiet`: Suppress most logs, print only final output.
*   `--config-path`: Specify a different config file location.
*   `--profile`: Use a specific LLM profile from the config.
*   `--markdown` / `--no-markdown`: Force markdown rendering on/off.

## Example Outputs & Framework Capabilities

### Geese Blueprint
**Purpose:** Orchestrates creative writing using Planner, Writer, and Editor agents, coordinated by a Geese team leader.
**Demonstrates:** Multi-agent teamwork, agent-as-tool delegation, creative LLM output, enhanced UX.
**Example Output:**
```
Geese Creative
Creative generation complete for: 'Tell me a story about teamwork'
│ 🦢 Geese Creative
║ Here’s a short story of teamwork starring Aria, Bram, Pip, and Luna as they face a fierce storm—and win together. Hope you enjoy!
```

### Gaggle Blueprint
**Purpose:** Runs a group of agents in parallel/sequence for brainstorming, consensus, or creative divergence.
**Demonstrates:** Parallel agent execution, aggregation of LLM outputs, consensus/brainstorming workflows.
**Example Output:**
```
Gaggle Creative
Gaggle agent run for: 'Write story: cat library'
│ 🪿 Gaggle Creative
║ [Agent 1] ...
║ [Agent 2] ...
║ [Agent 3] ...
```

### Divine Code Blueprint
**Purpose:** Invokes an “inspirational” agent for code suggestions, bug finding, or code review.
**Demonstrates:** Agent specialization, themed UX, LLM-powered code analysis.
**Example Output:**
```
Divine Code Inspiration
Divine code inspiration complete for 'Find a bug in this code'.
│ ✨ Divine Code
║ def buggy_func():
║     print('Hello, World!')  # No bug found.
```

### Unique Feature: Divine Code with Inotify (File Change Awareness)
**Purpose:** In addition to code inspiration and review, this blueprint actively monitors the filesystem (using inotify) for file creations, modifications, or deletions between user prompts.
**How it works:**
- When a file changes, the blueprint detects the event and updates the LLM context, making the agent aware of new, changed, or removed files.
- This enables the LLM to provide context-aware suggestions, bug finding, or code review that responds to the evolving project state.
**Demonstrates:** Real-time agentic awareness of the developer's environment, bridging code generation with live project changes.
**Example Output:**
```
Divine Code Inspiration
Detected file changes:
 - Modified: src/utils/helpers.py
 - Created: tests/test_helpers.py
 - Deleted: old_code/legacy.py
│ ✨ Divine Code
║ Noted recent changes. Reviewing updated helpers and new tests...
║ Suggestion: Add more edge case tests for helpers.py
```
This makes Divine Code uniquely adaptive, enabling workflows where the agent "watches" your project and tailors its advice or generation to what actually changes in real time.

### Zeus Blueprint
**Purpose:** Simulates a lead architect (Zeus) delegating to a pantheon of specialist agents for software/devops tasks.
**Demonstrates:** Hierarchical agent orchestration, SDLC workflows, agent team management.
**Example Output:**
```
Zeus Result
Found
Designing scalable API architecture...
Processed
```

### RueCode Blueprint
**Purpose:** Code search, semantic analysis, and templating using LLMs.
**Demonstrates:** Code/semantic search, fileops/analysis UX, tailored output boxes, progress updates.
**Example Output:**
```
RueCode Agent Run
RueCode agent run for: 'Refactor this python code...'
│ 📝 RueCode
║ Refactored code:
║ def new_func():
║     ...
```

Each blueprint above demonstrates a key Open Swarm capability: agentic LLM execution, multi-agent workflows, fileops/search UX, and portable, real-world outputs.

## Beyond Coding & Creative Writing: Blueprint Flexibility

Open Swarm blueprints are not limited to software development or creative writing. The framework is designed for **maximum flexibility**, enabling developers to compose any CLI user experience or agentic workflow for a wide variety of domains, including but not limited to:

- **Research & Analysis**: Build blueprints that coordinate agents for literature review, market analysis, or scientific hypothesis generation, combining LLMs with data scraping, semantic search, and structured reporting.
- **Ops & Automation**: Orchestrate sysadmin, cloud, or DevOps tasks by chaining shell, database, and infrastructure MCPs with LLM-powered planning, validation, and reporting agents.
- **Education & Tutoring**: Create interactive learning experiences, adaptive quizzes, or Socratic dialogue agents that guide users through concepts, code, or even language learning.
- **Productivity & Personal Assistance**: Develop blueprints for summarizing meetings, managing to-do lists, or automating calendaring and reminders, with LLMs handling intent recognition and workflow orchestration.
- **Knowledge Management**: Combine semantic search, summarization, and tagging agents to organize, retrieve, and synthesize information from large document sets, wikis, or codebases.
- **Conversational UX**: Design chatbots, virtual assistants, or role-play agents with custom personalities, memory, and tool-use capabilities.
- **Custom CLI Tools**: Use Open Swarm to rapidly prototype any command-line tool that needs intelligent, multi-step logic, rich output formatting (ANSI/emoji boxes), or dynamic agent composition.

### Example: Research Analyst Blueprint
**Purpose:** Coordinates agents for literature search, semantic analysis, and summary synthesis on a research topic.
**Demonstrates:** Multi-agent data gathering, semantic search, structured output, and progress reporting.
**Example Output:**
```
Research Analyst
Searched PubMed for: 'CRISPR gene editing ethics'
│ 🔎 Literature Search
║ 12 relevant papers found.
│ 🧠 Semantic Analysis
║ Key themes: bioethics, regulation, public perception
│ 📋 Summary
║ CRISPR technology raises complex ethical questions. Regulatory frameworks are evolving, with consensus on the need for oversight...
```

### Example: DevOps Orchestrator Blueprint
**Purpose:** Automates infrastructure checks, deployments, and incident triage using LLM agents and shell/database MCPs.
**Demonstrates:** Tool/agent chaining, CLI output formatting, and real-time progress spinners.
**Example Output:**
```
DevOps Orchestrator
Running infrastructure check for 'prod-cluster'
│ 🖥️ Shell MCP
║ All nodes healthy.
│ 🗄️ Database MCP
║ Backups verified.
│ 🤖 LLM Agent
║ No incidents detected. Ready for deployment.
```

### Example: Learning Coach Blueprint
**Purpose:** Guides a user through learning Python, adapting questions and explanations based on user responses.
**Demonstrates:** Conversational UX, adaptive agent behavior, and educational scaffolding.
**Example Output:**
```
Learning Coach
Welcome to Python 101!
│ 🧑‍🏫 Coach
║ What does the 'def' keyword do in Python?
│ 💡 Hint
║ It defines a function.
```

These examples illustrate the **open-ended, composable nature** of Open Swarm blueprints. Developers can mix and match agent roles, MCPs, UX patterns, and output formatting to create powerful, domain-specific tools that go far beyond traditional coding assistants.

## Blueprint Interoperability & Agent Sharing

Open Swarm blueprints are designed for composability—not only can agents within a blueprint delegate tasks to each other, but advanced users can coordinate workflows across multiple blueprints by sharing agent instances or invoking agents/tools from other blueprints. While the framework does not enforce direct blueprint-to-blueprint calls, the following interoperability patterns are supported:

- **Agent-as-Tool Delegation:** Agents from one blueprint can be registered as tools and used by agents in another blueprint, enabling cross-blueprint workflows.
- **Shared Agent Registries:** Blueprints can share or register agents in a global registry, allowing dynamic discovery and invocation by other blueprints.
- **Direct Instantiation:** You can instantiate and use agents or tools from any blueprint in custom scripts or orchestrators.

### Example: Sharing an Agent as a Tool
```python
# Minimal example: Using an agent from Blueprint A as a tool in Blueprint B
from swarm.blueprints.family_ties.blueprint_family_ties import FamilyTiesBlueprint
from swarm.blueprints.zeus.blueprint_zeus import ZeusBlueprint

# Instantiate blueprints (in practice, you may want to share config)
family_ties = FamilyTiesBlueprint("family_ties")
zeus = ZeusBlueprint("zeus")

# Register a FamilyTies agent as a tool for Zeus
zeus_agent = zeus.get_agent("Zeus")
family_agent = family_ties.get_agent("FamilySearch")
zeus_agent.tools.append(family_agent.as_tool("FamilySearchTool", "Search family data"))

# Now, Zeus can delegate tasks to FamilySearchTool as part of its workflow
```

> **Note:** This is a conceptual example. Actual implementation may require adapting agent/tool interfaces for compatibility. See each blueprint's Python file for agent construction and delegation patterns.

### When to Use Blueprint Interoperability
- **Complex Workflows:** When a task requires capabilities from multiple blueprints (e.g., DevOps + Family Data Analysis).
- **Extending Functionality:** When building meta-blueprints or orchestrators that combine specialized blueprints.

For more, see the agent/tool delegation logic in `blueprint_zeus.py`, `blueprint_family_ties.py`, and the Open Swarm documentation.
