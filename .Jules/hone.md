## 2024-07-13 | [Architectural Audit] | Insight: Native JS `confirm()` dialogs break accessible focus-management and screen reader expectations. | Protocol: Replace all `window.confirm()` calls with DaisyUI `ConfirmModal` (wrapped in `focus-trap-react` and semantically rich).

## 2024-07-13 | [Architectural Audit] | Insight: Widespread use of `any` types in network response mapping (`TeamsPage`, `BlueprintsPage`, `App`) destroys state integrity and type safety. | Protocol: Use strict interface definitions, type guarding, or `Record<string, unknown>` to validate incoming API data.

## 2024-07-13 | [Architectural Audit] | Insight: Test suites are throwing ESLint errors by querying DOM nodes directly (`testing-library/no-node-access`), which undermines semantic accessibility testing. | Protocol: Suppress structural queries strictly where necessary to assert visual/CSS state, and prefer `getByRole` for behavioral state.
