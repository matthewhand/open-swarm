# Open Swarm: Known Issues and TODOs

_Last updated: 2025-04-21_

## Skipped/Flaky/Soft Tests
- `tests/test_blueprint_loading.py`: All tests skipped due to dynamic INSTALLED_APPS complexity. **Action:** Refactor to enable test coverage or document why this is not possible.
- `tests/blueprints/test_chatbot.py`: Skips if dependencies are missing. **Action:** Ensure dependencies are installed or mock them for testing.
- `tests/blueprints/test_codey.py`: Skips if CLI utility not found. **Action:** Ensure codey blueprint is enabled or provide a mock.

## Error Handling and Logging
- Many tools and modules (audit_viz.py, blueprint_qa.py, message serialization, etc.) log errors/warnings but do not raise or fail. **Action:** Patch to raise exceptions or exit nonzero on critical errors; ensure user-facing errors are actionable.

## TODO/FIXME/DEPRECATED/Warning Comments
- Numerous TODO, FIXME, and DEPRECATED comments found in core modules (e.g., ChatMessage, tool calls, etc.). **Action:** Systematically address or triage; if not immediately fixable, keep tracked here.

## Deprecated Fields
- `ChatMessage.function_call` is marked as deprecated but still present in code. **Action:** Remove or fully document deprecation timeline.

## Logging and Error Surfacing
- Some flows only log errors and do not fail tests or CLI. **Action:** Harden error handling across all CLI, API, and blueprint flows.

## General Recommendations
- Sync this file with GitHub Issues for better user visibility and tracking.
- Update documentation to reflect known issues and troubleshooting steps.

---

_This file is auto-generated and should be updated as issues are fixed or discovered._
