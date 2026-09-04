# REQ-46 — Dropdown changes appear in chat history

**Status:** in flight (this PR)

## Intent

When the user changes a chat dropdown (team member, CLI, model, or similar), the **transcript** records a bubble-less status line so the context history shows what changed — not only the next reply.

## Success

1. Team mode: changing a member/send-target dropdown inserts a bubble-less statement (Grok-Bot-style centred/status chrome, not a user/assistant bubble) naming what changed (from → to).
2. **Any** equivalent dropdown: e.g. CLI `antigravity` → `grok`, model/profile switch, remote/CLI mode. Same treatment.
3. Line persists with the thread (chat JSON / existing persist path). Reopening the chat still shows it in order.
4. Tests: switching CLI or team target appends one status event; it is not rendered as `chat-start`/`chat-end` bubble; reload keeps it.

## Constraints

- React 18 + Vite + Tailwind 4 + DaisyUI 5.
- Do **not** fold into chrome PR #344 (already crowded). New PR from current main, `Fixes` this issue.
- No live preview checkout. No secrets.

## Owner

- Cursor cloud from current main after engineer quotes + feasibility.
