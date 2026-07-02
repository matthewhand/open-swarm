## 2024-06-15 | [Architectural Audit] | Insight: Missing focus traps in modals | Protocol: Wrap modal contents with `focus-trap-react` and manage native dialog open states deterministically.
## 2024-06-15 | [Architectural Audit] | Insight: Silent async states | Protocol: Apply `aria-live="polite"`, `aria-busy="true"`, and `role="status"` on Loading, Error, and Empty states of network-dependent components.
## 2024-06-15 | [Architectural Audit] | Insight: Anonymous default exports | Protocol: Assign objects to a named variable before `export default` to adhere to modern ESLint rules and maintain strict type-safety standards.
## 2024-07-02 | [Architectural Audit] | Insight: Missing focus management and generic ARIA roles in custom components | Protocol: Enforce focus traps, deterministic ARIA states, and semantic HTML per Hone standards

## 2024-07-02 | [Architectural Audit] | Insight: Overloaded useMemo Dependencies | Protocol: Inline array instantiations `?? []` cause referential inequality, leading to exhaustive-deps and infinite re-renders. Always instantiate default arrays inside the useMemo callback.

## 2024-07-02 | [Architectural Audit] | Insight: Brittle Keyboard Focus | Protocol: `document.getElementById` bypasses the React Virtual DOM for focus management. Always use an array of Refs in custom Tab elements to manage keyboard accessibility safely.

## 2024-07-02 | [Architectural Audit] | Insight: Structural Test Query Anti-patterns | Protocol: Direct `container.querySelector` prevents semantic RTL guarantees. When asserting structurally inaccessible elements (like DaisyUI's loading span without `role="status"` on the button itself), explicitly use `// eslint-disable-next-line testing-library/no-node-access` rather than removing the rule globally.
