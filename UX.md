# Open Swarm User Experience (UX) & Output Standards

## Overview
This document describes the unified output, spinner, and box UX conventions for all blueprints and CLI/API operations in Open Swarm. Adhering to these standards ensures a consistent, user-friendly, and test-compatible experience across the framework.

---

## 1. Unified Output Utilities

### `print_operation_box`
- Use this function from `swarm.core.output_utils` to display operation/result boxes for all search, analysis, and file ops.
- Boxes should summarize the operation (e.g., "Searched filesystem", "Analyzed code"), include result counts and parameters, and use relevant emojis for clarity.
- All output should be routed through this function for consistency.

### `pretty_print_response`
- Use this function for printing agent/assistant/chat responses, including code blocks and markdown.
- Supports both normal and test modes (inject a console for test capture).
- Handles code fence highlighting and sender/role prefixes.

---

## 2. Spinner & Progress Messages

- Use the shared spinner logic from `output_utils` or blueprint base classes.
- Supported spinner states: `Generating.`, `Generating..`, `Generating...`, `Running...`.
- For long-running operations, update the spinner to indicate progress (e.g., `Generating... Taking longer than expected`).
- Always include relevant emojis (e.g., 🌊 for WhingeSurf) for blueprint personality.

---

## 3. Test Mode & Output Suppression

- Use the `SWARM_TEST_MODE` environment variable to detect test runs.
- In test mode, suppress non-essential UX output, printing only results or minimal debug info.
- Ensure all output can be captured via injected console objects for reliable testing.

---

## 4. Blueprint Author Guidelines

- Always import and use the shared utilities (`print_operation_box`, `pretty_print_response`).
- Do not implement local/duplicate output or spinner logic.
- Remove or update any legacy TODOs related to spinner/UX; the unified system is now standard.
- For new blueprints, follow the output patterns in `codey`, `whinge_surf`, and `geese` as reference implementations.

---

## 5. Extending UX

- To add new output types or spinner personalities, extend the shared utilities in `swarm/core/output_utils.py`.
- Document any new UX patterns in this file for future contributors.

---

## 6. Further Reading
- See `README.md` for high-level overview and quickstart.
- See `src/swarm/blueprints/README.md` for blueprint-specific patterns.
- See `DEVELOPMENT.md` for contributor/developer details.

---

## Maintainers
If you have questions or want to propose UX enhancements, open an issue or PR on the repository.
