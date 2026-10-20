# Compact usage default (#958)

The API composer starts with a slim token count and an icon-only chevron.
No labels, cards or breakdown appear until the user explicitly expands it.
The button retains its accessible name, tooltip, expanded state and Escape
focus restoration. Unknown usage shows just the disclosure icon.

Verified on Windows: production build, TypeScript, 130 focused unit tests and
five Chromium viewport cases (320–1280px). Browser assertions check that details
start absent, the expand button has no visible text, and the compact strip is
at most 28px tall. Expansion, sending and keyboard behavior remain covered.
Visually reviewed the default inventory-demo conversation at 401 × 605px.
Full repository CI gates must pass before merge.
