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
- `divine_code` (divine_code/blueprint_divine_code.py)
- `django_chat` (django_chat/blueprint_django_chat.py)
- `echocraft` (echocraft/blueprint_echocraft.py)
- `geese` (geese/blueprint_geese.py)
- `jeeves` (jeeves/blueprint_jeeves.py)
- `mcp_demo` (mcp_demo/blueprint_mcp_demo.py)
- `mission_improbable` (mission_improbable/blueprint_mission_improbable.py)
- `monkai_magic` (monkai_magic/blueprint_monkai_magic.py)
- `nebula_shellz` (nebula_shellz/blueprint_nebula_shellz.py)
- `omniplex` (omniplex/blueprint_omniplex.py)
- `poets` (poets/blueprint_poets.py)
- `rue_code` (rue_code/blueprint_rue_code.py)
- `stewie` (stewie/blueprint_family_ties.py)
- `suggestion` (suggestion/blueprint_suggestion.py)
- `whinge_surf` (whinge_surf/blueprint_whinge_surf.py)
- `whiskeytango_foxtrot` (whiskeytango_foxtrot/blueprint_whiskeytango_foxtrot.py)
- `zeus` (zeus/blueprint_zeus.py)

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
import asyncio
from swarm.extensions.cli.utils.async_input import async_cli_input

async def main():
    while True:
        user_input = await async_cli_input()
        print(f"You typed: {user_input}")
        await asyncio.sleep(0.05)
```
This pattern is now used in the `codey` and `poets` blueprints for unified, responsive CLI UX.

## TODO
- [ ] Flesh out code examples for each config pattern.
- [ ] Link to main README and ensure discoverability.
- [ ] Document framework-wide async CLI input handler pattern.

---
*This README documents implemented features and standards. For feature status, see the main project TODOs.*
