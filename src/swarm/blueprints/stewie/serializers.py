from blueprints.chc.models import AgentInstruction
from rest_framework import serializers


class AgentInstructionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentInstruction
        fields = ['id', 'agent_name', 'instruction_text', 'model', 'env_vars', 'mcp_servers', 'created_at', 'updated_at']

class StewieSerializer(serializers.Serializer):
    pass
