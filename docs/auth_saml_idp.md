SAML IdP Integration (djangosaml2idp)
=====================================

Goal
----
Provide a Django‑managed SAML 2.0 Identity Provider at `/idp/` for the Open Swarm web UI, using `djangosaml2idp`. The IdP is optional and disabled by default.

Enable
------
1) Install the package in your environment (not required for default tests):

   pip install djangosaml2idp

2) Enable the feature flag and run migrations:

```
export ENABLE_SAML_IDP=true
uv run python manage.py migrate
uv run python manage.py runserver
```

3) Endpoints (served under the same host):
   - IdP base: `/idp/`
   - Typical metadata: `/idp/metadata/`

Configuration
-------------
- Settings flag: `ENABLE_SAML_IDP=true` enables IdP and adds `djangosaml2idp` to `INSTALLED_APPS`.
- Template config: `SAML_IDP_SPCONFIG` is defined in settings as a mapping keyed by SP entity IDs. Provide real SP entries via environment or a secure settings module.
- Example (in Django settings or via environment expansion):

```python
SAML_IDP_SPCONFIG = {
  "https://sp.example.com/metadata": {
    "acs_url": "https://sp.example.com/saml/acs",
    "audiences": ["https://sp.example.com"],
    "nameid_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
  }
}
```

Environment-driven IdP base config (template-only)
-------------------------------------------------

These optional environment variables populate template settings for djangosaml2idp.

- `SAML_IDP_ENTITY_ID` — IdP entityID (defaults to `$HOST/idp/metadata/`)
- `SAML_IDP_CERT_FILE` — path to public certificate PEM (do not commit)
- `SAML_IDP_PRIVATE_KEY_FILE` — path to private key PEM (do not commit)

In `settings.py`, these are exposed under `SAML_IDP_CONFIG` as:

```python
SAML_IDP_CONFIG = {
  'entityid': SAML_IDP_ENTITY_ID,
  'cert_file': SAML_IDP_CERT_FILE,
  'key_file': SAML_IDP_PRIVATE_KEY_FILE,
}
```

Security & Secrets
------------------
- Do not store private keys or secrets in the repository. Provision certificates/keys securely.
- This integration only scaffolds the IdP; production deployments must configure HTTPS, certificates, signing/encryption keys, and SP metadata appropriately.

SP config via environment
-------------------------
- You can inject Service Provider entries via `SAML_IDP_SPCONFIG_JSON` (a JSON object keyed by SP entity IDs):

```
export SAML_IDP_SPCONFIG_JSON='
{
  "https://sp.example.com/metadata": {
    "acs_url": "https://sp.example.com/saml/acs",
    "audiences": ["https://sp.example.com"],
    "nameid_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
  }
}
'
```

- The loader validates minimal structure (`acs_url` required; `audiences` coerced to list when present). Invalid items are dropped silently.

SP config via file
------------------
- Alternatively, point to a JSON file using `SAML_IDP_SPCONFIG_FILE`:

```
export SAML_IDP_SPCONFIG_FILE=/secure/path/spconfig.json
```

- The same validation rules apply as with the JSON env variable.

Local Development Tips
----------------------
- If you need quick self‑signed certs for testing:

```
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
```

Add the appropriate `djangosaml2idp` settings to point to these files for local dev only. Never commit keys.
