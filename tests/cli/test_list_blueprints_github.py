import pytest
import argparse
from unittest.mock import patch, MagicMock
from swarm.extensions.cli.commands import list_blueprints

def test_execute_list_blueprints_github():
    """Test execute function calls github discovery with correct args."""
    args = argparse.Namespace(
        github=True,
        repo="https://github.com/user/repo",
        min_stars=10,
        unrated=True,
        sort="updated",
        available=False
    )

    with patch("swarm.core.github_discovery.discover_remote_blueprints") as mock_discover:
        mock_discover.return_value = []
        list_blueprints.execute(args)

        mock_discover.assert_called_once_with(
            repo_url="https://github.com/user/repo",
            min_stars=10,
            include_unrated=True,
            sort_by="updated"
        )

def test_execute_list_blueprints_default_search():
    """Test execute function calls github discovery with defaults."""
    args = argparse.Namespace(
        github=True,
        available=False
    )
    # Default values from argparse
    args.repo = None
    args.min_stars = 3
    args.unrated = False
    args.sort = "stars"

    with patch("swarm.core.github_discovery.discover_remote_blueprints") as mock_discover:
        mock_discover.return_value = []
        list_blueprints.execute(args)

        mock_discover.assert_called_once_with(
            repo_url=None,
            min_stars=3,
            include_unrated=False,
            sort_by="stars"
        )
