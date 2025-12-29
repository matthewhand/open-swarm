End‑to‑End Flow: Marketplace → Local Config → Secure MCP → Clients
================================================================

Goal
----
Let a user discover/import a blueprint from the marketplace, configure any
required MCP servers (no secrets in shared manifests), and expose a secure MCP
endpoint that external MCP clients can call using local identity (OAuth/SAML).

High‑Level Flow
---------------
1) Discover/import blueprint
   - From GitHub topics (open‑swarm‑blueprint/open‑swarm‑mcp‑template) or from
     the optional Wagtail editorials.
   - Import/instantiate the blueprint locally (JSON library or installed source).

2) Configure MCP servers (local only)
   - For desktop/local MCP servers (e.g., filesystem), minimal/no secrets.
   - For cloud MCP servers (e.g., third‑party APIs), store per‑user secrets in
     the local Django DB or env. Shared templates never include secrets; they
     use placeholders like ${API_KEY}.

3) Expose MCP endpoint
   - Use `ENABLE_MCP_SERVER` with `django-mcp-server` to expose `/mcp/` routes.
   - Register blueprint tools via `swarm.mcp.integration.register_blueprints_with_mcp()`
     so each blueprint appears as an MCP tool with a simple parameter schema.
   - Execution (MVP) returns acknowledgements; integrate Runner/BlueprintBase for
     real output next.

4) Secure access with local IdP
   - Identity provider options (local):
     - SAML (already scaffolded via `djangosaml2idp` under `/idp/`).
     - OAuth/OIDC (recommended for MCP clients) to be added (e.g., Django OAuth
       Toolkit or an OIDC provider).
   - Protect `/mcp/` endpoints with token‑based authorization (OAuth/OIDC). SAML
     can be used for SSO to obtain tokens, but MCP clients usually expect bearer
     tokens.

5) Clients consume MCP
   - Users configure their MCP client to point at the local `/mcp/` endpoint and
     present an access token.
   - The client invokes blueprint tools with arguments and receives results.

Security Model
--------------
- No secrets in shared repos; all sensitive values are provided locally.
- Per‑user secrets stored in Django DB or env; never exported.
- MCP endpoints require auth (token) and can enforce per‑user/per‑tool scopes.

Roadmap Notes
-------------
- Add OAuth/OIDC provider and protect `/mcp/` with token auth.
- Add per‑user MCP server settings UI and storage (encrypt at rest if desired).
- Integrate provider execution with Runner/BlueprintBase for at least one exemplar
  blueprint (e.g., Suggestion) and expand schemas over time.

