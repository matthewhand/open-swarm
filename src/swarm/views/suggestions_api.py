"""REQ-85: GET ``/v1/agents/<id>/suggestions/`` — kickstart / continue chips.

Chrome only. Never writes chips into the transcript. Fail-soft empty list
when the toggle is off, the list is unusable, or the specialist fails.
"""

from __future__ import annotations

import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.core.agent_settings import is_use_suggestions
from swarm.core.chat_store import normalize_agent_id
from swarm.core.suggestions import (
    load_continue_messages,
    resolve_suggestions_agents,
    run_suggestions,
)
from swarm.views.agent_settings_api import SETTINGS_API_PERMISSIONS

logger = logging.getLogger(__name__)


class AgentSuggestionsAPIView(APIView):
    """GET /v1/agents/<agent_id>/suggestions/?mode=kickstart|continue"""

    permission_classes = SETTINGS_API_PERMISSIONS

    @extend_schema(
        operation_id="v1_agent_suggestions_get",
        summary="Quick-select suggestion chips for a consumer agent (REQ-85)",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request, agent_id: str, *_args, **_kwargs):
        agent = normalize_agent_id(agent_id)
        if not is_use_suggestions(agent):
            return Response(
                {"object": "suggestions", "agent_id": agent, "suggestions": []},
                status=status.HTTP_200_OK,
            )
        raw_mode = str(request.query_params.get("mode") or "kickstart").strip().lower()
        mode = "continue" if raw_mode == "continue" else "kickstart"
        conversation_id = str(request.query_params.get("conversation_id") or "").strip()
        messages = (
            load_continue_messages(request.user, agent, conversation_id)
            if mode == "continue"
            else []
        )
        agents = resolve_suggestions_agents(agent)
        try:
            chips = run_suggestions(mode=mode, messages=messages, agents=agents)
        except Exception:
            logger.debug("suggestions API omitted for %s", agent, exc_info=True)
            chips = []
        return Response(
            {"object": "suggestions", "agent_id": agent, "suggestions": chips},
            status=status.HTTP_200_OK,
        )
