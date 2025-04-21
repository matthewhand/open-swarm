# Family Ties Blueprint

**Family Ties** is an agentic blueprint for Open Swarm, demonstrating robust agent-based search and analysis over family data with unified UX, ANSI/emoji output, spinner feedback, and resilient fallback for LLM/agent errors.

---

## What This Blueprint Demonstrates
- **Agent-based orchestration** for search and analysis
- **LLM fallback and error handling** with user-friendly messages
- **Unified ANSI/emoji boxes** for search/analysis results, including summaries, counts, and parameters
- **Custom spinner messages**: 'Generating.', 'Generating..', 'Generating...', 'Running...'
- **Progress updates** for long-running searches (line numbers, result counts)
- **Test mode** for robust, deterministic testing

## Usage
Run with the CLI:
```sh
swarm-cli run family_ties --instruction "Find all cousins of Jane Doe born after 1950"
```

## Test
```sh
uv run pytest -v tests/blueprints/test_family_ties.py
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
- See `blueprint_family_ties.py` for agent logic and UX hooks.
- Extend agent capabilities or UX by modifying the `_run_non_interactive` and `run` methods.

---
_Last updated: 2025-04-21_
