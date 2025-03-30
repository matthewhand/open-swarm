from rest_framework import serializers
from swarm.models import ChatConversation, ChatMessage # Use correct model name
from typing import List, Dict, Optional, Union, Any # Import necessary types

# === Existing Serializers ===

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = '__all__'

class ChatConversationSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True) # Optional: Nest messages

    class Meta:
        model = ChatConversation
        fields = ['conversation_id', 'created_at', 'student', 'messages'] # Explicit fields


# === OpenAI Compatible Chat Completion Serializers ===

# --- Request Serializers ---

class ChatCompletionMessageSerializer(serializers.Serializer):
    """Serializer for a single message within the request."""
    role = serializers.ChoiceField(choices=['system', 'user', 'assistant', 'tool'])
    content = serializers.CharField(allow_null=True, required=False) # Content can be null for tool calls
    name = serializers.CharField(required=False) # Optional name for function/tool role
    tool_calls = serializers.ListField(child=serializers.DictField(), required=False) # For assistant messages with tool calls
    tool_call_id = serializers.CharField(required=False) # For tool role messages

    # REMOVED validate_content method

    def validate(self, data):
        """
        Validate message based on role and content/tool_calls presence.
        'data' contains the validated fields for this specific message object.
        """
        role = data.get('role')
        content = data.get('content')
        tool_calls = data.get('tool_calls')
        tool_call_id = data.get('tool_call_id') # For tool role

        # --- Role-specific validation based on OpenAI spec ---

        # User/System messages MUST have content
        if role in ['user', 'system'] and content is None:
             raise serializers.ValidationError(f"Content cannot be null for role '{role}'.")

        # Assistant messages: Must have content OR tool_calls (or potentially both?)
        if role == 'assistant' and content is None and not tool_calls:
             raise serializers.ValidationError("Assistant message must have 'content' or 'tool_calls'.")
             # Note: OpenAI spec might allow *both* content and tool_calls. Adjust if needed.

        # Tool messages MUST have content and tool_call_id
        if role == 'tool':
            if content is None:
                 raise serializers.ValidationError("Content cannot be null for role 'tool'.")
            if not tool_call_id:
                 raise serializers.ValidationError("Missing 'tool_call_id' for role 'tool'.")

        # Tool calls should only be present for assistant role?
        if role != 'assistant' and tool_calls:
             raise serializers.ValidationError(f"'tool_calls' are only valid for role 'assistant', not '{role}'.")

        # tool_call_id should only be present for tool role?
        if role != 'tool' and tool_call_id:
             raise serializers.ValidationError(f"'tool_call_id' is only valid for role 'tool', not '{role}'.")

        # 'name' is used for function/tool role, maybe assistant responses to tool calls? Check spec.
        # Add validation for 'name' if required.

        return data # Return the validated data dict


class ChatCompletionRequestSerializer(serializers.Serializer):
    """Serializer for the main chat completion request body."""
    model = serializers.CharField(max_length=100)
    messages = serializers.ListField(child=ChatCompletionMessageSerializer(), min_length=1)
    stream = serializers.BooleanField(default=False)
    # Add other common OpenAI parameters as needed
    temperature = serializers.FloatField(min_value=0.0, max_value=2.0, required=False)
    max_tokens = serializers.IntegerField(min_value=1, required=False)
    top_p = serializers.FloatField(min_value=0.0, max_value=1.0, required=False)
    n = serializers.IntegerField(min_value=1, default=1, required=False) # Number of choices to generate
    # Use JSONField for fields that accept multiple types (string or list/dict)
    stop = serializers.JSONField(required=False)
    presence_penalty = serializers.FloatField(min_value=-2.0, max_value=2.0, required=False)
    frequency_penalty = serializers.FloatField(min_value=-2.0, max_value=2.0, required=False)
    logit_bias = serializers.DictField(child=serializers.FloatField(), required=False)
    user = serializers.CharField(required=False) # User ID string
    # Tools / Functions (Example structure, adjust based on exact spec)
    tools = serializers.ListField(child=serializers.DictField(), required=False)
    # Use JSONField for fields that accept multiple types (string or dict)
    tool_choice = serializers.JSONField(required=False)


# --- Response Serializers (Non-Streaming) ---

class ResponseMessageSerializer(serializers.Serializer):
    """Serializer for the message object in the response."""
    role = serializers.ChoiceField(choices=['assistant']) # Typically only assistant role in response
    content = serializers.CharField(allow_null=True, required=False) # Can be null if tool_calls present
    tool_calls = serializers.ListField(child=serializers.DictField(), required=False)

class ResponseChoiceSerializer(serializers.Serializer):
    """Serializer for a single choice in the response."""
    index = serializers.IntegerField()
    message = ResponseMessageSerializer()
    finish_reason = serializers.ChoiceField(
        choices=['stop', 'length', 'tool_calls', 'content_filter', 'function_call', 'error'], # Add 'error' or others if needed
        allow_null=True, # Can be null in streaming chunks before the end
        required=False
    )

class UsageSerializer(serializers.Serializer):
    """Serializer for token usage information."""
    prompt_tokens = serializers.IntegerField()
    completion_tokens = serializers.IntegerField()
    total_tokens = serializers.IntegerField()

class ChatCompletionResponseSerializer(serializers.Serializer):
    """Serializer for the complete non-streaming chat completion response."""
    id = serializers.CharField()
    object = serializers.CharField(default="chat.completion")
    created = serializers.IntegerField() # Unix timestamp
    model = serializers.CharField()
    choices = serializers.ListField(child=ResponseChoiceSerializer())
    usage = UsageSerializer(required=False) # Usage might not always be present


# --- Response Serializers (Streaming Chunks) ---

class DeltaMessageSerializer(serializers.Serializer):
    """Serializer for the 'delta' object within a streaming chunk."""
    role = serializers.ChoiceField(choices=['system', 'user', 'assistant', 'tool'], required=False) # Role might appear in first chunk
    content = serializers.CharField(required=False) # Content diff
    tool_calls = serializers.ListField(child=serializers.DictField(), required=False) # Tool call diffs/chunks

class ChunkChoiceSerializer(serializers.Serializer):
    """Serializer for a single choice within a streaming chunk."""
    index = serializers.IntegerField()
    delta = DeltaMessageSerializer()
    finish_reason = serializers.ChoiceField(
        choices=['stop', 'length', 'tool_calls', 'content_filter', 'function_call', 'error'],
        allow_null=True, # Usually null until the last chunk for that choice
        required=False
    )

class ChatCompletionChunkResponseSerializer(serializers.Serializer):
    """Serializer for a single streaming chunk response."""
    id = serializers.CharField()
    object = serializers.CharField(default="chat.completion.chunk")
    created = serializers.IntegerField() # Unix timestamp
    model = serializers.CharField()
    choices = serializers.ListField(child=ChunkChoiceSerializer())
    # Usage is typically NOT included in chunks, only in the final non-streaming response

