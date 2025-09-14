import json
import pytest


@pytest.mark.django_db
def test_github_blueprints_endpoint(monkeypatch, client):
    # Enable feature via settings module attribute after import
    from swarm import settings as sw_settings
    monkeypatch.setattr(sw_settings, 'ENABLE_GITHUB_MARKETPLACE', True, raising=False)

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
    from swarm import settings as sw_settings
    monkeypatch.setattr(sw_settings, 'ENABLE_GITHUB_MARKETPLACE', True, raising=False)
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

