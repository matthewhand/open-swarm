## 2024-07-10 | [Architectural Audit] | Insight: Modal backdrop uses unfocusable `<form>` | Protocol: Changed `<form method="dialog">` to `<button type="button">` to ensure 100% keyboard operability, properly handling a11y focus when closing modals.

## 2024-07-10 | [Architectural Audit] | Insight: Implicit Loading and Empty states missing deterministic announcements | Protocol: Explicitly mapped async states (`isPending`, `isError`, empty) to `role="status"`, `role="alert"`, and explicit `aria-live` / `aria-busy` tags across major views (Dashboard, Teams, Blueprints) to maintain screen reader state consistency.

## 2024-07-10 | [Architectural Audit] | Insight: Relaxed type safety mapping APIs as `any` | Protocol: Replaced all `any` usages with `unknown` mapped types and proper type guards (e.g. `typeof team.id === "string"` and `e instanceof Error`) ensuring strict typescript safety in core data views.
