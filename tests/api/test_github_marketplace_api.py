import json
from unittest.mock import patch

import pytest


@pytest.mark.django_db
def test_github_blueprints_endpoint(monkeypatch, client):
    # Enable feature via django settings (not module-level import)
    with patch('swarm.views.api_views.ENABLE_GITHUB_MARKETPLACE', True):
        # Stub service functions
        from swarm.marketplace import github_service as gh
        captured = {}

        def fake_search(topics, orgs, *, sort, order, query, token):
            captured.update({'topics': topics, 'orgs': orgs, 'sort': sort, 'order': order, 'query': query})
            return [{
                'full_name': 'example/repo',
                'html_url': 'https://github.com/example/repo',
            }]

        def fake_fetch(repo, token=None):
            return [{
                'name': 'Demo BP', 'description': 'Demo', 'version': '1.0.0', 'tags': ['demo']
            }]

        monkeypatch.setattr(gh, 'search_repos_by_topics', fake_search)
        monkeypatch.setattr(gh, 'fetch_repo_manifests', fake_fetch)

        resp = client.get('/marketplace/github/blueprints/?search=demo&org=open-swarm&sort=updated&order=asc')
        assert resp.status_code == 200
        payload = json.loads(resp.content)
        assert payload['object'] == 'list'
        assert len(payload['data']) == 1
        item = payload['data'][0]
        assert item['kind'] == 'blueprint'
        assert item['repo_full_name'] == 'example/repo'
        # Verify params passed through
        assert captured['orgs'] == ['open-swarm']
        assert captured['sort'] == 'updated'
        assert captured['order'] == 'asc'
        assert captured['query'] == 'demo'


@pytest.mark.django_db
def test_github_mcp_configs_endpoint(monkeypatch, client):
    with patch('swarm.views.api_views.ENABLE_GITHUB_MARKETPLACE', True):
        from swarm.marketplace import github_service as gh

        def fake_search(topics, orgs, *, sort, order, query, token):
            return [{ 'full_name': 'example/repo', 'html_url': 'https://github.com/example/repo' }]

        def fake_fetch(repo, token=None):
            return [{ 'name': 'FS Config', 'description': 'Filesystem template', 'version': '0.1.0', 'tags': ['filesystem'] }]

        monkeypatch.setattr(gh, 'search_repos_by_topics', fake_search)
        monkeypatch.setattr(gh, 'fetch_repo_manifests', fake_fetch)

        resp = client.get('/marketplace/github/mcp-configs/?topic=open-swarm-mcp-template')
        assert resp.status_code == 200
        payload = json.loads(resp.content)
        assert payload['object'] == 'list'
        assert payload['data'][0]['kind'] == 'mcp'


@pytest.mark.django_db
def test_github_sort_last_used(monkeypatch, client):
    with patch('swarm.views.api_views.ENABLE_GITHUB_MARKETPLACE', True):
        from swarm.marketplace import github_service as gh
        from swarm.views import api_views as av

        def fake_search(topics, orgs, *, sort, order, query, token):
            # Two repos with one item each
            return [
                {'full_name': 'a/repo', 'html_url': 'https://github.com/a/repo'},
                {'full_name': 'b/repo', 'html_url': 'https://github.com/b/repo'},
            ]

        def fake_fetch(repo, token=None):
            if repo['full_name'] == 'a/repo':
                return [{'name': 'X', 'description': 'one'}]
            return [{'name': 'Y', 'description': 'two'}]

        # usage: (repo_full_name, name) -> ts
        def fake_usage():
            return {('b/repo', 'Y'): 100.0, ('a/repo', 'X'): 50.0}

        monkeypatch.setattr(gh, 'search_repos_by_topics', fake_search)
        monkeypatch.setattr(gh, 'fetch_repo_manifests', fake_fetch)
        monkeypatch.setattr(av, 'get_last_used_map', fake_usage)

        resp = client.get('/marketplace/github/blueprints/?sort=last_used')
        assert resp.status_code == 200
        names = [it['name'] for it in resp.json()['data']]
        assert names == ['Y', 'X']  # b/repo/Y used more recently
