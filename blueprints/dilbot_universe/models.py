from django.db import models

class AgentInstruction(models.Model):
    agent_name = models.CharField(max_length=100, unique=True)
    instruction_text = models.TextField()
    model = models.CharField(max_length=100, default="default")
    env_vars = models.TextField(blank=True, null=True)
    mcp_servers = models.TextField(blank=True, null=True)
    nemo_guardrails_config = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.agent_name

    class Meta:
        app_label = 'blueprints.dilbot_universe'
