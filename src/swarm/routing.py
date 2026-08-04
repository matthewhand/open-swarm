"""Websocket URL routing for the swarm project.

Kept separate from ``swarm.urls`` (HTTP) so that ``swarm.asgi`` can build a
``URLRouter`` without importing the (much heavier) HTTP urlconf. The single
route mirrors the convention used by both the Django template UI
(``templates/chat.html`` HTMx ``ws-connect``) and the SPA
(``webui/frontend/src/lib/chatWs.ts``):

    ws(s)://<host>/ws/ai-demo/<conversation_id>/
"""

from django.urls import path

from swarm.consumers import DjangoChatConsumer

websocket_urlpatterns = [
    path("ws/ai-demo/<str:conversation_id>/", DjangoChatConsumer.as_asgi()),
]
