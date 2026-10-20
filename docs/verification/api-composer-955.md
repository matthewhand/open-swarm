# API composer and token usage (#955)

API seats now share one composer surface around the draft, controls and Send
button. Its usage disclosure expands upward with Context used and Last reply
cards, a breakdown, estimate/reported labels, and a context-capacity bar only
when the backend supplies a positive limit. Advanced token diagnostics remain
available through More details. CLI, remote and team composer paths are unchanged.

Local verification on Windows, 2026-10-21:

- Production frontend build and TypeScript check passed.
- Eight focused Vitest files: 160 tests passed, including eight new usage-panel
  tests for unknown/missing limits, over-capacity values, live updates, keyboard
  dismissal, diagnostics and accidental form submission.
- Chromium: 22 tests passed. Five new cases exercise API send, Shift+Enter,
  expandable usage, frame/Send geometry, focus restoration and horizontal overflow
  at 320, 375, 401, 768 and 1280 pixels. The other 17 protect message actions and
  navbar placement from regressions.
- Visually inspected the real inventory-demo conversation at 401 × 605 pixels.
  The existing server usage endpoint supplied 107 context tokens and 76 last-reply
  tokens; the model did not report its context limit and no capacity was invented.
- The local full backend attempt stopped after 119 passing tests on
  `test_minted_conversation_resumes_across_turns[agy]`: the Windows asyncio event
  loop raised `NotImplementedError` while creating a subprocess transport.
  No backend or backend-test files changed in this PR. This local attempt is not
  a full backend pass; the Linux Python suites and separate Windows process gate
  run in CI before merge.

The new browser regression tests use synthetic inference and usage responses;
they demonstrate UI behavior, not a new model or harness compatibility claim.
No model requests or private credentials are needed for these layout tests.
Full frontend/backend CI gates are required before merge.
