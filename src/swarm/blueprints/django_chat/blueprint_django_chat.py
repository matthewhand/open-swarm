"""
Django Chat Blueprint

A blueprint providing a web-based chat interface with conversation history management.
HTTP-only; not intended for CLI use.
"""

import asyncio
import logging
import os
import sys
import threading
import time
from typing import Any

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rich.console import Console
from rich.style import Style
from rich.text import Text

from swarm.blueprints.common.operation_box_utils import display_operation_box
from swarm.core.blueprint_base import BlueprintBase as Blueprint
from swarm.models import ChatConversation
from swarm.utils.logger_setup import setup_logger

# Django imports after CLI rejection
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
import django

django.setup()

# --- Logging Setup ---
def setup_logging():
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args, _ = parser.parse_known_args()
    loglevel = os.environ.get('LOGLEVEL', None)
    if args.debug or os.environ.get('SWARM_DEBUG', '0') == '1' or (loglevel and loglevel.upper() == 'DEBUG'):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    return args

args = setup_logging()

logger = logging.getLogger(__name__)

logger = setup_logger(__name__)

# Reject CLI execution immediately
if __name__ == "__main__":
    logger.info("DjangoChatBlueprint is an HTTP-only service. Access it via the web interface at /django_chat/.")
    print("This blueprint is designed for HTTP use only. Please access it via the web server at /django_chat/", file=sys.stderr)
    sys.stderr.flush()
    sys.exit(1)

class DjangoChatSpinner:
    FRAMES = [
        "Generating.", "Generating..", "Generating...", "Running...",
        "⠋ Generating...", "⠙ Generating...", "⠹ Generating...", "⠸ Generating...",
        "⠼ Generating...", "⠴ Generating...", "⠦ Generating...", "⠧ Generating...",
        "⠇ Generating...", "⠏ Generating...", "🤖 Generating...", "💡 Generating...", "✨ Generating..."
    ]
    SLOW_FRAME = "Generating... Taking longer than expected"
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10  # seconds

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._start_time = None
        self.console = Console()
        self._last_frame = None
        self._last_slow = False

    def start(self):
        self._stop_event.clear()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        idx = 0
        while not self._stop_event.is_set():
            elapsed = time.time() - self._start_time
            if elapsed > self.SLOW_THRESHOLD:
                txt = Text(self.SLOW_FRAME, style=Style(color="yellow", bold=True))
                self._last_frame = self.SLOW_FRAME
                self._last_slow = True
            else:
                frame = self.FRAMES[idx % len(self.FRAMES)]
                txt = Text(frame, style=Style(color="cyan", bold=True))
                self._last_frame = frame
                self._last_slow = False
            self.console.print(txt, end="\r", soft_wrap=True, highlight=False)
            time.sleep(self.INTERVAL)
            idx += 1
        self.console.print(" " * 40, end="\r")  # Clear line

    def stop(self, final_message="Done!"):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self.console.print(Text(final_message, style=Style(color="green", bold=True)))

    def current_spinner_state(self):
        if self._last_slow:
            return self.SLOW_FRAME
        return self._last_frame or self.FRAMES[0]


