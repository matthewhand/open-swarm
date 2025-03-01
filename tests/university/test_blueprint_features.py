import os
import pytest
import subprocess
import tempfile
from django.test import Client
from unittest.mock import patch
from blueprints.university.blueprint_university import UniversitySupportBlueprint
from blueprints.chatbot.blueprint_chatbot import ChatbotBlueprint
from blueprints.messenger.blueprint_messenger import MessengerBlueprint
from blueprints.django_chat.blueprint_django_chat import DjangoChatBlueprint

# Base environment setup
BASE_ENV = {
    "UNIT_TESTING": "true",
    "ENABLE_API_AUTH": "false",
    "SUPPORT_EMAIL": "test@example.com",
    "PYTHONPATH": os.path.abspath("."),
    "DJANGO_SETTINGS_MODULE": "swarm.settings"
}

# Dummy config path
CONFIG_PATH = os.path.abspath("swarm_config.json")

# Patch UniversityBaseViewSet.initial to skip authentication enforcement
@pytest.fixture(scope="module")
def bypass_auth():
    from blueprints.university.views import UniversityBaseViewSet
    original_initial = UniversityBaseViewSet.initial
    def mock_initial(self, request, *args, **kwargs):
        request.user = type('User', (), {'is_authenticated': True, 'is_anonymous': False})()
        super(UniversityBaseViewSet, self).initial(request, *args, **kwargs)
    UniversityBaseViewSet.initial = mock_initial
    yield
    UniversityBaseViewSet.initial = original_initial

# Mock BlueprintBase.__init__ to simplify CLI testing
@pytest.fixture
def mock_blueprint_init():
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
    original_init = BlueprintBase.__init__
    def mock_init(self, config, **kwargs):
        self.config = config
        self.swarm = type('Swarm', (), {
            'agents': {},
            'run': lambda *a, **kw: {"response": {"messages": [], "agent": None}}
        })()
        self.context_variables = {}
        self.starting_agent = None
        if self._is_create_agents_overridden():
            self.swarm.agents = self.create_agents()
            self.starting_agent = list(self.swarm.agents.values())[0] if self.swarm.agents else None
    BlueprintBase.__init__ = mock_init
    yield
    BlueprintBase.__init__ = original_init

@pytest.fixture(scope="module", autouse=True)
def setup_blueprint_urls(bypass_auth):
    # Register URLs for all blueprints under test
    for blueprint_cls in [UniversitySupportBlueprint, ChatbotBlueprint, MessengerBlueprint, DjangoChatBlueprint]:
        blueprint = blueprint_cls(config={"llm": {"default": {"provider": "openai", "model": "gpt-4o", "base_url": "https://api.openai.com/v1", "api_key": "dummy"}}})
        blueprint.register_blueprint_urls()
    yield

@pytest.fixture
def temp_db():
    """Create a temporary SQLite database file."""
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

def run_cli(blueprint_path, args, temp_db_path):
    """Helper to run CLI commands with proper setup."""
    env = BASE_ENV.copy()
    env["SQLITE_DB_PATH"] = temp_db_path
    cmd = ["python", blueprint_path] + args
    result = subprocess.run(
        cmd,
        env=env,
        cwd=os.path.abspath("."),
        capture_output=True,
        text=True,
        input="exit\n" if "--instruction" not in args else None  # Provide input only for interactive mode
    )
    return result

@pytest.mark.django_db
def test_non_interactive_mode_university(temp_db, mock_blueprint_init):
    """Test non-interactive mode for UniversitySupportBlueprint with --instruction."""
    blueprint_path = "blueprints/university/blueprint_university.py"
    instruction = "List all courses"
    args = ["--config", CONFIG_PATH, "--instruction", instruction]
    result = run_cli(blueprint_path, args, temp_db)
    output = result.stdout
    assert result.returncode == 0, f"Non-interactive mode failed: output={output}, stderr={result.stderr}"
    assert "University Support System Non-Interactive Mode" in output, f"Mode header missing: {output}"
    assert "Execution completed. Exiting." in output, f"Exit message missing: {output}"

@pytest.mark.django_db
def test_interactive_mode_university(temp_db, mock_blueprint_init):
    """Sanity check for interactive mode in UniversitySupportBlueprint."""
    blueprint_path = "blueprints/university/blueprint_university.py"
    args = ["--config", CONFIG_PATH]
    result = run_cli(blueprint_path, args, temp_db)
    output = result.stdout
    assert result.returncode == 0, f"Interactive mode failed: output={output}, stderr={result.stderr}"
    assert "University Support System Interactive Mode" in output, f"Mode header missing: {output}"
    assert "Exiting interactive mode." in output, f"Exit message missing: {output}"

def test_http_only_chatbot(temp_db):
    """Test that ChatbotBlueprint rejects CLI execution."""
    blueprint_path = "blueprints/chatbot/blueprint_chatbot.py"
    args = ["--config", CONFIG_PATH]
    result = run_cli(blueprint_path, args, temp_db)
    output = result.stderr  # Check stderr since message is printed there
    assert result.returncode == 1, f"Chatbot CLI execution should fail: output={output}"
    assert "This blueprint is designed for HTTP use only" in output, f"HTTP-only message missing: {output}"
    assert "/chatbot/" in output, f"URL missing: {output}"

def test_http_only_messenger(temp_db):
    """Test that MessengerBlueprint rejects CLI execution."""
    blueprint_path = "blueprints/messenger/blueprint_messenger.py"
    args = ["--config", CONFIG_PATH]
    result = run_cli(blueprint_path, args, temp_db)
    output = result.stderr  # Check stderr since message is printed there
    assert result.returncode == 1, f"Messenger CLI execution should fail: output={output}"
    assert "This blueprint is designed for HTTP use only" in output, f"HTTP-only message missing: {output}"
    assert "/messenger/" in output, f"URL missing: {output}"

def test_http_only_django_chat(temp_db):
    """Test that DjangoChatBlueprint rejects CLI execution."""
    blueprint_path = "blueprints/django_chat/blueprint_django_chat.py"
    args = ["--config", CONFIG_PATH]
    result = run_cli(blueprint_path, args, temp_db)
    output = result.stderr  # Check stderr since message is printed there
    assert result.returncode == 1, f"Django Chat CLI execution should fail: output={output}"
    assert "This blueprint is designed for HTTP use only" in output, f"HTTP-only message missing: {output}"
    assert "/django_chat/" in output, f"URL missing: {output}"

@pytest.mark.django_db
def test_http_endpoints_accessible():
    """Test that HTTP endpoints for blueprints are accessible."""
    client = Client()
    endpoints = [
        "/chatbot/",
        "/messenger/",
        "/django_chat/",
        "/v1/university/teaching-units/"
    ]
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code in (200, 302, 404), f"Endpoint {endpoint} returned {response.status_code}: {response.content}"
        assert response.status_code != 401, f"Endpoint {endpoint} unauthorized: {response.content}"
