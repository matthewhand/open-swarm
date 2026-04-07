
import sys
from unittest.mock import MagicMock, patch

# Mock all dependencies that are missing in the environment
mock_httpx = MagicMock()
sys.modules["httpx"] = mock_httpx
sys.modules["asgiref"] = MagicMock()
sys.modules["asgiref.sync"] = MagicMock()
sys.modules["django"] = MagicMock()
sys.modules["django.conf"] = MagicMock()
sys.modules["django.db"] = MagicMock()
sys.modules["django.db.models"] = MagicMock()
sys.modules["swarm.models.core_models"] = MagicMock()
sys.modules["swarm.settings"] = MagicMock()
sys.modules["swarm.utils.env_utils"] = MagicMock()

# Mock pytest
sys.modules["pytest"] = MagicMock()

# Now we can import the service
sys.path.insert(0, 'src')
from swarm.marketplace import github_service

import base64
import json

def test_fetch_repo_manifests_parallel():
    """Verify that fetch_repo_manifests still works correctly after optimization."""
    repo = {'full_name': 'owner/repo'}

    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self.json_data = json_data
        def json(self): return self.json_data

    def mock_get(url, **kwargs):
        if url.endswith('contents/open-swarm.json'):
            return MockResponse(404, {})
        if url.endswith('contents/swarm/blueprints') or url.endswith('contents/swarm/mcp'):
            base = "swarm/blueprints" if "blueprints" in url else "swarm/mcp"
            return MockResponse(200, [{'type': 'dir', 'path': f'{base}/item-0'}])
        if url.endswith('manifest.json'):
            content = base64.b64encode(json.dumps({'name': 'test-item'}).encode()).decode()
            return MockResponse(200, {'type': 'file', 'content': content})
        if '/contents/swarm/' in url and not url.endswith('.py'):
            return MockResponse(200, []) # No files for enrichment
        return MockResponse(404, {})

    class MockClient:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url, **kwargs): return mock_get(url, **kwargs)

    github_service.httpx.Client = MockClient

    results = github_service.fetch_repo_manifests(repo)

    assert len(results) == 2 # 1 blueprint + 1 mcp
    assert results[0]['name'] == 'test-item'
    assert results[1]['name'] == 'test-item'
    print("Test passed!")

if __name__ == "__main__":
    test_fetch_repo_manifests_parallel()
