# MCP Server Mode (`ENABLE_MCP_SERVER`)

**Status: aspirational.** Setting `ENABLE_MCP_SERVER=true` does not currently expose a
working MCP endpoint on any standard install. Worse, it breaks startup outright:
`swarm/settings.py` appends `'django_mcp_server'` to `INSTALLED_APPS` when the flag is
set, and since no package provides that module, `django.setup()` raises
`ModuleNotFoundError` before any URL is served. (The `try/except` around the append is
ineffective — appending a string never raises; the failure happens later in
`apps.populate()`.)

Independently, `src/swarm/urls.py` tries to mount
`path('mcp/', include('django_mcp_server.urls'))` when the flag is set; that import
also fails, and the mount is skipped with a logged warning naming the missing package
(previously this failed silently).

## Why no dependency is declared

The closest PyPI distribution, [`django-mcp-server`](https://pypi.org/project/django-mcp-server/)
(v0.5.7 as of Oct 2025, actively maintained, Python >= 3.10, Django 4/5), installs the
module **`mcp_server`** — not `django_mcp_server` — and requires adding `'mcp_server'`
to `INSTALLED_APPS` plus `path('', include('mcp_server.urls'))`. Pinning it without
those settings changes would still leave the flag dead, so it is intentionally not
declared yet.

## Real options for serving MCP from this project

1. Adopt `django-mcp-server`: add it as an optional extra, register `'mcp_server'`
   (not `'django_mcp_server'`) in `INSTALLED_APPS`, and switch the include in
   `swarm/urls.py` to `mcp_server.urls`.
2. Mount the official MCP Python SDK (`mcp` on PyPI) as an ASGI sub-application
   (e.g. Streamable HTTP transport) alongside Django.
3. Leave the flag aspirational (current state) — the warning makes that explicit.

`tests/mcp/test_mcp_urls.py` exercises the mount by stubbing `django_mcp_server` in
`sys.modules`; `tests/mcp/test_mcp_missing_package_warning.py` guards the warning path.
