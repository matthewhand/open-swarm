# Suggestion Blueprint

**Suggestion** is a swarm-powered agentic blueprint for Open Swarm, demonstrating agent-driven creative suggestion generation, robust fallback for LLM/agent errors, and unified ANSI/emoji UX with spinner feedback.

---

## What This Blueprint Demonstrates
- **Agent-based suggestion/idea generation**
- **LLM fallback and error handling** with user-friendly messages
- **Unified ANSI/emoji boxes** for suggestion results, including summaries and counts
- **Custom spinner messages**: 'Generating.', 'Generating..', 'Generating...', 'Running...'
- **Progress updates** for long-running operations (result counts, summaries)
- **Test mode** for robust, deterministic testing

## Usage
Run with the CLI:
```sh
swarm-cli run suggestion --instruction "Suggest viral marketing ideas for a new product."
```

## Test
```sh
uv run pytest -v tests/blueprints/test_suggestion.py
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
- See `blueprint_suggestion.py` for agent logic and UX hooks.
- Extend agent capabilities or UX by modifying the `_run_non_interactive` method.

---
_Last updated: 2025-04-21_
