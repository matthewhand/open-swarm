# WhingeSurf Blueprint

**WhingeSurf** is an agentic blueprint for Open Swarm, demonstrating agent-based LLM communication for web search and complaint analysis, with unified ANSI/emoji UX, spinner feedback, and resilient fallback for LLM/agent errors.

---

## What This Blueprint Demonstrates
- **Agent-based LLM orchestration** for web search and analysis
- **LLM fallback and error handling** with user-friendly messages
- **Unified ANSI/emoji boxes** for search/analysis results, including summaries, counts, and parameters
- **Custom spinner messages**: 'Generating.', 'Generating..', 'Generating...', 'Running...'
- **Progress updates** for long-running operations (line numbers, result counts)
- **Test mode** for robust, deterministic testing

## Usage
Run with the CLI:
```sh
swarm-cli run whinge_surf --instruction "Analyze recent complaints about airline delays."
```

## Test
```sh
uv run pytest -v tests/blueprints/test_whinge_surf.py
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
- See `blueprint_whinge_surf.py` for agent logic and UX hooks.
- Extend agent capabilities or UX by modifying the `_run_non_interactive` method.

---
_Last updated: 2025-04-21_
