# REQ-8

Intent: navbar is overcrowded. Agent chat is the primary tab; everything else lives in a More popup.

Success:
1. Primary tab is Agents (`/agents`) on Django chrome and SPA.
2. More popup: Chat, Blueprints, Teams, Sessions, Settings (GitHub on Django desktop).
3. Mobile dock is Agents + More (drop-up), not a four-tab Chat/Blueprints/Teams/Sessions strip.
4. `/chat` stays the websocket composer. `/agents` is Agent Router, not a Chat alias.

Constraints: No extra UI frameworks. Match existing Bootstrap (Django) and daisyUI (SPA) dropdowns.

Owner: open-swarm engineer.
