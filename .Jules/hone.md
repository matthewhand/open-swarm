## 2024-06-15 | [Architectural Audit] | Insight: Missing focus traps in modals | Protocol: Wrap modal contents with `focus-trap-react` and manage native dialog open states deterministically.
## 2024-06-15 | [Architectural Audit] | Insight: Silent async states | Protocol: Apply `aria-live="polite"`, `aria-busy="true"`, and `role="status"` on Loading, Error, and Empty states of network-dependent components.
## 2024-06-15 | [Architectural Audit] | Insight: Anonymous default exports | Protocol: Assign objects to a named variable before `export default` to adhere to modern ESLint rules and maintain strict type-safety standards.
## 2024-06-15 | [Architectural Audit] | Insight: Missing focus restoration for dialog | Protocol: Restore focus to previous active element on modal close.
## 2024-06-15 | [Architectural Audit] | Insight: Unstable deps in useMemo | Protocol: Move dependencies directly into useMemo to ensure stable rendering.
## 2024-06-15 | [Architectural Audit] | Insight: DOM-reliant accessibility tests | Protocol: Remove use of querySelector in favor of screen queries, matching by accessible roles or text, and verify strict structure by ARIA attributes.
