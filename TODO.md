# Swarm Configuration & System TODOs

## Critical Missing Tests
- [x] Test XDG config discovery and fallback order.
- [x] Test default config auto-generation when no config is found.
- [x] Test envvar/placeholder substitution in config loader.
- [ ] Test per-blueprint and per-agent model override logic.
- [ ] Test fallback to default model/profile with warning if requested is missing.
- [ ] Test MCP server config add/remove/parse.
- [ ] Test redaction of secrets in logs and config dumps.

## Unified UX Enhancements (Spinner, ANSI/Emoji Boxes)
- [ ] Implement and verify enhanced ANSI/emoji operation boxes for search and analysis operations across all blueprints. Boxes should:
    - Summarize search/analysis results (e.g., 'Searched filesystem', 'Analyzed ...')
    - Include result counts and display search parameters
    - Update line numbers/progress during long operations
    - Distinguish between code/semantic search output
    - Use emojis and box formatting for clarity
- [ ] Implement spinner messages: 'Generating.', 'Generating..', 'Generating...', 'Running...', and 'Generating... Taking longer than expected' for all blueprints (Codey, Geese, Jeeves, RueCode, Zeus, WhingeSurf)
- [ ] Add system/integration tests that objectively verify the above UX features in CLI output (spinner, boxes, progressive updates, emojis, etc.)

## Code Fixes
- [x] Add XDG path (`~/.config/swarm/swarm_config.json`) as the first search location in config discovery. (Already implemented)
- [ ] Revise and update `blueprints/README.md` to reflect current blueprints, configuration, UX expectations, and modular/provider-agnostic patterns. Ensure it is discoverable and referenced from the main README.
- [ ] Implement async CLI input handler for all blueprints: allow user to continue typing while previous response streams. If Enter is pressed once, warn: "Press Enter again to interrupt and send a new message." If Enter is pressed twice, interrupt the current operation and submit the new prompt. (Framework-wide, inspired by whinge_surf request)
