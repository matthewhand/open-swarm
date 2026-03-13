import pytest
from unittest.mock import MagicMock, patch
from swarm.services.github_client import GitHubConfig, GitHubClient

def test_github_config_defaults():
    config = GitHubConfig()
    assert config.base_url == "https://api.github.com"
    assert config.timeout == 30
    assert config.user_agent == "Swarm-GitHub-Client"

def test_github_client_init():
    config = GitHubConfig(base_url="https://custom.api.com/", timeout=10)
    client = GitHubClient(config)
    assert client.base_url == "https://custom.api.com"
    assert client.config.timeout == 10

@patch("swarm.services.github_client.httpx.Client")
def test_search_repositories(mock_httpx_client):
    mock_instance = MagicMock()
    mock_instance.get.return_value.status_code = 200
    mock_instance.get.return_value.json.return_value = {
        "items": [
            {"full_name": "owner/repo", "html_url": "url", "description": "desc", "stargazers_count": 10, "updated_at": "now", "topics": []}
        ]
    }
    mock_httpx_client.return_value.__enter__.return_value = mock_instance

    client = GitHubClient()
    results = client.search_repositories(topics=["test"])

    assert len(results) == 1
    assert results[0]["full_name"] == "owner/repo"
    mock_instance.get.assert_called_once()
    args, kwargs = mock_instance.get.call_args
    assert "q" in kwargs["params"]
    assert "topic:test" in kwargs["params"]["q"]
