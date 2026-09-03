# REQ-43 — Default LLM and per-task overrides

**Status:** this PR — in flight (`Fixes #358`)

## Intent

Settings lets you pick a default inference profile and, with a toggle, override
that default per task class so cheap work stays on auxiliary and heavy work can
use delegation.

## Success

- Settings → LLM profiles (SPA sheet, not a Django eject) lists configured
  profiles from connected CLIs / APIs / remotes and a **Default** picker.
- Default persists as `settings.default_llm_profile` (existing SoT). Chat /
  server default model uses that default. Auto-picks fill Default + the map
  when the user never opens the picker.
- **Override per task** off = everything uses Default. On: user chat →
  orchestration; code summary (#356 hook) → auxiliary; design / coding →
  delegation. Missing id warns and falls back to Default.
- `orchestration` / `auxiliary` / `delegation` are optional aliases, not
  required model ids. Boring ids (`gpt-5.6-terra`) are valid.

## Constraints

- React 18 + Vite + Tailwind 4 + DaisyUI 5. Reuse existing LLM profile config.
- No guest auth. No Neon. No secrets in the PR or tests.
- New PR from current main — do not fold into #344 or #356.

## Owner

- CoS transcribes
- cloud implements
- engineer GitHub-merge after skeptic
