import importlib


def test_env_driven_idp_settings(monkeypatch):
    monkeypatch.setenv('ENABLE_SAML_IDP', 'true')
    monkeypatch.setenv('SAML_IDP_ENTITY_ID', 'https://idp.example.com/metadata')
    monkeypatch.setenv('SAML_IDP_CERT_FILE', '/tmp/cert.pem')
    monkeypatch.setenv('SAML_IDP_PRIVATE_KEY_FILE', '/tmp/key.pem')

    settings_mod = importlib.import_module('swarm.settings')
    importlib.reload(settings_mod)

    assert settings_mod.ENABLE_SAML_IDP is True
    assert settings_mod.SAML_IDP_CONFIG['entityid'] == 'https://idp.example.com/metadata'
    assert settings_mod.SAML_IDP_CONFIG['cert_file'] == '/tmp/cert.pem'
    assert settings_mod.SAML_IDP_CONFIG['key_file'] == '/tmp/key.pem'

