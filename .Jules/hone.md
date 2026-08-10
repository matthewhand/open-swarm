## 2025-05-18 | [Architectural Audit] | Insight: Missing Architectural Consistency for DaisyUI Loading Spinners | Protocol: All loaders and skeletons must use explicit ARIA states, typically `role="status"` and `aria-live="polite"` if conveying new info, while buttons with loaders must set `aria-busy="true"`

## 2025-05-18 | [Architectural Audit] | Insight: Modal dialog markup does not trap focus appropriately if it is purely custom. Our existing Modal uses HTML5 `<dialog>` and `focus-trap-react` which is good, but `aria-labelledby` usage should be stricter.

## 2025-05-18 | [Architectural Audit] | Insight: Pagination lacks proper generic types for custom async hooks (`useInfiniteScroll`) to manage deterministically the `error` and `isEmpty` states.
