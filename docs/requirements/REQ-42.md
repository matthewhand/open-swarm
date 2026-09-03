# REQ-42 — Role badge → explained definition pane

**Status:** PR in flight — Fixes #356

## Intent

Clicking a **role badge** (or a blueprint / team identity that has a definition)
opens a Settings pane that **explains** how that seat works. If a default LLM is
configured, that model summarises the real source plus injected metadata. The
operator can Edit code, then ask the LLM to re-summarise.

This is not REQ-25 hover-edit (PR #334): that opens the Blueprint Python editor.
The badge itself is the click target, and the pane leads with a human brief.

## Success

1. Clicking a role badge (support / gate / skeptic / CoS / others) opens the
   DaisyUI `modal-end` Settings sheet focused on **that** definition. Same
   pattern for a team identity badge or chat-header identity.
2. The pane leads with a brief human explanation (gate YES/NO, skeptic retry,
   support Socratic, CoS talk-to-any-team) — not a raw file dump.
3. If a default LLM is configured (`LITELLM_MODEL` / `OPENAI_MODEL` /
   `DEFAULT_LLM`, same as `respond_with_default_model`): that client summarises
   the actual source plus injected detail (system prompt, tools, metadata,
   handoff/as-tool wiring, extra runtime context). If no default LLM, keep the
   static brief and a disabled/missing-model hint. No second inference stack.
4. **Edit code** opens the source editor. After save, **Re-summarise** refreshes
   the LLM against the new source + injections.
5. Tests: badge click opens the pane for that id; explanation visible without
   LLM; stub/default LLM summary includes `REQ42_INJECTED_FIXTURE_MARKER`;
   edit + re-summarise updates the shown text.

## Constraints

- React 18 + Vite + Tailwind 4 + DaisyUI 5. Reuse SettingsSheet (PR #320) and
  Grok chrome (PR #322). Do not fold into PR #334 or PR #344.
- No guest auth. No Neon. No secrets/tokens/personal dumps in prompts or tests
  (fixtures / placeholders only).

## Owner

- CoS transcribes
- cloud implements
- engineer GitHub-merge after skeptic
