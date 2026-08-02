## 2024-05-23 | [Architectural Audit] | Insight: Pagination state is missing from SR announcements | Protocol: Always explicitly add `aria-current="page"` to the active page button in pagination components.

## 2024-05-23 | [Architectural Audit] | Insight: Missing focus traps in user confirmation | Protocol: Use `<ConfirmModal>` for user confirmations instead of native `window.confirm()` to ensure focus trapping and HTML5 modal semantics.

## 2024-05-23 | [Architectural Audit] | Insight: Missing deterministic async states | Protocol: Ensure all async views have an explicit empty state component, and use `aria-live="polite"` and `aria-busy="true"` for loading components, and `role="alert"` for errors.

## 2024-05-23 | [Architectural Audit] | Insight: Lax type checking and use of 'any' | Protocol: Do not use `any`. Use strict TypeScript types or generics, and `unknown` in catch blocks combined with `e instanceof Error` for safety.
