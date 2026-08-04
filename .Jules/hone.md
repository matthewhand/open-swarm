## 2024-05-20 | [Architectural Audit] | Insight: Native confirm() modal bypasses A11y and UX context | Protocol: Replace with declarative DaisyUI ConfirmModal
The `TeamsPage` implements destructive actions using `window.confirm()`. This native dialog cannot be styled, disrupts the application's focus management, and provides no semantic context for screen readers. Protocol is to strictly use custom `ConfirmModal` components with defined `focus-trap` and `aria-labelledby` semantics.

## 2024-05-20 | [Architectural Audit] | Insight: Conditional FocusTrap breaks DaisyUI modal transitions | Protocol: Utilize active prop for FocusTrap
The `Modal` component conditionally wraps the dialog in a `FocusTrap` when open. This abrupt structural change prevents CSS transitions from completing on close. Protocol requires rendering `FocusTrap` permanently and toggling its `active` prop to harmonize DOM state with DaisyUI CSS animations.

## 2024-05-20 | [Architectural Audit] | Insight: Unsemantic DOM assertions in test suite | Protocol: Enforce RTL queries and explicit roles
Test files like `Button.test.tsx` rely heavily on `container.querySelector` to assert loading states, bypassing semantic roles. This pattern hides accessibility regressions. Protocol mandates the use of semantic HTML (`role="status"` for spinners) paired with Testing Library's `screen.getByRole` to guarantee structural and a11y integrity simultaneously.
