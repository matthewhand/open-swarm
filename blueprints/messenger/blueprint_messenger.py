"""
Messenger Blueprint

A web-based messenger interface. HTTP-only.
"""

import logging
import sys
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d - %(message)s"))
logger.addHandler(handler)

if __name__ == "__main__":
    logger.info("MessengerBlueprint is an HTTP-only service. Access it via the web interface at /messenger/.")
    print("This blueprint is designed for HTTP use only. Please access it via the web server at /messenger/", file=sys.stderr)
    sys.stderr.flush()
    sys.exit(1)

from swarm.extensions.blueprint.blueprint_base import BlueprintBase as Blueprint

class MessengerBlueprint(Blueprint):
    @property
    def metadata(self) -> Dict[str, Any]:
        logger.debug("Fetching metadata")
        return {
            "title": "Messenger Interface",
            "description": "A web-based messenger interface. HTTP-only.",
            "cli_name": "messenger",
            "env_vars": [],
            "urls_module": "blueprints.messenger.urls",
            "url_prefix": "messenger/"
        }

    def messenger(self, request):
        from django.shortcuts import render
        from django.views.decorators.csrf import csrf_exempt
        @csrf_exempt
        def inner(request):
            logger.debug("Rendering messenger web UI")
            context = {
                "dark_mode": request.session.get('dark_mode', True),
                "is_chatbot": False
            }
            return render(request, "messenger/messenger.html", context)
        return inner(request)

    def run_with_context(self, messages: List[Dict[str, str]], context_variables: dict) -> dict:
        logger.debug("Running with context (UI-focused implementation)")
        return {
            "response": {"messages": [{"role": "assistant", "content": "Messenger UI active via web interface at /messenger/"}]},
            "context_variables": context_variables
        }
