# Composer and physical-device sweep (#960, #957)

Focused fixes and regression coverage:

- Preserve continuation whitespace in both the model service and browser so
  accepting ` world` after `Hello` produces `Hello world`, not `Helloworld`.
- Clear disabled suggestions, cancel their debounce and abort obsolete browser
  requests on editing, changing targets, disabling the feature and unmounting.
- Respect composition keys and avoid querying the model for unfinished IME text.
- Prevent late AI rewrites from overwriting edited drafts or another agent/session;
  cancel their requests and suppress errors from cancelled work.
- Close the autocomplete service's SDK client on success and failure.
- Reset expanded usage when changing conversations within the same agent.
- Synchronize the Pi malformed-line regression with actual settlement, retaining
  event/text assertions instead of racing prompt acceptance (#957).
- Rename the message action and tooltip from “Compress to here” to “Compact”,
  including the alternate overlay and affected UI assertions. Cull mode keeps
  its separate “Start context from here” behavior.

- Prevent a delayed initial usage response or failure from replacing newer socket
  usage. Both outcomes were reproduced; updates now invalidate earlier requests.
- Use the dynamic viewport instead of the large mobile viewport. On the real
  phone the old shell was 592 CSS pixels tall while only 536 were visible, putting
  the expanded composer's bottom at 576. After fixing it, that bottom is 520.
- Bound the provider notice on short viewports so the soft keyboard cannot push
  the composer out of view. Add `min-width: 0` to the inner input row: the Esc hint
  previously caused ten pixels of horizontal scrolling while typing.
- Keep long agent placeholders on one line without changing multiline draft
  wrapping, avoiding a partially clipped second placeholder line on narrow inputs.

Verification on Windows and the physical phone, 2026-10-21:

- Four new autocomplete reproductions failed against the original code. The two
  delayed-usage tests also failed before their fix.
- Final focused frontend run: 20 files, 273 tests passed.
- Backend spacing, SDK cleanup, constructor errors, model-text and Pi driver tests:
  35 passed. Constructor failure preserves its original exception because it
  precedes the cleanup block; no unbound-client cleanup occurs.
- Review regressions also prove that cancelling a rewrite immediately resets its
  busy state through the scope/draft effect. Stale request finalizers remain
  guarded so they cannot clear a newer rewrite's loading state.
- TypeScript and production build passed.
- Desktop Chromium layout suite: 22 passed, covering five composer widths and
  previous message-action/navbar regressions.
- The new opt-in physical-browser suite passed on a Samsung SM-G970F running
  Android 12 / Chrome 155. It exercised compact and expanded usage, typed a
  multiline draft, observed the real soft keyboard and restored the original
  draft. Page and conversation horizontal overflow were zero in all three states.
- At the phone's configured display density the viewport was 320 × 537 CSS pixels,
  shrinking to about 320 × 270 with the keyboard. Input and Send stayed visible.

An initial execution pause due to approval-review account limits was resolved
before these final checks. Full repository CI gates are required before merge.
See [physical-device checks](physical-device-ui.md) for the repeatable suite and
the Chromebook limitation; desktop emulation is not counted as a device pass.
