## 2025-06-12 | Architectural Audit | Insight: Uncontrolled UI Unmounts via Component Wrapping | Protocol: Stable Root Rendering

**The Discovery:**
DaisyUI's modal elements were subject to a severe state-loss regression due to React conditional unmounting. Specifically, the `<FocusTrap>` component was conditionally wrapping the native `<dialog>` element depending on `isOpen`. In React, changing the type of the root node from `dialog` to `FocusTrap` forces a complete destruction and recreation of the underlying DOM tree. This means:
1. All CSS transitions (DaisyUI's smooth opacities/visibilities) are bypassed as the elements snap into existence.
2. Form state internal to the modal is completely wiped on closure, directly harming form workflows.

**The Prevention Strategy:**
To ensure high-fidelity interactions, wrapping components like `<FocusTrap>` must always be rendered. Use their internal state management (`active={isOpen}`) to toggle behavior without forcing React reconciliation to destroy the underlying DOM nodes. This maintains continuous reference stability and preserves accessible state sequences.

## 2025-06-12 | Architectural Audit | Insight: Silent Async Form Submissions | Protocol: Defensive Interaction Broadcasting

**The Discovery:**
The primary interaction form (`ChatPage.tsx`) managed async generation exclusively through visual loading spinners. For screen readers, submission triggered no distinct semantic events. While visually obvious, standard assistive technology assumes a synchronous interaction model unless explicitly informed otherwise. A silent UI during an extended async operation equates to a broken application state for these users.

**The Prevention Strategy:**
Implementing deterministic A11y broadcasting on the `Button` components using `aria-busy` and `aria-disabled` bound to the streaming state, and ensuring the connection badge sits within an `aria-live="polite"` and `role="status"` region. This translates the async execution flow securely across the accessibility tree without overwhelming the user with duplicate announcements.

## 2025-06-12 | Architectural Audit | Insight: Brittle Empty States in Admin Dashboards | Protocol: Explicit Accessibility Boundaries

**The Discovery:**
The `AgentCreatorPage` effectively fetched and mapped custom blueprints but fell back to non-semantic, poorly styled empty states (div-soup) or naked error logs when data failed to load or when no data existed. These fragments lack structural identity, making navigation ambiguous when filtering or loading dashboard lists.

**The Prevention Strategy:**
Mandate the use of structured `Alert` components or explicit status blocks (with `aria-live="polite"`) that provide semantic wrappers around complex async outcomes (e.g., `isPending`, `isError`, empty array conditions). This isolates the visual state cleanly while ensuring screen readers receive a cohesive announcement.