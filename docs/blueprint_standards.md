# Open Swarm Blueprint Standards

## Purpose
Every blueprint in Open Swarm demonstrates a unique agentic pattern, LLM workflow, or user experience. This document sets clear standards for output, UX, and implementation so that every blueprint is polished, testable, and easy to extend.

---

## 1. Output Box Standards
- Use `print_search_progress_box` or `print_operation_box` for all agent outputs.
- The first visible line in the box must be the first result line (test compliance).
- No stray output before or after the box.
- Boxes must include:
  - Operation type/title and emoji
  - Themed spinner/progress messages
  - Parameters and summary (when relevant)
  - Result lines (assertion/testable content)

---

## 2. Spinner and Progress Messaging
- Spinner states must be custom and thematic for each blueprint (e.g., “Summoning thunder... ⚡” for Zeus).
- If an operation takes longer than expected, update spinner to a friendly, themed message (e.g., “Generating... Taking longer than expected ⚡”).
- Progress lines (e.g., “Step X/Y”) should be included for multi-step operations.

---

## 3. LLM Provider Fallback
- All agent runners must attempt LLM calls with fallback across configured providers.
- Log each attempt and its result (provider, endpoint, sanitized error message) for auditability.
- Never expose API keys or secrets in logs or output.
- If all providers fail, output a clear, user-friendly error in the output box.

---

## 4. Blueprint Purpose and Theming
- Each blueprint must have a clear demonstration purpose, reflected in its code, spinner, and output.
- Spinner messages, summary, and result lines should reinforce the blueprint’s theme.
- Add docstrings and comments explaining the blueprint’s intent and UX conventions.

---

## 5. Parameter and Progress Transparency
- Always show relevant parameters (keywords, instructions, etc.) and progress inside the output box.
- Summaries and result counts should be clear and easy to find.

---

## 6. Code Quality and Extensibility
- No hardcoded secrets or magic values.
- Reuse utilities for output, spinner, and fallback logic.
- Code should be DRY, modular, and easy to extend for new blueprints.

---

## 7. Test Compliance
- All expected assertion strings for tests must appear in the correct order.
- No extra newlines or stray prints.

---

## 8. Documentation
- Each blueprint should have docstrings and comments.
- Update this file as standards evolve.
- Use the Geese blueprint as a reference for best practices.

---

## 9. Test Mode and Automated Compliance
- All blueprints must emit deterministic spinner/box/emoji/summary output in test mode (`SWARM_TEST_MODE=1`).
- Compliance is checked via robust tests in `tests/blueprints/` and the `scripts/check_ux_compliance.py` utility.
- Blueprints that do not emit all required UX elements in test mode will raise warnings, not failures, to surface issues for future improvements.
- See also: `docs/blueprint_test_mode_ux.md`.

---

## Example: Polished Output Box

```
╔══════════════════════════════════════════════════════════════╗
│ ⚡ Zeus Agent Run                                            │
│ Step 2/4                                                    │
│ Summoning thunder... ⚡                                      │
│ Instruction: "Find all uses of 'asyncio'"                   │
│ Zeus agent is running your request... (Step 2)              │
╚══════════════════════════════════════════════════════════════╝
```

If slow:
```
╔══════════════════════════════════════════════════════════════╗
│ ⚡ Zeus Agent Run                                            │
│ Step 4/4                                                    │
│ Generating... Taking longer than expected ⚡                 │
│ Storm clouds gathering...                                   │
╚══════════════════════════════════════════════════════════════╝
```

---

## Reference
- See `src/swarm/blueprints/geese/blueprint_geese.py` for a model implementation.
- For questions or to propose changes, open a PR or contact a maintainer.
