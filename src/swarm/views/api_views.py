import time
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
# *** Import async_to_sync ***
from asgiref.sync import async_to_sync

from swarm.views.utils import get_available_blueprints

logger = logging.getLogger(__name__)

class ModelsListView(APIView):
    """
    API view to list available models (blueprints) compatible with OpenAI's /v1/models format.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        try:
            # *** Use async_to_sync to call the async function ***
            available_blueprints = async_to_sync(get_available_blueprints)()

            models_data = []
            current_time = int(time.time())
            if isinstance(available_blueprints, dict):
                blueprint_ids = available_blueprints.keys()
            elif isinstance(available_blueprints, list):
                 blueprint_ids = available_blueprints
            else:
                 logger.error(f"Unexpected type from get_available_blueprints: {type(available_blueprints)}")
                 blueprint_ids = []

            for blueprint_id in blueprint_ids:
                models_data.append({
                    "id": blueprint_id,
                    "object": "model",
                    "created": current_time,
                    "owned_by": "open-swarm",
                })

            response_payload = {
                "object": "list",
                "data": models_data,
            }
            return Response(response_payload, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error retrieving available models.")
            return Response(
                {"error": "Failed to retrieve models list."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

