import json
import pytest


@pytest.mark.django_db
def test_marketplace_blueprints_headless(monkeypatch, client):
    # Provide fake data via helper monkeypatch; avoids Wagtail dependency
    fake_items = [
        {
            'id': 1,
            'title': 'Demo Blueprint',
            'summary': 'An example',
            'version': '1.0.0',
            'category': {'slug': 'ai', 'name': 'AI'},
            'tags': ['demo', 'example'],
            'repository_url': 'https://example.com/repo',
            'manifest_json': '{}',
            'code_template': '# template',
        }
    ]

    from swarm.views import api_views as av
    monkeypatch.setattr(av, 'get_marketplace_blueprints', lambda: fake_items)

    resp = client.get('/marketplace/blueprints/?search=demo&tag=example')
    assert resp.status_code == 200
    payload = json.loads(resp.content)
    assert payload['object'] == 'list'
    assert len(payload['data']) == 1
    assert payload['data'][0]['title'] == 'Demo Blueprint'


@pytest.mark.django_db
def test_marketplace_mcp_configs_headless(monkeypatch, client):
    fake_items = [
        {
            'id': 10,
            'title': 'Filesystem Config',
            'summary': 'FS server',
            'version': '0.1.0',
            'server_name': 'filesystem',
            'config_template': '{"env": {"ALLOWED_PATH": "${ALLOWED_PATH}"}}',
        }
    ]

    from swarm.views import api_views as av
    monkeypatch.setattr(av, 'get_marketplace_mcp_configs', lambda: fake_items)

    resp = client.get('/marketplace/mcp-configs/?search=fs&server=files')
    assert resp.status_code == 200
    payload = json.loads(resp.content)
    assert payload['object'] == 'list'
    assert len(payload['data']) == 1
    assert payload['data'][0]['server_name'] == 'filesystem'

