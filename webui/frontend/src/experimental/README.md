# Experimental SPA additions

Opt-in UX experiments living outside the core page flow. Everything here is
**on by default for review** and can be disabled per-feature without a rebuild:

```js
// In the browser console, then reload:
localStorage.setItem('swarm_experimental_command_palette', 'off')
localStorage.setItem('swarm_experimental_chat_message_actions', 'off')
```

| Flag | File | What it does |
|------|------|--------------|
| `command_palette` | `CommandPalette.tsx` | ⌘K / Ctrl+K fuzzy launcher across SPA routes + Django operator pages + theme flip. Combobox/listbox ARIA pattern; Esc closes; arrows navigate. |
| `chat_message_actions` | `ChatMessageActions.tsx` | Copy (raw markdown) on every assistant bubble; Retry re-sends your last prompt on the final bubble once streaming completes. |

## Also in this changeset (not flag-gated — judged as fixes/quality-of-life)

- Theme preference now persists (`swarm_theme`, default dark to match Django).
- Dashboard stats poll every 30s via react-query instead of a one-shot fetch.
- Scroll anchoring during streaming only follows when you're already near the
  bottom (reading history mid-stream is no longer yanked).
- Assistant bubbles are memoized so finished messages don't re-render markdown
  on every streamed chunk.

## Promotion / removal

If an experiment proves itself: move the component into `src/components/` or
`src/pages/`, drop the flag check, delete it from this README. If not, delete
the file and its integration point(s):

- `CommandPalette` → mounted in `App.tsx`
- `ChatMessageActions` → rendered in `pages/ChatPage.tsx`
