# Zeus Blueprint

**Zeus** is a multi-agent DevOps and delegation blueprint for Open Swarm, demonstrating multi-agent coordination, delegation to specialist agent tools, robust fallback for LLM/agent errors, and unified ANSI/emoji UX with spinner feedback.

---

## What This Blueprint Demonstrates
- **Multi-agent delegation and coordination** (Zeus, Odin, Hermes, Hephaestus, etc.)
- **Specialist agent tools** for architecture, code, DevOps, documentation, etc.
- **LLM fallback and error handling** with user-friendly messages
- **Unified ANSI/emoji boxes** for operation results, including summaries, counts, and parameters
- **Custom spinner messages**: 'Generating.', 'Generating..', 'Generating...', 'Running...'
- **Progress updates** for long-running operations (file counts, summaries)
- **Test mode** for robust, deterministic testing

## Usage
Run with the CLI:
```sh
swarm-cli run zeus --instruction "Design and implement a login system."
```

## Test
```sh
uv run pytest -v tests/blueprints/test_zeus.py
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
- See `blueprint_zeus.py` for agent logic and UX hooks.
- Extend agent capabilities or UX by modifying the `_run_non_interactive` and agent tool delegation methods.

---
_Last updated: 2025-04-21_