class DjangoChatBlueprint(Blueprint):
    def __init__(self, blueprint_id: str = "django_chat", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self.blueprint_id = blueprint_id
        self.config_path = config_path
        # NOTE: do NOT re-assign self._config / self._llm_profile_name here — the
        # base __init__ already loads the config (from app.config when none is
        # passed). Nulling them broke LLM-profile resolution at runtime (the
        # blueprint reported "not configured" even with a valid llm profile).
        self._markdown_output = None
        class DummyLLM:
            def chat_completion_stream(self, _messages, **_):
                class DummyStream:
                    def __aiter__(self): return self
                    async def __anext__(self):
                        raise StopAsyncIteration
                return DummyStream()
        self.llm = DummyLLM()

    @property
    def metadata(self) -> dict[str, Any]:
        logger.debug("Fetching metadata")
        return {
            "title": "Django Chat Interface",
            "description": "A web-based chat interface with conversation history management. HTTP-only.",
            "cli_name": "django_chat",
            "env_vars": [],
            "urls_module": "blueprints.django_chat.urls",
            "url_prefix": "django_chat/"
        }

    def get_or_create_default_user(self):
        """Create or retrieve a default 'testuser' (DEBUG mode only).

        Refused outside debug mode (DJANGO_DEBUG=true); never uses a
        hardcoded password (random per-process unless TESTUSER_PASSWORD is set).
        """
        from django.core.exceptions import PermissionDenied

        from swarm.utils.env_utils import get_testuser_password, is_django_debug
        if not is_django_debug():
            raise PermissionDenied(
                "The default 'testuser' fallback is a development-only convenience "
                "and is disabled because DJANGO_DEBUG is not enabled."
            )
        username = "testuser"
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, password=get_testuser_password())
            logger.info(f"Created default user: {username}")
        return user

    @csrf_exempt
    @login_required
    def django_chat(self, request):
        """Render the django_chat UI with user-specific conversation history."""
        logger.debug("Rendering django_chat web UI")
        user = request.user if request.user.is_authenticated else self.get_or_create_default_user()
        conversations = ChatConversation.objects.filter(student=user).order_by('-created_at')
        context = {
            "dark_mode": request.session.get('dark_mode', True),
            "is_chatbot": False,
            "conversations": conversations
        }
        return render(request, "django_chat/django_chat_webpage.html", context)

    def render_prompt(self, _template_name: str, context: dict) -> str:
        return f"User request: {context.get('user_request', '')}\nHistory: {context.get('history', '')}\nAvailable tools: {', '.join(context.get('available_tools', []))}"

    async def run(self, messages: list[dict[str, str]], **kwargs):
        """Main execution entry point for the DjangoChat blueprint.

        Accepts **kwargs (e.g. ``stream=``) for compatibility with the
        OpenAI-compatible API layer, which always passes ``stream``.
        """
        # Proxy the conversation to the configured LLM profile (OpenAI-compatible),
        # mirroring DynamicTeamBlueprint. Previously this only yielded a simulated
        # "[DjangoChat LLM] Would respond to: …" box — it never called a model.
        from openai import AsyncOpenAI

        logger.info("DjangoChatBlueprint run method called.")
        try:
            profile = self.get_llm_profile(self.llm_profile_name)
            base_url = profile.get("base_url")
            api_key = profile.get("api_key") or "ollama"  # local backends ignore the key
            model_name = profile.get("model") or "gpt-oss:20b"
        except Exception as e:  # config not initialized / no profile
            logger.warning("DjangoChat: LLM profile unavailable (%s)", e)
            base_url = None

        if not base_url:
            yield {"messages": [{"role": "assistant", "content": (
                "DjangoChat is not configured with an LLM profile. "
                "Add an 'llm' profile in swarm_config.json to enable responses."
            )}]}
            return

        client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        try:
            resp = await client.chat.completions.create(
                model=model_name, messages=messages, stream=False
            )
            text = (resp.choices[0].message.content or "").strip()
            yield {"messages": [{"role": "assistant", "content": text}]}
        except Exception as e:
            logger.error(f"DjangoChat LLM call failed: {e}", exc_info=True)
            yield {"messages": [{"role": "assistant", "content": f"[DjangoChat Error] {e}"}]}

    def run_with_context(self, _messages: list[dict[str, str]], context_variables: dict) -> dict:
        """Minimal implementation for CLI compatibility without agents."""
        logger.debug("Running with context (UI-focused implementation)")
        return {
            "response": {"messages": [{"role": "assistant", "content": "Django Chat UI active via web interface at /django_chat/"}]},
            "context_variables": context_variables
        }

if __name__ == "__main__":
    messages = [
        {"role": "user", "content": "Start a chat session about Django."}
    ]
    blueprint = DjangoChatBlueprint(blueprint_id="demo-1")
    async def run_and_print():
        spinner = DjangoChatSpinner()
        spinner.start()
        try:
            all_results = []
            async for response in blueprint.run(messages):
                content = response["messages"][0]["content"] if (isinstance(response, dict) and "messages" in response and response["messages"]) else str(response)
                all_results.append(content)
                # Enhanced progressive output
                if isinstance(response, dict) and (response.get("progress") or response.get("matches")):
                    display_operation_box(
                        title="Progressive Operation",
                        content="\n".join(response.get("matches", [])),
                        style="bold cyan" if response.get("type") == "code_search" else "bold magenta",
                        result_count=len(response.get("matches", [])) if response.get("matches") is not None else None,
                        params={k: v for k, v in response.items() if k not in {'matches', 'progress', 'total', 'truncated', 'done'}},
                        progress_line=response.get('progress'),
                        total_lines=response.get('total'),
                        spinner_state=spinner.current_spinner_state() if hasattr(spinner, 'current_spinner_state') else None,
                        op_type=response.get("type", "search"),
                        emoji="🔍" if response.get("type") == "code_search" else "🧠"
                    )
        finally:
            spinner.stop()
        display_operation_box(
            title="DjangoChat Output",
            content="\n".join(all_results),
            style="bold green",
            result_count=len(all_results),
            params={"prompt": messages[0]["content"]},
            op_type="django_chat"
        )
    asyncio.run(run_and_print())
