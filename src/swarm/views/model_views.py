"""
Views related to listing and describing available models (Blueprints).
"""
import logging
from django.conf import settings
from django.http import JsonResponse # Not used directly, Response is preferred
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from drf_spectacular.utils import extend_schema

# *** Import async_to_sync ***
from asgiref.sync import async_to_sync

# Import the utility function
from .utils import get_available_blueprints
from ..permissions import HasValidTokenOrSession

logger = logging.getLogger(__name__)

# ==============================================================================
# API Views (DRF based) for Models
# ==============================================================================

class ListModelsView(APIView):
    """
    API view to list available models (Blueprints).
    Compliant with OpenAI API's /v1/models endpoint structure.
    """
    permission_classes = [HasValidTokenOrSession]

    @extend_schema(
        responses={ # Simplified schema for brevity
            200: {"description": "A list of available models."}
        }
    )
    # *** Make the handler synchronous ***
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests to list available models.
        """
        try:
            # *** Call the async utility function using async_to_sync ***
            # Ensure get_available_blueprints is awaitable (async def or wrapped)
            available_blueprints_dict = async_to_sync(get_available_blueprints)()

            models_data = [
                {
                    "id": model_id,
                    "object": "model",
                    "created": 0, # Placeholder
                    "owned_by": "open-swarm",
                    # Access metadata safely
                    "profile_name": metadata.get('profile_name', 'unknown') if isinstance(metadata, dict) else 'unknown'
                }
                # Ensure iteration works correctly
                for model_id, metadata in (available_blueprints_dict.items() if isinstance(available_blueprints_dict, dict) else [])
            ]

            response_data = {
                "object": "list",
                "data": models_data,
            }
            # Return the standard sync Response
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving available blueprints: {e}", exc_info=True)
            # Return the standard sync Response
            return Response(
                {"error": "Internal server error retrieving models."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
