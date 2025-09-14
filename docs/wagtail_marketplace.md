Wagtail Marketplace (Blueprints + MCP Config Templates)
=======================================================

Goal
----
Provide a Wagtail-powered, optional web UI to browse and share example agent blueprints and MCP configuration templates (template-only, never secrets).

Enable
------
1) Install deps (already listed in pyproject): wagtail, taggit, modelcluster.
2) Export env var and run migrations:

```
export ENABLE_WAGTAIL=true
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

3) Visit `/cms/admin/` to add:
   - A `MarketplaceIndexPage` as the home page under the default Wagtail Site.
   - `BlueprintPage` and `MCPConfigPage` beneath the index.

Models
------
- `BlueprintCategory` (snippet)
- `MarketplaceIndexPage`
- `BlueprintPage` fields:
  - summary, version, category, tags (comma-separated), repository_url
  - manifest_json, code_template (validated for secrets)
- `MCPConfigPage` fields:
  - summary, version, server_name, config_template (validated for secrets)

Secret Redaction
----------------
Basic validation rejects content containing likely secrets (patterns for `sk-`, `api_key`, `secret`, `password`, `token`). Extend as needed.

API / Headless
--------------
This initial drop focuses on the editorial UI and basic site rendering. If you want a headless JSON API:
- Enable Wagtail API v2 and register endpoints, or
- Add a small DRF view to serialize `BlueprintPage`/`MCPConfigPage` data for clients.

Notes
-----
- Wagtail is optional; the project only activates it when `ENABLE_WAGTAIL=true`.
- No credentials should be stored in `manifest_json`, `code_template`, or `config_template`.

