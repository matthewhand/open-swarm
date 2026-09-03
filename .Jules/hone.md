## 2026-08-31 | [Architectural Audit] | Insight: Modal Background Buttons (Anti-Pattern) | Protocol: Revert to standard HTML5 `<form method="dialog">` backdrop wrapper to preserve native browser event delegation (Escape key handling, outside click processing) strictly according to DaisyUI architecture, removing React re-render hacking via raw `.modal-backdrop` buttons.

## 2026-08-31 | [Architectural Audit] | Insight: Silent Async Loading Components | Protocol: Enforce explicit structural ARIA loading guarantees. Decorative indicator spans (e.g. `LoadingDots`, `LoadingRing`, etc) must uniformly output `role="status"`, `aria-live="polite"`, and `aria-busy="true"` to enforce non-visual screen reader notification of async transitions.

## 2026-08-31 | [Architectural Audit] | Insight: Type-Unsafe Promise Catching in Pagination hooks | Protocol: Implement strict `err: unknown` type guards with `err instanceof Error` object validation to ensure deterministic rendering of error strings in async data-fetching custom hooks (e.g., `useInfiniteScroll`). This guarantees UI state machine integrity by ensuring error views always resolve to standard string signatures.

## 2024-05-23 | [Architectural Audit] | Insight: Missing deterministic async states | Protocol: Ensure all async views have an explicit empty state component, and use `aria-live="polite"` and `aria-busy="true"` for loading components, and `role="alert"` for errors.

## 2024-05-23 | [Architectural Audit] | Insight: Lax type checking and use of 'any' | Protocol: Do not use `any`. Use strict TypeScript types or generics, and `unknown` in catch blocks combined with `e instanceof Error` for safety.

## 2024-05-18 | [Architectural Audit] | Insight: Modal component uses inaccessible <form method="dialog"> for backdrop, lacks rigorous focus management, and relies on brittle `document.getElementById` navigation in Tabs. Pagination is missing `aria-current="page"` and `aria-live` is misused or missing on loading states. | Protocol: Refactor Modal backdrop to a proper focusable button with `tabIndex={-1}`, ensure robust state handling across components and use explicit accessibility patterns

## 2024-05-18 | [Architectural Audit] | Insight: Codebase uses `any` types when parsing API responses in `TeamsPage.tsx` and `BlueprintsPage.tsx`. | Protocol: Replace `any` with `unknown` and strict type guards to ensure TypeScript integrity during async data extraction.

## 2026-08-26 | [Architectural Audit] | Insight: ConfirmModal treated onConfirm as fire-and-forget, so async deletes could double-submit with no error surface. Accordion used a checkbox+div collapse instead of native disclosure. | Protocol: ConfirmModal must accept `() => void | Promise<void>`, guard with `aria-busy`, and report failures via `Alert` `role="alert"` using `unknown` + `instanceof Error`. Keep the modal backdrop as a `tabIndex={-1}` button (do not wrap it in `<form method="dialog">`). Accordion items use `<details>`/`<summary>`; preventDefault on summary click so React `open` stays the source of truth.

## 2026-08-29 | [Architectural Audit] | Insight: Modal backdrop anti-pattern and testing library DOM access violations | Protocol: Enforce <form method="dialog"> for modal backdrops and ban direct DOM selectors (querySelector) in UI tests.
