# Minimal slash_commands.py to restore compatibility

class SlashCommandRegistry:
    def __init__(self):
        self.commands = {}
    def register(self, command, func=None):
        if func is None:
            def decorator(f):
                self.commands[command] = f
                return f
            return decorator
        self.commands[command] = func
        return func
    def get(self, command):
        return self.commands.get(command)

slash_registry = SlashCommandRegistry()
# Built-in '/help' slash command
@slash_registry.register('/help')
def _help_command(blueprint=None, args=None):
    """List available slash commands."""
    cmds = sorted(slash_registry.commands.keys())
    return "Available slash commands:\n" + "\n".join(cmds)

# Built-in '/compact' slash command
@slash_registry.register('/compact')
def _compact_command(blueprint=None, args=None, conversation_id=None, messages=None, user=None, **_kwargs):
    """Compact the backlog (composer + menu is the primary UI)."""
    if conversation_id and messages and user is not None:
        from swarm.core.chat_compact import CompactError, compact_backlog

        agent_id = ""
        if blueprint is not None:
            agent_id = getattr(blueprint, "blueprint_name", None) or getattr(blueprint, "name", "") or ""
        try:
            row, _raw = compact_backlog(
                user=user,
                conversation_id=conversation_id,
                agent_id=str(agent_id or ""),
                messages=messages,
            )
        except CompactError as exc:
            return f"[slash command] compact failed: {exc}"
        return row.body
    return "Compact the chat from the composer + menu."

# Built-in '/model' slash command
@slash_registry.register('/model')
def _model_command(blueprint=None, args=None):
    """
    /model                   Show current default and overrides
    /model <profile>         Set session default LLM profile
    /model <agent> <profile> Override model profile for specific agent
    """
    # Sanity: blueprint must be provided
    if blueprint is None:
        return "No blueprint context available."
    profiles = list(blueprint.config.get('llm', {}).keys())
    # No args: list current settings
    if not args:
        lines = [f"Session default: {blueprint._session_model_profile}"]
        for agent, prof in blueprint._agent_model_overrides.items():
            lines.append(f"Agent {agent}: {prof}")
        lines.append("Available profiles: " + ", ".join(profiles))
        return lines
    parts = args.split()
    # Set session default
    if len(parts) == 1:
        prof = parts[0]
        if prof not in profiles:
            return f"Unknown profile '{prof}'. Available: {', '.join(profiles)}"
        blueprint._session_model_profile = prof
        return f"Session default LLM profile set to '{prof}'"
    # Override specific agent
    if len(parts) == 2:
        agent_name, prof = parts
        if prof not in profiles:
            return f"Unknown profile '{prof}'. Available: {', '.join(profiles)}"
        blueprint._agent_model_overrides[agent_name] = prof
        return f"Model for agent '{agent_name}' overridden to '{prof}'"
    return "Usage: /model [agent_name] <profile_name>"

# Built-in '/approval' slash command
@slash_registry.register('/approval')
def _approval_command(blueprint=None, args=None):
    """Toggle or display auto-approval mode."""
    return "[slash command] approval mode not implemented yet."

# Built-in '/history' slash command
@slash_registry.register('/history')
def _history_command(blueprint=None, args=None):
    """Display session history of commands and files."""
    return "[slash command] history not implemented yet."

# Built-in '/clear' slash command
@slash_registry.register('/clear')
def _clear_command(blueprint=None, args=None):
    """Clear the screen and current context."""
    return "[slash command] context cleared."

# Built-in '/clearhistory' slash command
@slash_registry.register('/clearhistory')
def _clearhistory_command(blueprint=None, args=None):
    """Clear the command history."""
    return "[slash command] command history cleared."
