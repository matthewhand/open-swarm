import pytest
from unittest.mock import patch, MagicMock
from swarm.core import github_discovery

@pytest.fixture
def mock_requests_get():
    with patch("requests.get") as mock_get:
        yield mock_get

def test_search_blueprint_repos_defaults(mock_requests_get):
    """Test searching with default parameters."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"items": [{"name": "repo1"}]}
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    results = github_discovery.search_blueprint_repos()

    assert len(results) == 1
    assert results[0]["name"] == "repo1"

    # Check default query
    args, kwargs = mock_requests_get.call_args
    assert "q" in kwargs["params"]
    assert "topic:open-swarm-blueprints" in kwargs["params"]["q"]
    assert "stars:>=3" in kwargs["params"]["q"] # Default min_stars
    assert kwargs["params"]["sort"] == "stars"

def test_search_blueprint_repos_custom(mock_requests_get):
    """Test searching with custom filters."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"items": []}
    mock_requests_get.return_value = mock_response

    github_discovery.search_blueprint_repos(limit=5, min_stars=10, sort_by="updated")

    args, kwargs = mock_requests_get.call_args
    params = kwargs["params"]
    assert params["per_page"] == 5
    assert "stars:>=10" in params["q"]
    assert params["sort"] == "updated"

def test_parse_github_url():
    """Test URL parsing logic."""
    assert github_discovery.parse_github_url("https://github.com/user/repo") == ("user", "repo")
    assert github_discovery.parse_github_url("github.com/user/repo.git") == ("user", "repo")
    assert github_discovery.parse_github_url("https://notgithub.com/user/repo") is None

@patch("swarm.core.github_discovery.search_blueprint_repos")
@patch("swarm.core.github_discovery.inspect_repo_content")
def test_discover_remote_blueprints(mock_inspect, mock_search):
    """Test the main discovery flow."""
    # Mock search returning one repo
    mock_search.return_value = [{
        "owner": {"login": "testuser"},
        "name": "testrepo",
        "description": "A test repo",
        "stargazers_count": 5,
        "html_url": "http://github.com/testuser/testrepo"
    }]

    # Mock inspection:
    # 1. 'blueprints' dir exists
    # 2. 'blueprints/mybp' dir exists
    # 3. 'blueprints/mybp' contains 'blueprint_mybp.py'

    def side_effect(owner, repo, path):
        if path == "blueprints":
            return [{"type": "dir", "name": "mybp", "path": "blueprints/mybp"}]
        if path == "blueprints/mybp":
            return [{"name": "blueprint_mybp.py"}]
        return []

    mock_inspect.side_effect = side_effect

    blueprints = github_discovery.discover_remote_blueprints()

    assert len(blueprints) == 1
    bp = blueprints[0]
    assert bp["name"] == "mybp"
    assert bp["path"] == "blueprints/mybp"
    assert bp["entry_point"] == "blueprint_mybp.py"
    assert bp["stars"] == 5

@patch("swarm.core.github_discovery.get_repo_metadata")
@patch("swarm.core.github_discovery.inspect_repo_content")
def test_discover_remote_blueprints_direct_url(mock_inspect, mock_meta):
    """Test discovery via direct URL."""
    mock_meta.return_value = {
        "owner": {"login": "direct"},
        "name": "repo",
        "description": "Direct",
        "stargazers_count": 100,
        "html_url": "..."
    }

    # Setup minimal content structure
    mock_inspect.side_effect = lambda o, r, p: [{"type": "dir", "name": "bp1", "path": "blueprints/bp1"}] if p == "blueprints" else [{"name": "main.py"}]

    bps = github_discovery.discover_remote_blueprints(repo_url="https://github.com/direct/repo")

    assert len(bps) == 1
    assert bps[0]["owner"] == "direct"
    mock_meta.assert_called_once()
