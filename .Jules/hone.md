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

## 2024-06-13 | [Architectural Audit] | Insight: Inaccessible Accordion/Tabs Pattern | Protocol: ID Linkage and ARIA State Projection
- **Pattern:** `AccordionItem` within DaisyUI Tabs wrapper components relied on raw `input[type="checkbox"]` elements without proper ARIA structural properties linking the control logic to the content body for screen readers.
- **Protocol:** Added dynamic ID linkage. Specifically, bound `aria-controls` to the content regions (`id={panelId}`) and `aria-expanded` to track component state dynamically based on user interaction or the array state map. Set `role="region"` onto content nodes and pointed `aria-labelledby` back to the controls. Added keyboard support references.

## 2024-06-13 | [Architectural Audit] | Insight: Sub-optimal Loading Component Accessibility | Protocol: Strict Polite Live Regions
- **Pattern:** `LoadingSpinner` and its siblings correctly provided a visual proxy for long-running processes but left screen readers muted, causing asynchronous state dissonance for visually impaired users.
- **Protocol:** Applied `aria-live="polite"` and `aria-busy="true"` attributes to all dynamic loading indicators, enabling screen readers to silently buffer the announcement and play it to the end user after any current system utterances.

## 2024-06-13 | [Architectural Audit] | Insight: Generic Infinite Pagination | Protocol: Strict Parameterized Generics for TS Engine
- **Pattern:** The pagination hook `useInfiniteScroll` relied on `any[]` and failed to capture object types across usage, polluting inference engine checks.
- **Protocol:** Enforced strict parameterization via generic signature bindings `<T>`.
