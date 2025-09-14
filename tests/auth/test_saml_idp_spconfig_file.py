import importlib
import json


def test_spconfig_file_loader(monkeypatch, tmp_path):
    monkeypatch.setenv('ENABLE_SAML_IDP', 'true')
    payload = {
        "https://sp3.example.com/metadata": {
            "acs_url": "https://sp3.example.com/acs",
            "audiences": ["https://sp3.example.com"]
        },
        # invalid entry should be dropped
        "https://invalid.example.com/metadata": {}
    }
    path = tmp_path / 'spconfig.json'
    path.write_text(json.dumps(payload), encoding='utf-8')
    monkeypatch.setenv('SAML_IDP_SPCONFIG_FILE', str(path))

    settings_mod = importlib.import_module('swarm.settings')
    importlib.reload(settings_mod)

    cfg = settings_mod.SAML_IDP_SPCONFIG
    assert "https://sp3.example.com/metadata" in cfg
    assert "https://invalid.example.com/metadata" not in cfg

