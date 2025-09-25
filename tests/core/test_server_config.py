import json
import os
from unittest.mock import patch, mock_open
import pytest

from swarm.core.server_config import save_server_config, load_server_config


def test_save_server_config_success():
    config = {"key": "value", "nested": {"subkey": "subvalue"}}
    file_path = "/test/config.json"
    
    with patch("builtins.open", mock_open()) as mock_file:
        save_server_config(config, file_path)
        
        mock_file.assert_called_once_with(file_path, "w")
        handle = mock_file()
        handle.write.assert_called_once_with(json.dumps(config, indent=4))


def test_save_server_config_default_path():
    config = {"key": "value"}
    
    with patch("os.getcwd", return_value="/current/dir"), \
         patch("builtins.open", mock_open()) as mock_file:
        save_server_config(config)
        
        expected_path = "/current/dir/swarm_settings.json"
        mock_file.assert_called_once_with(expected_path, "w")


def test_save_server_config_invalid_input():
    with pytest.raises(ValueError, match="Configuration must be a dictionary."):
        save_server_config("not a dict")


@patch("builtins.open")
def test_save_server_config_os_error(mock_open_func):
    config = {"key": "value"}
    file_path = "/test/config.json"
    
    mock_open_func.side_effect = OSError("Permission denied")
    
    with pytest.raises(OSError):
        save_server_config(config, file_path)


def test_load_server_config_success():
    config = {"key": "value", "nested": {"subkey": "subvalue"}}
    file_path = "/test/config.json"
    
    with patch("builtins.open", mock_open(read_data=json.dumps(config))) as mock_file:
        result = load_server_config(file_path)
        
        mock_file.assert_called_once_with(file_path)
        assert result == config


def test_load_server_config_default_path():
    config = {"key": "value"}
    
    with patch("os.getcwd", return_value="/current/dir"), \
         patch("builtins.open", mock_open(read_data=json.dumps(config))) as mock_file:
        result = load_server_config()
        
        expected_path = "/current/dir/swarm_settings.json"
        mock_file.assert_called_once_with(expected_path)
        assert result == config


def test_load_server_config_not_found():
    file_path = "/nonexistent/config.json"
    
    with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
        with pytest.raises(FileNotFoundError):
            load_server_config(file_path)


def test_load_server_config_invalid_json():
    file_path = "/test/config.json"
    
    with patch("builtins.open", mock_open(read_data="{invalid json")):
        with pytest.raises(ValueError, match="Invalid JSON in configuration file:"):
            load_server_config(file_path)


def test_load_server_config_not_dict():
    file_path = "/test/config.json"
    
    with patch("builtins.open", mock_open(read_data=json.dumps("not a dict"))):
        with pytest.raises(ValueError, match="Configuration must be a dictionary."):
            load_server_config(file_path)