# Chatbot Blueprint

**Chatbot** is an agentic conversational blueprint for Open Swarm, demonstrating agent-based conversation flows, robust fallback for LLM/agent errors, and unified ANSI/emoji UX with spinner feedback.

---

## What This Blueprint Demonstrates
- **Agent-based conversational orchestration**
- **LLM fallback and error handling** with user-friendly messages
- **Unified ANSI/emoji boxes** for conversation output, including summaries and fallback
- **Custom spinner messages**: 'Generating.', 'Generating..', 'Generating...', 'Running...'
- **Test mode** for robust, deterministic testing

## Usage
Run with the CLI:
```sh
swarm-cli run chatbot --instruction "What is the weather today?"
```

## Test
```sh
uv run pytest -v tests/blueprints/test_chatbot.py
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
- See `blueprint_chatbot.py` for agent logic and UX hooks.
- Extend agent capabilities or UX by modifying the `_run_non_interactive` method.

---
_Last updated: 2025-04-21_
