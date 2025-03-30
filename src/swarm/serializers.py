from rest_framework import serializers
from rest_framework.exceptions import ValidationError # Import ValidationError

class ChatMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["system", "user", "assistant", "tool"])
    content = serializers.CharField(allow_null=True, required=False)

    def validate(self, data):
        role = data.get('role')
        content = data.get('content')
        if role == 'user' and content is None:
            # Raise field-specific error
            raise ValidationError({"content": "User messages must have content."})
        return data

class ChatCompletionRequestSerializer(serializers.Serializer):
    model = serializers.CharField(max_length=100)
    messages = ChatMessageSerializer(many=True, min_length=1)
    stream = serializers.BooleanField(default=False)
    params = serializers.JSONField(required=False, allow_null=True)
    temperature = serializers.FloatField(min_value=0.0, max_value=2.0, required=False)
    max_tokens = serializers.IntegerField(min_value=1, required=False)

    # Removed validate_model and validate_stream methods

    def validate(self, data):
        """Explicit type checks in the main validate method."""
        errors = {}
        # Check model type
        if 'model' in data and not isinstance(data['model'], str):
            # Use field-specific error format
            errors['model'] = ["Must be a string."]
            # Alternatively, for non-field errors: raise ValidationError("Model must be a string.")

        # Check stream type
        if 'stream' in data and not isinstance(data['stream'], bool):
             errors['stream'] = ["Must be a boolean."]

        # Check messages type and content
        if 'messages' in data:
            if not isinstance(data['messages'], list):
                 errors['messages'] = ["Must be a list."]
            elif not data['messages']:
                 errors['messages'] = ["This list may not be empty."]
            # Individual message validation happens in ChatMessageSerializer

        # Add other cross-field validation if needed

        if errors:
            raise ValidationError(errors) # Raise collected errors

        return data

