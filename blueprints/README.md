# Open Swarm Blueprints & Configuration

## Overview
This document describes the modular, provider-agnostic blueprint system, configuration patterns, and user experience (UX) standards for Open Swarm.

## Configuration System
- **XDG-compliant config discovery**
- **Default config auto-generation**
- **Environment variable substitution**
- **Per-blueprint and per-agent model overrides**
- **MCP server config parsing/selection**
- **Redaction of secrets**

## Blueprint Model/Profile Overrides
- Blueprints can specify their own `default_model`.
- Agents fall back to `settings.default_llm_profile` if the requested model/profile is missing.

## MCP Server Configuration
- Multiple MCP servers supported; select via `settings.active_mcp`.

## Security & Redaction
- All secrets are redacted in logs and dumps.

## User Experience (UX) Standards
- Enhanced ANSI/emoji boxes for search/analysis results.
- Custom spinner messages: `Generating.`, `Generating..`, `Generating...`, `Running...`, and `Generating... Taking longer than expected`.
- Async CLI input handler: allows typing while response streams, with double-Enter to interrupt.

## Current Blueprints
These blueprints are included as examples and can be used or extended:

- `chatbot` (chatbot/blueprint_chatbot.py)
- `codey` (codey/blueprint_codey.py)
- `digitalbutlers` (digitalbutlers/blueprint_digitalbutlers.py)
- `divine_code` (deprecated, use zeus)
- `django_chat` (django_chat/blueprint_django_chat.py)
- `echocraft` (echocraft/blueprint_echocraft.py)
- `family_ties` (family_ties/blueprint_family_ties.py)
- `geese` (geese/blueprint_geese.py)
- `jeeves` (jeeves/blueprint_jeeves.py)
- `mcp_demo` (mcp_demo/blueprint_mcp_demo.py)
- `mission_improbable` (mission_improbable/blueprint_mission_improbable.py)
- `monkai_magic` (monkai_magic/blueprint_monkai_magic.py)
- `nebula_shellz` (nebula_shellz/blueprint_nebula_shellz.py)
- `omniplex` (omniplex/blueprint_omniplex.py)
- `poets` (poets/blueprint_poets.py)
- `rue_code` (rue_code/blueprint_rue_code.py)
- `suggestion` (suggestion/blueprint_suggestion.py)
- `whinge_surf` (pending implementation; no blueprint_whinge_surf.py yet)
- `whiskeytango_foxtrot` (whiskeytango_foxtrot/blueprint_whiskeytango_foxtrot.py)
- `zeus` (see divine_code/blueprint_divine_code.py; no standalone blueprint_zeus.py)

All DivineOpsBlueprint and divine_code functionality is now part of ZeusBlueprint. All references to DivineOps or divine_code are historical only; use ZeusBlueprint for all new development, tests, and documentation.

For more details on each, see the corresponding Python file.

## Discoverability
- This file is referenced from the main [README.md](../README.md) and should be your starting point for blueprint usage, extension, and best practices.

## Best Practices for Blueprint Authors
- Subclass `BlueprintBase` and document required environment variables and MCP servers.
- Use provider-agnostic config patterns for maximum portability.
- Leverage the UX standards (ANSI/emoji boxes, spinner, async CLI input) for a unified experience.

## Async CLI Input Handler (Pattern)
Blueprints should support async user input:
- While a response is streaming, the user can type a new prompt.
- Pressing Enter once warns: "Press Enter again to interrupt and send a new message."
- Pressing Enter twice interrupts the current operation.
- See framework utilities (`src/swarm/extensions/cli/utils/async_input.py`) or blueprint examples (`codey`, `poets`) for implementation guidance.

### Example Usage (Codey/Poets)
```python
from swarm.extensions.cli.utils.async_input import AsyncInputHandler
handler = AsyncInputHandler()
print("You: ", end="", flush=True)
user_input = ""
warned = False
while True:
    inp = handler.get_input(timeout=0.1)
    if inp == 'warn' and not warned:
        print("\n[!] Press Enter again to interrupt and send a new message.", flush=True)
        warned = True
    elif inp and inp != 'warn':
        user_input = inp
        break
    await asyncio.sleep(0.05)
```
This pattern is now used in the `codey` and `poets` blueprints for unified, responsive CLI UX.

## RueCode Blueprint: Real Output Example

After fixing missing features, RueCode now produces the following output for a code search:

```
╔══════════════════════════════════════════════════════════════════╗
RueCode Run
Step 1/4
Generating.
User instruction received
│ 📝 RueCode Run
║ Show me how Rue Code does templating and swarm execution.
╚══════════════════════════════════════════════════════════════════╝
...
RueCode Search
Processed
Generating... Taking longer than expected
Searched filesystem for: 'Show me how Rue Code does templating and swarm execution.'
│ 📝 RueCode Search
║ RueCode Search
║ ./src/swarm/blueprints/rue_code/blueprint_rue_code.py:598: {"role": "user", "content": "Show me how Rue Code does templating and swarm execution."}
║ Processed
╚══════════════════════════════════════════════════════════════════╝
...
RueCode agent response
│ 📝 RueCode Run
║ Code Search complete. Found 1 matches for 'Show me how Rue Code does templating and swarm execution.'.
╚══════════════════════════════════════════════════════════════════╝
```

