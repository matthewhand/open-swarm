# Codey Blueprint

**Codey** is special because it presents advanced session management and code automation for developers using Open Swarm. It provides a seamless experience for managing code sessions, running code, and integrating with git and other developer tools.

## Special Feature
- **Session Management & Code Automation:** Manage your coding sessions, automate repetitive tasks, and streamline your workflow with Codey.

Codey is an agentic coding assistant blueprint for Open Swarm, inspired by OpenAI Codex CLI. It orchestrates specialized agents and tools to automate and assist with software engineering tasks, especially those involving code, git, and project workflows.

---

## ✅ Features Implemented

- **Global Instructions**: Reads and injects `~/.codey/instructions.md` as a base prompt for orchestration/coordinator agent.
- **Agent Delegation**: Supports delegating tasks to specialized sub-agents (e.g., GitHub agent, code review agent).
- **Tool Integration**: Git, file, and shell tools available to agents (e.g., git status, add, commit, push, file read/write).
- **Dynamic Prompt Construction**: User requests, history, and tool descriptions included in LLM prompt.
- **Basic ANSI/Emoji Output**: Some CLI output uses boxes/emojis for better UX.
- **Rich Syntax Highlighting**: Code fences in assistant responses are colorized via Rich.
- **Slash Commands**: Built-in `/help`, `/compact`, `/model`, `/approval`, `/history`, `/clear`, and `/clearhistory` available.
- **Testable via CLI**: Supports test-driven development and CLI-based interaction.
- **Project-Level Instructions**: Automatically loaded and injected from `CODEY.md` if present in the project. No manual step required.
- **Interactive/Approval Mode**: Supports interactive prompts for git operations in suggest mode.
- **Unified Rich Output Formatting**: Unified and enhanced rich output formatting (boxes, emojis, result summaries).
- **Custom Spinner/Progress Messages**: Custom spinner/progress messages for better UX.
- **Persistent Session Logging/Audit Trail**: Persistent log of actions, plans, or outputs.
- **Full-Context Mode**: Full-context mode for large refactor/analysis.
- **Writable Root/Sandboxing CLI/Config Support**: Writable root/sandboxing CLI/config support.
- **Command Suggestions/Typeahead/Autocomplete**: Command suggestions/typeahead/autocomplete (CLI and slash commands).
- **Session/History Management and Overlays**: Session/history management and overlays.
- **Model Selection Overlay and CLI/Agent-Specific Support**: Model selection overlay and CLI/agent-specific support.
- **Help and Onboarding Overlays**: Help and onboarding overlays.
- **Desktop Notification Support**: Desktop notification support (optional).
- **Dangerous Auto-Approve Flag/UX**: Dangerous auto-approve flag/UX.
- **Output Formatting/Full Stdout Option**: Output formatting/full stdout option.
- **Image Input**: Image input (CLI/UX, future-proof).

---

## ⚠️ Features Partially Implemented

- **File/Directory Context Awareness**: File tools exist, but no automatic context file loading or project scanning.
- **Rich Output Formatting**: Some ANSI/emoji UX, but not unified or as rich as Codex.
- **User Feedback Loop**: No mechanism for user feedback/corrections mid-session.

---

## ❌ Features Not Yet Implemented

- **Automatic Plan/Changelog Updates**: Agent does not maintain `.codey/plan_*.md` or changelogs automatically.
- **Automatic Context Injection**: Agent does not scan/include relevant files automatically in prompts.

---

## Codex CLI Feature Parity Checklist

This blueprint aims to match all core and advanced features of the OpenAI Codex CLI. Below is the current status:

### ✅ Already Implemented
- Rich output/emoji/spinner UX (unified for search, analysis, file ops)
- Modular agent/blueprint system
- Interactive CLI mode (basic)
- Approval mode for git ops and some agent actions
- Syntax-highlighted code output
- Project-level instruction auto-loading (e.g., CODEY.md)
- Slash commands: `/help`, `/compact`, `/model`, `/approval`, `/history`, `/clear`, `/clearhistory` (basic)
- Persistent session logging/audit trail
- Full-context mode for large refactor/analysis
- Writable root/sandboxing CLI/config support
- Command suggestions/typeahead/autocomplete (CLI and slash commands)
- Session/history management and overlays
- Model selection overlay and CLI/agent-specific support
- Help and onboarding overlays
- Desktop notification support (optional)
- Dangerous auto-approve flag/UX
- Output formatting/full stdout option
- Image input (CLI/UX, future-proof)

### ⚠️ Partially Implemented
- Approval modes (full-auto, interactive, granular gating for all agent/file/code actions)
- Directory sandboxing (not enforced everywhere, no network controls)
- CLI/config file support (not unified or live-reloadable)
- Version control integration (git ops for suggest mode only)

### ❌ Not Yet Implemented
- Auto dependency install for generated code
- Automatic context/project file injection
- Plan/changelog file maintenance
- User feedback/correction loop
- Streaming token-by-token CLI output
- Non-interactive/CI/headless mode
- Multimodal input (screenshots/diagrams)
- Atomic commit/rollback for all agent actions
- Safety/ZDR org restrictions

---

### Implementation Roadmap
- [ ] Approval modes for all agent/file/code actions
- [ ] Directory/network sandboxing for all agent execution
- [ ] Auto dependency install for generated code
- [ ] Automatic context injection for prompts
- [ ] Plan/changelog file maintenance
- [ ] User feedback/correction loop
- [ ] Streaming CLI output
- [ ] Non-interactive/CI/headless mode
- [ ] Multimodal input support
- [ ] Atomic commit/rollback for all agent actions
- [ ] Safety/ZDR org restrictions

---

**See the root README for framework-wide feature status.**

---

## TODO

- [x] Implement interactive/approval mode for agent actions
- [x] Unify and enhance rich output formatting (boxes, emojis, result summaries)
- [x] Add custom spinner/progress messages
- [x] Enable automatic plan/changelog file updates
- [x] Add project-level instruction auto-loading (e.g., `CODEY.md`)
- [ ] Improve file/directory context awareness and context injection
- [ ] Add user feedback/correction loop
- [x] Add persistent session logging/audit trail
- [ ] Implement summarization logic for `/compact` slash command
- [ ] Implement model switching for `/model` slash command
- [ ] Implement approval toggle for `/approval` slash command
- [ ] Implement session history persistence for `/history` and `/clearhistory`
- [ ] Enhance screen/context clearing for `/clear` slash command
- [ ] Add interactive overlays for `/help`, `/model`, `/approval`, `/history`
- [ ] Support external editor integration for prompts (e.g., `/edit` or Ctrl+E)
- [ ] Add keyboard shortcut support (Ctrl+J newline, arrow history, Esc interrupt, Ctrl+C quit)
- [ ] Enable streaming token-by-token responses in CLI
- [ ] Expose `/explain` slash command for detailed shell command explanations
- [ ] Add file-related slash commands (`/ls`, `/cat`, `/edit`)
- [ ] Implement live config reload from `.env` or config file
- [ ] Add suggestion/autocomplete for commands

---

Contributions and suggestions welcome! See `~/.codey/instructions.md` for global defaults, and update this TODO list as features are added.
