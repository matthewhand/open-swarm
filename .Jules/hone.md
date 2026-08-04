## 2023-10-27 | [Architectural Audit] | Insight: Component test files (Button.test.tsx) are using generic Testing Library `container.querySelector` DOM traversals rather than semantic queries, violating `testing-library/no-container` and `testing-library/no-node-access`. | Protocol: Replace `container.querySelector` with semantically meaningful queries (e.g. `getByRole`, `getByTestId` with explicit roles/data-testids or disable eslint correctly for testing structure).

## 2023-10-27 | [Architectural Audit] | Insight: In frontend codebase there is an issue with `import/first` in `inferenceProfile.test.ts` | Protocol: Ensure all imports are at the top of test files.

## 2023-10-27 | [Architectural Audit] | Insight: Native `confirm()` modal is used in `TeamsPage.tsx`, violating `no-restricted-globals` and causing A11y & state management issues. | Protocol: Refactor native `confirm()` with a managed accessible `ConfirmModal` component from `components/DaisyUI`.

## 2023-10-27 | [Architectural Audit] | Insight: Empty `eslint.config.js` not found when running lint, while package has `.eslintrc` but uses eslint v8. The lint command actually ran fine, but we have strict warnings/errors to fix. | Protocol: Address ESLint errors reported during `npm run lint`.