- **Spinner Sequence:** `Generating.`, `Generating..`, `Generating...`, `Running...`, `Generating... Taking longer than expected`
- **Output Boxes:** Clearly show operation, progress, and results.
- **Result Count:** Number of matches found is displayed.
- **No sensitive data is shown.**

### Usage

To run RueCode blueprint:

```bash
python -m swarm.blueprints.rue_code.blueprint_rue_code
```

Or, for CLI (if implemented):

```bash
swarm-cli run rue_code --instruction "find all TODOs"
```

---

As each blueprint is fixed, this documentation will be updated with real, working output and usage instructions.

## Divine Code Blueprint: Real Output Example

After recent incremental improvements, Divine Code now produces the following output:

```
╔══════════════════════════════════════════════════════════════════╗
Divine Code Inspiration
Step 1/18
Generating.
Divine code inspiration for: 'Inspire me!'
│ ✨ Divine Code Inspiration
║ Seeking divine code for 'Inspire me!'...
╚══════════════════════════════════════════════════════════════════╝
...
Divine Code Inspiration
Step 18/18
Generating... Taking longer than expected
Divine code inspiration for: 'Inspire me!'
│ ✨ Divine Code Inspiration
║ Seeking divine code for 'Inspire me!'...
║ Taking longer than expected
╚══════════════════════════════════════════════════════════════════╝
Divine Code Inspiration
Divine code inspiration for: 'Inspire me!'
│ ✨ Divine Code Inspiration
║ Invoking inspiration for: Inspire me!
║ Divine code inspiration complete for 'Inspire me!'.
║ Your divine code is: ```print('Hello, World!')```
╚══════════════════════════════════════════════════════════════════╝
```

- **Spinner Sequence:** `Generating.`, `Generating..`, `Generating...`, `Running...`, and `Generating... Taking longer than expected`
- **Output Boxes:** Clearly show operation, progress, and results with emoji and summary.
- **Final Result:** Shows inspiration summary and a code snippet.
- **No sensitive data is shown.**

### Usage

To run Divine Code blueprint:

```bash
python -m swarm.blueprints.divine_code.blueprint_divine_code
```

---

All documentation examples are validated with real output after each incremental improvement.

## Geese Blueprint: Real Output Example

After fixing the missing import, Geese now produces the following output:

```
Geese Agent Run
Step 1/4
Generating.
Geese agent run for: 'Tell me a story about teamwork'
╔══════════════════════════════════════════════════════════════════╗
Geese Agent Run
Step 1/4
Generating.
Geese agent run for: 'Tell me a story about teamwork'
│ 🪿 Geese Agent Run
║ Tell me a story about teamwork
║ Geese agent is running your request... (Step 1)
╚══════════════════════════════════════════════════════════════════╝
...
Geese Agent Run
Step 4/4
Generating... Taking longer than expected
Geese agent run for: 'Tell me a story about teamwork'
│ 🪿 Geese Agent Run
║ Tell me a story about teamwork
║ Geese agent is running your request... (Taking longer than expected)
╚══════════════════════════════════════════════════════════════════╝
Geese Creative
Creative generation complete for: 'Tell me a story about teamwork'
│ 🦢 Geese Creative
║ Creative story generated for 'Tell me a story about teamwork'.
╚══════════════════════════════════════════════════════════════════╝
```

- **Spinner Sequence:** `Generating.`, `Generating..`, `Generating...`, `Running...`, `Generating... Taking longer than expected`
- **Output Boxes:** Clearly show operation, progress, and results with emoji and summary.
- **Final Result:** Shows creative summary and a completion message.
- **No sensitive data is shown.**

### Usage

To run Geese blueprint:

```bash
python -m swarm.blueprints.geese.blueprint_geese "Tell me a story about teamwork"
```

---

All documentation examples are validated with real output after each incremental improvement.

## TODO
- [ ] Flesh out code examples for each config pattern.
- [ ] Add screenshots or demos of ANSI/emoji boxes and spinner states.
- [ ] Validate and document functional output for each blueprint after code changes:
    - [x] RueCode
    - [x] Divine Code
    - [x] Family Ties
    - [x] Geese
    - [ ] Gaggle (no output on CLI run)
    - [ ] Zeus (no output on CLI run)
- [ ] Ensure spinner and result boxes are standardized and compliant across all blueprints.
- [ ] Add troubleshooting for common blueprint errors (e.g., missing imports, CLI argument issues).

---
