# Omniplex Blueprint

**Omniplex** is a dynamic MCP orchestrator blueprint for Open Swarm, demonstrating dynamic delegation to agents for npx, uvx, and other MCP tools, robust fallback for LLM/agent errors, and unified ANSI/emoji UX with spinner feedback.

---

## What This Blueprint Demonstrates
- **Dynamic multi-agent orchestration** for npx, uvx, and other MCP tools
- **Delegation to specialized agent tools**
- **LLM fallback and error handling** with user-friendly messages
- **Unified ANSI/emoji boxes** for operation results, including summaries, counts, and parameters
- **Custom spinner messages**: 'Generating.', 'Generating..', 'Generating...', 'Running...'
- **Progress updates** for long-running operations (file counts, summaries)
- **Test mode** for robust, deterministic testing

## Usage
Run with the CLI:
```sh
swarm-cli run omniplex --instruction "Run npx create-react-app my-app"
```

## Test
```sh
uv run pytest -v tests/blueprints/test_omniplex.py
```

## Compliance
- Agentic: 
- UX (ANSI/emoji): 
- Spinner: 
- Fallback: 
- Test Coverage: 

## Required Env Vars
- `SWARM_TEST_MODE` (optional): Enables test mode for deterministic output.

## Extending
- See `blueprint_omniplex.py` for agent logic and UX hooks.
- Extend agent capabilities or UX by modifying the `_run_non_interactive` method and agent tool delegation logic.

---
_Last updated: 2025-04-21_
