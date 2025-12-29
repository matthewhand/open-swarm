import importlib
import json


def test_spconfig_env_loader(monkeypatch):
    monkeypatch.setenv('ENABLE_SAML_IDP', 'true')
    payload = {
        "https://sp1.example.com/metadata": {
            "acs_url": "https://sp1.example.com/saml/acs",
            "audiences": ["https://sp1.example.com"]
        },
        # invalid (missing acs_url) → dropped
        "https://bad.example.com/metadata": {
            "audiences": "https://bad.example.com"
        },
        # coerce audiences to list
        "https://sp2.example.com/metadata": {
            "acs_url": "https://sp2.example.com/acs",
            "audiences": "https://sp2.example.com"
        }
    }
    monkeypatch.setenv('SAML_IDP_SPCONFIG_JSON', json.dumps(payload))

    settings_mod = importlib.import_module('swarm.settings')
    importlib.reload(settings_mod)

    cfg = settings_mod.SAML_IDP_SPCONFIG
    assert "https://sp1.example.com/metadata" in cfg
    assert cfg["https://sp1.example.com/metadata"]["acs_url"].endswith("/saml/acs")
    # bad entry removed
    assert "https://bad.example.com/metadata" not in cfg
    # sp2 audiences coerced to list
    assert isinstance(cfg["https://sp2.example.com/metadata"]["audiences"], list)

