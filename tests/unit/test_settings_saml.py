import importlib
import json
import sys
import os
from unittest.mock import patch, mock_open, MagicMock
import contextlib

# Ensure 'src' is in sys.path for standalone execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

@contextlib.contextmanager
def mock_dependencies():
    """Context manager to mock missing dependencies safely."""
    # Only mock if they aren't already there to avoid interfering with real environments
    to_mock = ['dotenv', 'rest_framework', 'rest_framework.authtoken', 'drf_spectacular']
    patched_modules = {}

    for mod_name in to_mock:
        if mod_name not in sys.modules:
            patched_modules[mod_name] = MagicMock()

    with patch.dict(sys.modules, patched_modules):
        yield

def test_saml_spconfig_json_malformed():
    """Test that malformed JSON in SAML_IDP_SPCONFIG_JSON doesn't crash settings."""
    with mock_dependencies():
        import swarm.settings
        import swarm.utils.env_utils
        with patch('swarm.utils.env_utils.get_saml_idp_spconfig_json', return_value='{invalid json}'):
            with patch('swarm.utils.env_utils.get_saml_idp_spconfig_file', return_value=None):
                # Should not raise Exception
                importlib.reload(swarm.settings)
                assert isinstance(swarm.settings.SAML_IDP_SPCONFIG, dict)

def test_saml_spconfig_json_not_dict():
    """Test that SAML_IDP_SPCONFIG_JSON containing a list instead of a dict doesn't crash."""
    with mock_dependencies():
        import swarm.settings
        import swarm.utils.env_utils
        with patch('swarm.utils.env_utils.get_saml_idp_spconfig_json', return_value='["not", "a", "dict"]'):
            with patch('swarm.utils.env_utils.get_saml_idp_spconfig_file', return_value=None):
                importlib.reload(swarm.settings)
                assert isinstance(swarm.settings.SAML_IDP_SPCONFIG, dict)

def test_saml_spconfig_file_malformed():
    """Test that malformed JSON in SAML_IDP_SPCONFIG_FILE doesn't crash settings."""
    with mock_dependencies():
        import swarm.settings
        import swarm.utils.env_utils
        with patch('swarm.utils.env_utils.get_saml_idp_spconfig_json', return_value=None):
            with patch('swarm.utils.env_utils.get_saml_idp_spconfig_file', return_value='fake_config.json'):
                with patch('builtins.open', mock_open(read_data='{invalid json}')):
                    # Should not raise Exception
                    importlib.reload(swarm.settings)
                    assert isinstance(swarm.settings.SAML_IDP_SPCONFIG, dict)

def test_saml_spconfig_file_not_found():
    """Test that missing SAML_IDP_SPCONFIG_FILE doesn't crash settings."""
    with mock_dependencies():
        import swarm.settings
        import swarm.utils.env_utils
        with patch('swarm.utils.env_utils.get_saml_idp_spconfig_json', return_value=None):
            with patch('swarm.utils.env_utils.get_saml_idp_spconfig_file', return_value='nonexistent.json'):
                # Only the spconfig read should fail; settings.py legitimately
                # opens other files (.env) during import.
                real_open = open

                def selective_open(file, *args, **kwargs):
                    if 'nonexistent.json' in str(file):
                        raise FileNotFoundError(file)
                    return real_open(file, *args, **kwargs)

                with patch('builtins.open', side_effect=selective_open):
                    # Should not raise Exception
                    importlib.reload(swarm.settings)
                    assert isinstance(swarm.settings.SAML_IDP_SPCONFIG, dict)

def test_saml_spconfig_validation_and_conversion():
    """Test validation of SP config entries and conversion of audiences to list."""
    config = {
        'valid_sp': {
            'acs_url': 'https://sp.example.com/acs',
            'audiences': 'https://sp.example.com' # string should be converted to list
        },
        'invalid_sp_no_acs': {
            'foo': 'bar'
        },
        'invalid_sp_not_dict': 'not a dict'
    }

    with mock_dependencies():
        import swarm.settings
        import swarm.utils.env_utils
        with patch('swarm.utils.env_utils.get_saml_idp_spconfig_json', return_value=json.dumps(config)):
            with patch('swarm.utils.env_utils.get_saml_idp_spconfig_file', return_value=None):
                importlib.reload(swarm.settings)

                assert 'valid_sp' in swarm.settings.SAML_IDP_SPCONFIG
                assert isinstance(swarm.settings.SAML_IDP_SPCONFIG['valid_sp']['audiences'], list)
                assert swarm.settings.SAML_IDP_SPCONFIG['valid_sp']['audiences'] == ['https://sp.example.com']

                assert 'invalid_sp_no_acs' not in swarm.settings.SAML_IDP_SPCONFIG
                assert 'invalid_sp_not_dict' not in swarm.settings.SAML_IDP_SPCONFIG

if __name__ == "__main__":
    test_saml_spconfig_json_malformed()
    test_saml_spconfig_json_not_dict()
    test_saml_spconfig_file_malformed()
    test_saml_spconfig_file_not_found()
    test_saml_spconfig_validation_and_conversion()
    print("All SAML settings tests passed!")
