## 2024-05-23 | [Architectural Audit] | Insight: Pagination state is missing from SR announcements | Protocol: Always explicitly add `aria-current="page"` to the active page button in pagination components.

## 2024-05-23 | [Architectural Audit] | Insight: Missing focus traps in user confirmation | Protocol: Use `<ConfirmModal>` for user confirmations instead of native `window.confirm()` to ensure focus trapping and HTML5 modal semantics.

## 2024-05-23 | [Architectural Audit] | Insight: Missing deterministic async states | Protocol: Ensure all async views have an explicit empty state component, and use `aria-live="polite"` and `aria-busy="true"` for loading components, and `role="alert"` for errors.

## 2024-05-23 | [Architectural Audit] | Insight: Lax type checking and use of 'any' | Protocol: Do not use `any`. Use strict TypeScript types or generics, and `unknown` in catch blocks combined with `e instanceof Error` for safety.

## 2024-05-18 | [Architectural Audit] | Insight: Modal component uses inaccessible <form method="dialog"> for backdrop, lacks rigorous focus management, and relies on brittle `document.getElementById` navigation in Tabs. Pagination is missing `aria-current="page"` and `aria-live` is misused or missing on loading states. | Protocol: Refactor Modal backdrop to a proper focusable button with `tabIndex={-1}`, ensure robust state handling across components and use explicit accessibility patterns

## 2024-05-18 | [Architectural Audit] | Insight: Codebase uses `any` types when parsing API responses in `TeamsPage.tsx` and `BlueprintsPage.tsx`. | Protocol: Replace `any` with `unknown` and strict type guards to ensure TypeScript integrity during async data extraction.
## 2026-08-16 | [Architectural Audit] | Insight: Pagination accessibility needs structure | Protocol: Use semantic `<nav>` wrapper and `aria-current` properly
## 2026-08-16 | [Architectural Audit] | Insight: TypeScript warnings on unused variables and redeclarations | Protocol: Clean up unused imports and duplicate declarations
## 2026-08-16 | [Architectural Audit] | Insight: DaisyUI Modals should use <form method="dialog"> for the backdrop, not a <button> | Protocol: Retain native <form method="dialog"> for the backdrop to allow the browser to natively handle modal closing semantics
