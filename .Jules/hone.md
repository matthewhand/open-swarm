## 2025-07-16 | [Architectural Audit] | Insight: Blocking Native Dialogs Limit State Fluidity | Protocol: Replaced synchronous `confirm()` blocking functions with the accessible `ConfirmModal` component on data tables to preserve React state loops and enable consistent UI/UX workflows without halting the main thread.

## 2025-07-16 | [Architectural Audit] | Insight: CSS State vs ARIA Lifecycle Desync | Protocol: DaisyUI's `<dialog>` based modals lose exit-animations when completely unmounted. Use `active={isOpen}` within `FocusTrap` wrapper combined with controlled CSS classes (`modal-open`) to synchronize CSS transitions with proper ARIA accessibility states.

## 2025-07-16 | [Architectural Audit] | Insight: Brittle Fallbacks in Async Component Workflows | Protocol: Replaced informal text indicators (like `...`) with deterministic, semantic components (`<LoadingSpinner />`) equipped with `role="status"` and `aria-live="polite"` to guarantee deterministic state conveyance and screen reader notification.

## 2025-07-16 | [Architectural Audit] | Insight: Testing Rigidity via DOM Queries | Protocol: Systemic ESLint rule violations resulting from container usage (`querySelector`) in test utilities. Established convention of semantic queries (`getByRole`) and enforced localized `eslint-disable-next-line` overrides exclusively for necessary structural testing.
