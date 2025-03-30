from rest_framework import serializers
from blueprints.chc.models import AgentInstruction

class AgentInstructionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentInstruction
        fields = ['id', 'agent_name', 'instruction_text', 'model', 'env_vars', 'mcp_servers', 'created_at', 'updated_at']
