# Session Handoff Report: Post-Refactor Cleanup & Next Steps

**Date:** 2025-03-29

**Current Status:**

*   **Core Refactoring Complete:** All major blueprints (`burnt_noodles`, `rue_code`, `nebula_shellz`, `digitalbutlers`, `dilbot_universe`, `gaggle`, `family_ties`, `mission_improbable`, `whiskeytango_foxtrot`, `divine_ops`, `omniplex`, `unapologetic_press`, `chatbot`, `echocraft`, `suggestion`, `monkai_magic`) have been refactored to inherit from `BlueprintBase`.
*   **Design Patterns:**
    *   Agent-as-tool delegation is the primary pattern for coordination.
    *   Direct `@function_tool` usage is employed for local CLI wrappers (`burnt_noodles`, `monkai_magic`).
    *   MCP servers provide capabilities to specialist agents (`digitalbutlers`, `divine_ops`, `wtf`, `mission_improbable`, `omniplex`, `unapologetic_press`).
    *   Dynamic configuration via SQLite demonstrated (`dilbot_universe`, `mission_improbable`, `unapologetic_press`).
    *   Structured output via `output_type` demonstrated (`suggestion`).
*   **BlueprintBase Enhancements:**
    *   Added MCP server `description` field support in config (`get_mcp_server_description` helper).
    *   Added check for missing `env_vars` specified in blueprint metadata.
    *   Corrected default markdown logic for CLI mode (`use_markdown` defaults to True).
    *   Added (then reverted due to errors) MCP startup timeout logic. **The timeout logic caused `TypeError: '_GeneratorContextManager' object does not support the asynchronous context manager protocol` and was removed.** This needs further investigation, possibly using `asyncio.wait_for` instead of `anyio.fail_after` around the `stack.enter_async_context` call.
*   **Configuration:** `swarm_config.json` updated with new `git` and `google-cse` servers and example `description` / `startup_timeout` fields. Syntax error fixed.
*   **Testing:** Placeholder test files created for all refactored blueprints. Most tests are currently skipped (`reason="...not yet implemented"`). Existing config tests pass.

**Immediate Issues:**

*   **MCP Startup Timeout:** The `anyio.fail_after` implementation caused TypeErrors. The timeout logic in `_start_mcp_server_instance` has been **reverted**. MCP server startup failures might still hang indefinitely. **Investigate alternative timeout implementations (e.g., `asyncio.wait_for`)**.
*   **MCP Failures:** Some MCP servers failed to start in the last run (`slack`, `mondayDotCom`, `basic-memory`, `mcp-npx-fetch`), triggering the blueprint failure logic correctly. Root cause unknown (could be network, dependencies, config, etc.).

**Next Tactical Steps:**

1.  **Fix MCP Startup Timeout:** Re-implement a working timeout mechanism for `_start_mcp_server_instance`. `asyncio.wait_for(stack.enter_async_context(server_instance), timeout=startup_timeout)` might be a better approach. Test thoroughly.
2.  **Refactor Remaining Blueprints:**
    *   `chucks_angels` (Needs UVX/NeMo investigation or simplification).
    *   `django_chat` (Decide whether to keep Django dependency or refactor).
    *   `flock` (Implement based on original intent).
    *   `messenger` (Implement based on original intent).
3.  **Implement Guardrails:**
    *   Research `openai-agents`'s intended guardrail mechanism (likely via config).
    *   **Target Blueprints:** `DivineOps`, `MonkaiMagic`, `WhiskeyTangoFoxtrot` (due to shell/fs/web access).
    *   Define basic guardrail configs (e.g., prevent dangerous shell commands, filter topics).
    *   Modify `create_starting_agent` in target blueprints to potentially load and pass guardrail configs to relevant `Agent` instances.
4.  **Enhance Agent Synergy / Dynamic Prompts:**
    *   **Omniplex:** Modify `OmniplexCoordinator` instructions to use MCP descriptions (fetched via `self.get_mcp_server_description`) to explain available tools. Implement logic to choose *one* search provider if multiple (brave, google, ddg) are available and started.
    *   **Other Coordinators (e.g., Zeus, Valory):** Update instructions to dynamically include descriptions of the agent tools and the MCP tools *their* delegate agents have access to, using `self.get_mcp_server_description`.
5.  **Parallel Tool Calls Demo:**
    *   Design and implement a simple blueprint where the coordinator needs independent info from two different tools/agents simultaneously (e.g., read local file + web search).
    *   Verify that the `Runner` executes these concurrently if the LLM returns multiple `tool_calls`.
6.  **Update Blueprints README:** Regenerate or manually edit `blueprints/README.md` table to accurately reflect the status, features, and MCP usage of all blueprints post-refactoring. Ensure descriptions match the updated code.
7.  **Implement Skipped Tests:** Gradually unskip and implement tests in `tests/blueprints/`, focusing on:
    *   Agent creation and tool assignment.
    *   Basic delegation flows (mocking `Runner.run` or agent `process` methods).
    *   Direct testing of `@function_tool` functions.

**Strategic Considerations:**

*   **Guardrails Integration:** How deeply should guardrails be integrated? Per-agent? Global? Config-driven?
*   **Error Handling:** Standardize error reporting from tools and MCP interactions back to the coordinator.
*   **Testing Strategy:** Develop robust strategies for mocking MCP interactions and complex multi-agent flows.
*   **UI Elements:** Revisit custom spinners/prompts if essential, potentially via external wrappers or modifications to `BlueprintBase.main`.

**Tips & Hints:**

*   **Timeout:** Focus on `asyncio.wait_for` around `stack.enter_async_context(server_instance)` in `_start_mcp_server_instance`.
*   **Dynamic Prompts:** Use f-strings and loops within `create_starting_agent` to build instructions dynamically using `self.get_mcp_server_description(server_name)` for available servers/tools.
*   **Parallel Calls:** Requires an LLM that supports generating multiple `tool_calls` and an agent logic that makes independent requests suitable for parallel execution.
*   **Testing:** Start with unit tests for tools and basic agent creation tests (mocking dependencies). Integration tests require more effort.

Good luck!
