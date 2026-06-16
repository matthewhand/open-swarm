## 2024-05-18 | [Architectural Audit] | Insight: Div-Soup Modals Lack Accessibility Mechanics | Protocol: HTML5 Dialog Refactor
- **Pattern:** Found `Modal.tsx` leveraging `<div className="modal">` and handling its own focus-trapping and escape-key handlers manually.
- **Protocol:** Upgraded the component architecture to use the native HTML5 `<dialog>` API. This guarantees focus trapping, places the overlay correctly in the Top Layer, and inherently handles keyboard cancellations.

## 2024-05-18 | [Architectural Audit] | Insight: Orphaned Labels in Forms | Protocol: Deterministic ID Linkage
- **Pattern:** `Input`, `Textarea`, and `Select` components inside DaisyUI wrappers were not connecting `<label>` to their corresponding form controls via `htmlFor`/`id`.
- **Protocol:** Implemented `useId()` from React inside these form components to generate guaranteed deterministic ID mappings. Added `aria-invalid` to actively project error states to screen readers.

## 2024-05-18 | [Architectural Audit] | Insight: Silent Asynchronous Transitions | Protocol: ARIA State Declarations
- **Pattern:** Buttons and loading spinners provided visual feedback for network operations, but screen readers were completely unaware.
- **Protocol:** Injected `role="status"` and `aria-label="Loading"` into loading spinners. Added `aria-disabled` and `aria-busy` to buttons while loading, along with a visually-hidden `<span className="sr-only">Loading</span>` to explicitly describe state changes to assistive tech.
## 2024-06-11 | [Architectural Audit] | Insight: Modal Component Accessibility | Protocol: Strict focus management and semantic roles

## 2024-06-11 | [Architectural Audit] | Insight: Missing Accessibility Attributes in Custom UI Components | Protocol: Introduce ARIA roles, robust focus management (focus-trap-react), and keyboard event handlers.

## 2024-06-11 | [Architectural Audit] | Insight: Type safety and `any` types | Protocol: Refactor `FormValidation.tsx` and `Pagination.tsx` to use robust generics instead of `any`, ensuring strict TypeScript integrity.

## 2024-06-11 | [Architectural Audit] | Insight: Missing Accessibility Attributes in Loading States | Protocol: Add `aria-live="polite"` and `aria-busy="true"` to Loading components (LoadingSpinner, LoadingDots, etc) and `aria-disabled="true"` to LoadingButton.
## 2026-06-16 | [Architectural Audit] | Insight: Modal lacks robust focus-trapping and correct ARIA structure for a11y. | Protocol: Refactor Modal.tsx to enforce focus trapping, aria-modal, and deterministic dialog roles.
## 2026-06-16 | [Architectural Audit] | Insight: Pagination hooks use 'any' types violating type-safety constraints. | Protocol: Refactor useInfiniteScroll in Pagination.tsx to use generics (T) instead of any.
## 2026-06-16 | [Architectural Audit] | Insight: Missing focus traps on Modal components which breaks keyboard accessibility. | Protocol: Integrate focus-trap-react into DaisyUI Modal component.
## 2026-06-16 | [Architectural Audit] | Insight: Modal focus traps required fallbackFocus logic for component rendering tests lacking native tabbable elements. | Protocol: Added robust focusTrapOptions to Modal.tsx.
## 2026-06-16 | [Architectural Audit] | Insight: Pagination useInfiniteScroll lacked formal error tests causing code review failure. | Protocol: Added robust unit tests verifying deterministic state-machine output in Pagination.test.tsx.
