from rest_framework import serializers
from swarm.models import ChatMessage
import logging # Import logging

logger = logging.getLogger(__name__) # Add logger for debugging

class MessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["system", "user", "assistant", "tool"])
    content = serializers.CharField(allow_null=True, required=False, allow_blank=True)
    name = serializers.CharField(required=False)

    def validate(self, data):
        role = data.get('role')
        content = data.get('content')
        if role in ['user', 'assistant'] and content is None:
             raise serializers.ValidationError(f"Field 'content' is required for role '{role}'.")
        return data

class ChatCompletionRequestSerializer(serializers.Serializer):
    model = serializers.CharField(max_length=255)
    messages = MessageSerializer(many=True, min_length=1)
    stream = serializers.BooleanField(default=False)
    params = serializers.JSONField(required=False, allow_null=True)

    # REMOVED validate_model method

    # *** ADDED top-level validate method ***
    def validate(self, data):
        """
        Perform object-level validation.
        Check raw input types before DRF field coercion.
        """
        # Check the type of 'model' in the original input data
        # `initial_data` holds the data before field processing
        model_value = self.initial_data.get('model')
        logger.debug(f"Top-level validate checking model type. Got: {type(model_value)}, value: {model_value}")
        if model_value is not None and not isinstance(model_value, str):
             raise serializers.ValidationError({"model": "Field 'model' must be a string."})

        # You can add other cross-field validations here if needed

        # Return the validated data (after field-level validation has run)
        return data

    def validate_messages(self, value):
        # This runs on the 'messages' field *after* it passes MessageSerializer validation
        if not value:
            raise serializers.ValidationError("Messages list cannot be empty.")
        for i, msg in enumerate(value):
            if not isinstance(msg, dict):
                 raise serializers.ValidationError(f"Message at index {i} must be a dictionary.")
            if 'role' not in msg:
                 raise serializers.ValidationError(f"Message at index {i} must have a 'role'.")
        return value

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = '__all__'
        # read_only_fields = ('timestamp',)
