from django.db import models

class AgentInstruction(models.Model):
    agent_name = models.CharField(max_length=50, unique=True, help_text="Unique name (e.g., 'PeterGriffin').")
    instruction_text = models.TextField(help_text="Instructions for the agent.")
    model = models.CharField(max_length=50, default="default", help_text="LLM model.")
    env_vars = models.TextField(blank=True, null=True, help_text="JSON env variables.")
    mcp_servers = models.TextField(blank=True, null=True, help_text="JSON MCP servers.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "blueprints_chc"
        db_table = "swarm_agent_instruction_chc"
        verbose_name = "Agent Instruction"
        verbose_name_plural = "Agent Instructions"

    def __str__(self):
        return f"{self.agent_name} Instruction"
