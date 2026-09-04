# REQ-3

Intent: the operator shell is usable as a daily chat + team launcher, not a dump of headings and dead sockets.

Success:
1. Blueprint source is pretty Python (Prism on `/blueprint-library/.../source`, not a raw dump).
2. Team Launcher POSTs carry CSRF; Save as team persists; load-to-repopulate fills the form; Unsaved working copy is labelled until saved.
3. Sidepane has no leftover “Agents” heading; HTML5 drag-and-drop favourites (no extra DnD library).
4. Compact / oversight chat density for long threads.
5. Live CLI and API proof (one-shot CLI adapter, `/v1/chat/completions`).
6. `/chat` WebSockets on :8001 actually connect (ASGI/Daphne), not a silent hang.

Constraints: No extra UI frameworks. Django Bootstrap + SPA daisyUI only.

Owner: open-swarm engineer.
