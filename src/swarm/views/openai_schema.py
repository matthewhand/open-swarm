"""drf-spectacular schema decorators for the OpenAI-compatible endpoints.

Without these, ``/v1/chat/completions`` and ``/v1/responses`` show up in the
OpenAPI spec (``/api/schema/``) with auto-guessed, near-empty detail. These give
them a real request/response shape + examples so the spec is usable for client
codegen.
"""

from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from rest_framework import serializers

_MESSAGES = serializers.ListField(
    child=serializers.DictField(),
    help_text='OpenAI-style messages, e.g. [{"role": "user", "content": "..."}].',
)

chat_completions_schema = extend_schema(
    tags=["OpenAI"],
    summary="Create a chat completion",
    description=(
        "OpenAI-compatible chat completions. The `model` field selects which "
        "blueprint handles the request (e.g. `cli_fusion`, `cli_map`, "
        "`cli_agent`). Set `stream: true` for Server-Sent Events."
    ),
    request=inline_serializer(
        name="ChatCompletionRequest",
        fields={
            "model": serializers.CharField(help_text="Blueprint id, e.g. cli_fusion."),
            "messages": _MESSAGES,
            "stream": serializers.BooleanField(required=False, default=False),
        },
    ),
    responses={
        200: inline_serializer(
            name="ChatCompletionResponse",
            fields={
                "id": serializers.CharField(),
                "object": serializers.CharField(help_text='"chat.completion"'),
                "created": serializers.IntegerField(),
                "model": serializers.CharField(),
                "choices": serializers.ListField(child=serializers.DictField()),
            },
        )
    },
    examples=[
        OpenApiExample(
            "Consensus across CLIs",
            value={
                "model": "cli_fusion",
                "messages": [{"role": "user", "content": "In one word, capital of France?"}],
            },
            request_only=True,
        )
    ],
)

responses_schema = extend_schema(
    tags=["OpenAI"],
    summary="Create a response (Responses API)",
    description=(
        "OpenAI-compatible Responses API. `input` may be a string or an array of "
        "messages; `instructions` is prepended as a system message. The `model` "
        "field selects the blueprint. Set `stream: true` for SSE delta events."
    ),
    request=inline_serializer(
        name="ResponsesRequest",
        fields={
            "model": serializers.CharField(help_text="Blueprint id, e.g. cli_fusion."),
            "input": serializers.JSONField(help_text="A string, or an array of message objects."),
            "instructions": serializers.CharField(required=False, help_text="Optional system instructions."),
            "stream": serializers.BooleanField(required=False, default=False),
        },
    ),
    responses={
        200: inline_serializer(
            name="ResponsesResponse",
            fields={
                "id": serializers.CharField(),
                "object": serializers.CharField(help_text='"response"'),
                "created_at": serializers.IntegerField(),
                "model": serializers.CharField(),
                "status": serializers.CharField(),
                "output": serializers.ListField(child=serializers.DictField()),
                "output_text": serializers.CharField(),
            },
        )
    },
    examples=[
        OpenApiExample(
            "String input",
            value={"model": "cli_fusion", "input": "In one word, capital of France?"},
            request_only=True,
        )
    ],
)


# --- Auth scheme extensions: document Bearer-token auth in the OpenAPI spec
#     (and silence drf-spectacular "could not resolve authenticator" warnings). ---
from drf_spectacular.extensions import OpenApiAuthenticationExtension  # noqa: E402


class StaticTokenScheme(OpenApiAuthenticationExtension):
    target_class = "swarm.auth.StaticTokenAuthentication"
    name = "BearerToken"

    def get_security_definition(self, auto_schema):  # noqa: ARG002
        return {"type": "http", "scheme": "bearer", "description": "API_AUTH_TOKEN as a Bearer token."}


class SessionAuthScheme(OpenApiAuthenticationExtension):
    target_class = "swarm.auth.CustomSessionAuthentication"
    name = "SessionAuth"

    def get_security_definition(self, auto_schema):  # noqa: ARG002
        return {"type": "apiKey", "in": "cookie", "name": "sessionid"}
