# REQ-6

Intent: the Agent Router sidebar has too many agents. Operators need Hide all, then a short typed roster.

Success:
1. Hide all control on Agent Router, Django chrome sidepane, and SPA Chat sidepane.
2. Agent Router Hide all keeps Support (highlighted, default) plus three typed starters: CLI (grok/agy), API, Remote (framework dropdown).
3. Type-specific header dropdowns: CLI grok vs agy (+ CLI model), API blueprint, remote framework + member.
4. Persist hidden ids. Unhide all restores the catalog.

Constraints: Do not remove catalog agents from the API; hide is UI state. First visit may auto-hide except starters.

Owner: open-swarm engineer.
